# Frontend Engineering Standards
## ShiftSync — React 18 + TypeScript + TanStack Query + Socket.IO

---

## Module Structure

The frontend mirrors the backend's modular monolith layout.

```
web/src/
├── modules/
│   ├── auth/
│   │   ├── index.ts               ← Public barrel
│   │   ├── components/
│   │   │   └── LoginForm.tsx
│   │   ├── hooks/
│   │   │   └── useAuth.ts
│   │   ├── pages/
│   │   │   └── LoginPage.tsx
│   │   ├── auth.types.ts
│   │   └── __tests__/
│   │       └── LoginForm.test.tsx
│   ├── schedule/
│   │   ├── index.ts
│   │   ├── components/
│   │   │   ├── WeeklyCalendar.tsx
│   │   │   ├── ShiftTile.tsx
│   │   │   └── AssignmentModal.tsx
│   │   ├── hooks/
│   │   │   ├── useSchedule.ts
│   │   │   └── useAssignment.ts
│   │   └── __tests__/
│   └── ...
└── shared/
    ├── components/    ← Truly generic UI (Button, Modal, Badge, Spinner)
    ├── hooks/         ← useWebSocket, useNotifications
    ├── api/           ← Typed API client
    └── utils/         ← formatLocalTime, getLocationTz
```

---

## React Component Rules

### One Component = One Responsibility

```tsx
// ❌ WRONG — one component does data fetching + rendering + business decisions
function SchedulePage() {
  const [shifts, setShifts] = useState([]);
  useEffect(() => { fetch('/api/shifts').then(...).then(setShifts) }, []);
  const handleAssign = async (userId) => { /* constraint check logic here */ };
  return <div>{/* 300 lines of JSX */}</div>;
}

// ✅ CORRECT — separated by responsibility
// SchedulePage.tsx — routing + layout only
// useSchedule.ts   — data fetching + cache
// WeeklyCalendar.tsx — rendering only
// useAssignment.ts — mutation + optimistic update
```

### Component Template

```tsx
/**
 * Displays a single shift as a calendar tile with assignment status and staff count.
 * Clicking opens the AssignmentModal for managers, or the ShiftDetailDrawer for staff.
 *
 * @param shift        - The shift data to render
 * @param userRole     - Determines which interaction (manager vs staff view)
 * @param locationTz   - IANA timezone for displaying shift times correctly
 * @param onAssign     - Callback when manager selects this shift to assign
 */
export const ShiftTile = React.memo<ShiftTileProps>(({
  shift,
  userRole,
  locationTz,
  onAssign,
}) => {
  const startTime = formatLocalTime(shift.startUtc, locationTz);
  const endTime   = formatLocalTime(shift.endUtc, locationTz);
  const isManager = userRole === 'admin' || userRole === 'manager';

  return (
    <div
      className={cn('shift-tile', shift.status)}
      onClick={isManager ? () => onAssign(shift) : undefined}
      role={isManager ? 'button' : 'listitem'}
      aria-label={`${shift.requiredSkill} shift, ${startTime} to ${endTime}`}
    >
      <span className="shift-tile__time">{startTime} – {endTime}</span>
      <span className="shift-tile__skill">{shift.requiredSkill}</span>
      <AssignmentBadge assigned={shift.assignedCount} needed={shift.headcountNeeded} />
    </div>
  );
});

ShiftTile.displayName = 'ShiftTile';
```

---

## Custom Hooks — Data Fetching Layer

All server state lives in TanStack Query hooks. Components never call `fetch` directly.

```typescript
/**
 * Fetches and caches the weekly schedule for a given location.
 *
 * Cache key: ['schedule', locationId, weekStart]
 * Stale time: 30s (schedules change infrequently outside of publish events)
 * Background refetch: triggered by 'schedule.published' WebSocket event
 *
 * @param locationId - UUID of the location to fetch schedule for
 * @param weekStart  - ISO date string 'YYYY-MM-DD' (Monday of target week)
 */
export function useSchedule(locationId: string, weekStart: string) {
  const queryClient = useQueryClient();

  // Invalidate cache on real-time schedule.published event
  useWebSocketEvent('schedule.published', (event) => {
    if (event.locationId === locationId) {
      queryClient.invalidateQueries({ queryKey: ['schedule', locationId] });
    }
  });

  return useQuery({
    queryKey: ['schedule', locationId, weekStart],
    queryFn: () => api.schedule.getWeek(locationId, weekStart),
    staleTime: 30_000,
    enabled: Boolean(locationId && weekStart),
  });
}
```

### Mutation Hook with Optimistic Update

```typescript
/**
 * Mutation for creating a shift assignment with optimistic update.
 *
 * Optimistic update: immediately adds the assignment to the calendar UI
 * before the API call completes. Rolls back on failure.
 *
 * On constraint violation (422): passes structured error to onError callback
 * so AssignmentModal can display the specific violated rules and suggestions.
 *
 * @returns TanStack Query mutation object with typed error handling
 */
export function useAssignment(locationId: string, weekStart: string) {
  const queryClient = useQueryClient();

  return useMutation<Assignment, AssignmentError, AssignmentPayload>({
    mutationFn: (payload) => api.assignments.create(payload),

    // Optimistic update
    onMutate: async (payload) => {
      await queryClient.cancelQueries({ queryKey: ['schedule', locationId, weekStart] });
      const previous = queryClient.getQueryData<ScheduleData>(['schedule', locationId, weekStart]);
      // Add optimistic assignment tile immediately
      queryClient.setQueryData(['schedule', locationId, weekStart], (old) =>
        addOptimisticAssignment(old, payload)
      );
      return { previous }; // Context for rollback
    },

    onError: (_err, _payload, context) => {
      // Rollback optimistic update
      if (context?.previous) {
        queryClient.setQueryData(['schedule', locationId, weekStart], context.previous);
      }
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['schedule', locationId, weekStart] });
    },
  });
}
```

---

## WebSocket Hook — Centralised Connection

```typescript
/**
 * Manages the Socket.IO WebSocket connection lifecycle.
 *
 * - Authenticates via JWT on connect
 * - Auto-joins user and location rooms
 * - Reconnects automatically on disconnect (Socket.IO handles this)
 * - Provides a type-safe event subscription API
 *
 * PATTERN: Observer — consumers subscribe to specific events;
 * the hook manages the single shared connection.
 *
 * @example
 * const { isConnected } = useWebSocket();
 * useWebSocketEvent('assignment.changed', (event) => { ... });
 */
export function useWebSocket() {
  const { token } = useAuth();
  const socketRef = useRef<Socket | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    if (!token) return;

    const socket = io(WS_URL, {
      auth: { token },
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });

    socket.on('connect',    () => setIsConnected(true));
    socket.on('disconnect', () => setIsConnected(false));
    socketRef.current = socket;

    return () => { socket.disconnect(); };
  }, [token]);

  return { socket: socketRef.current, isConnected };
}

/**
 * Subscribes to a specific WebSocket event and calls the handler when received.
 * Automatically cleans up the listener on unmount or when deps change.
 *
 * @param event   - The socket event name to subscribe to
 * @param handler - Callback invoked with the typed event payload
 */
export function useWebSocketEvent<K extends keyof WebSocketEvents>(
  event: K,
  handler: (payload: WebSocketEvents[K]) => void,
): void {
  const { socket } = useWebSocket();

  useEffect(() => {
    if (!socket) return;
    socket.on(event, handler);
    return () => { socket.off(event, handler); };
  }, [socket, event, handler]);
}
```

---

## Typed API Client

All HTTP calls go through a typed client. No raw `fetch` in components or hooks.

```typescript
// shared/api/client.ts

/**
 * Typed API client for all ShiftSync REST endpoints.
 * All methods throw typed errors (ConstraintViolationError, ConcurrentConflictError)
 * that hooks and components can handle specifically.
 *
 * All datetime strings in responses are in UTC ISO 8601.
 * Display conversion to location timezone happens in UI utility functions.
 */
export const api = {
  assignments: {
    /**
     * Creates a shift assignment. Runs full constraint validation server-side.
     * @throws {ConstraintViolationError} on 422 — includes all violations and suggestions
     * @throws {ConcurrentConflictError} on 409 — another manager assigned this person simultaneously
     */
    create: async (payload: AssignmentCreatePayload): Promise<Assignment> => {
      const res = await httpClient.post<Assignment>(`/shifts/${payload.shiftId}/assignments`, payload);
      return res.data;
    },

    /**
     * What-if preview — runs constraint engine without committing any change.
     * Use before showing confirmation dialog to display projected impact.
     */
    preview: async (shiftId: string, userId: string): Promise<AssignmentPreview> => {
      const res = await httpClient.get<AssignmentPreview>(
        `/shifts/${shiftId}/assignments/preview`,
        { params: { userId } }
      );
      return res.data;
    },
  },
};
```

---

## Timezone Display — Always Use Location TZ

Times are always displayed in the shift's location timezone, never the viewer's local time.

```typescript
// shared/utils/timezone.utils.ts

/**
 * Formats a UTC datetime string for display in a given IANA timezone.
 * Always use this for displaying shift times — never use new Date().toLocaleTimeString().
 *
 * @param utcDatetime  - UTC ISO 8601 string from API (e.g. '2025-08-10T01:00:00Z')
 * @param ianaTimezone - IANA timezone of the shift location (e.g. 'America/Los_Angeles')
 * @param format       - Display format ('time' | 'datetime' | 'date')
 * @returns Formatted string in the location's local timezone
 *
 * @example
 * formatLocalTime('2025-08-10T01:00:00Z', 'America/Los_Angeles', 'time')
 * // Returns '6:00 PM' (UTC-7 in August)
 */
export function formatLocalTime(
  utcDatetime: string,
  ianaTimezone: string,
  format: 'time' | 'datetime' | 'date' = 'time',
): string {
  return new Intl.DateTimeFormat('en-US', {
    timeZone: ianaTimezone,
    hour: format !== 'date' ? 'numeric' : undefined,
    minute: format !== 'date' ? '2-digit' : undefined,
    month: format !== 'time' ? 'short' : undefined,
    day: format !== 'time' ? 'numeric' : undefined,
  }).format(new Date(utcDatetime));
}
```

---

## Component Testing

```tsx
// __tests__/ShiftTile.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ShiftTile } from '../ShiftTile';

describe('ShiftTile', () => {
  const mockShift = {
    id: 'shift-1',
    startUtc: '2025-08-10T01:00:00Z',  // 6pm PT
    endUtc: '2025-08-10T06:00:00Z',    // 11pm PT
    requiredSkill: 'bartender',
    assignedCount: 1,
    headcountNeeded: 2,
    status: 'published',
  };

  it('displays time in location timezone, not UTC', () => {
    render(
      <ShiftTile
        shift={mockShift}
        userRole="manager"
        locationTz="America/Los_Angeles"
        onAssign={jest.fn()}
      />
    );
    // Should show 6:00 PM – 11:00 PM, NOT 01:00 – 06:00 UTC
    expect(screen.getByText(/6:00 PM – 11:00 PM/)).toBeInTheDocument();
  });

  it('is clickable for managers but not for staff', async () => {
    const onAssign = jest.fn();
    const { rerender } = render(
      <ShiftTile shift={mockShift} userRole="manager" locationTz="America/Los_Angeles" onAssign={onAssign} />
    );
    await userEvent.click(screen.getByRole('button'));
    expect(onAssign).toHaveBeenCalledWith(mockShift);

    rerender(
      <ShiftTile shift={mockShift} userRole="staff" locationTz="America/Los_Angeles" onAssign={onAssign} />
    );
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});
```
