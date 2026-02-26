# ShiftSync — Software Product Development Plan
### Software Product Dev | Priority Soft Assessment

---

> **Skill Applied:** `software-product-dev`
> **Input:** PRD + System Design + API Architecture + Database Architecture
> **Goal:** Translate all upstream artifacts into an actionable build plan with technology choices, repo structure, 72-hour timeline, and implementation guidance.

---

## 1. Technology Stack

Every choice is justified against the requirements — not defaults.

| Layer | Technology | Version | Justification |
|---|---|---|---|
| **Frontend framework** | React | 18 | Component-based, strong TypeScript ecosystem, excellent WebSocket/real-time patterns |
| **Frontend language** | TypeScript | 5.x | Type safety across API contracts; catches timezone/interface bugs at compile time |
| **UI component library** | shadcn/ui + Tailwind CSS | Latest | Accessible, composable components; no vendor lock-in; utility-first styling for rapid iteration |
| **Calendar / Schedule view** | FullCalendar.io (React adapter) | 6.x | Pre-built weekly view with drag-and-drop; saves ~2–3 days of custom calendar development |
| **Server state management** | TanStack Query (React Query) | v5 | Server state caching, background refetch on window focus, optimistic updates for assignment actions |
| **WebSocket client** | Socket.IO Client | v4 | Matches server implementation; automatic reconnection, room management, long-polling fallback |
| **Backend framework** | Python + FastAPI | v4 | Non-blocking I/O handles concurrent WebSocket + REST cleanly; TypeScript support; 2× throughput vs Express |
| **ORM** | Prisma | v5 | Type-safe database access; migration management; native PostgreSQL support; strongly typed query results |
| **Database** | PostgreSQL | 15 | ACID, advisory locks, JSONB, TIMESTAMPTZ — see Database Architecture document |
| **Cache / Sessions** | Redis (ioredis client) | 7 | JWT session store, rate-limiting counters, WebSocket state |
| **WebSocket server** | Socket.IO | v4 | Same Node.js process for v1; extractable with Redis adapter for horizontal scaling |
| **Background jobs** | cron-jobs | v3 | Swap/drop expiry checks every 15 minutes; lightweight, no external dependency |
| **Timezone library** | date-fns-tz | v3 | DST-safe IANA timezone resolution; `fromZonedTime` and `toZonedTime` cover all required patterns |
| **Auth** | jose (JWT) | v5 | RS256 JWT signing/verification; no external auth service required |
| **Validation** | Zod | v3 | Schema-first request validation; shared types between frontend and backend |
| **Monorepo tooling** | Turborepo | v2 | Build pipeline, caching, workspace management |
| **Deployment** | Railway / Render / Fly.io | — | PaaS with PostgreSQL addon; free tier sufficient for assessment demo URL; < 10 min deploy |

---

## 2. Repository Structure

```
shiftsync/
├── apps/
│   ├── web/                          # React SPA
│   │   ├── src/
│   │   │   ├── pages/
│   │   │   │   ├── admin/
│   │   │   │   │   ├── Dashboard.tsx
│   │   │   │   │   └── AuditLog.tsx
│   │   │   │   ├── manager/
│   │   │   │   │   ├── ScheduleBuilder.tsx     # FullCalendar-based weekly view
│   │   │   │   │   ├── OvertimeDashboard.tsx
│   │   │   │   │   ├── FairnessReport.tsx
│   │   │   │   │   └── OnDutyNow.tsx
│   │   │   │   └── staff/
│   │   │   │       ├── MySchedule.tsx
│   │   │   │       ├── AvailableShifts.tsx     # Drop pickup feed
│   │   │   │       └── MySwapRequests.tsx
│   │   │   ├── components/
│   │   │   │   ├── AssignmentModal.tsx         # Constraint result display + suggestions
│   │   │   │   ├── ConstraintViolationAlert.tsx
│   │   │   │   ├── NotificationCenter.tsx
│   │   │   │   ├── WhatIfPreview.tsx
│   │   │   │   └── SwapRequestFlow.tsx
│   │   │   ├── hooks/
│   │   │   │   ├── useSchedule.ts
│   │   │   │   ├── useWebSocket.ts             # Socket.IO connection + event handlers
│   │   │   │   ├── useNotifications.ts
│   │   │   │   └── useAssignment.ts            # Mutation + optimistic update
│   │   │   └── lib/
│   │   │       ├── api.ts                      # Typed API client (generated from Zod schemas)
│   │   │       ├── queryClient.ts
│   │   │       └── timezone.ts                 # Display conversion helpers
│   │   └── package.json
│   │
│   └── api/                          # Node.js + Fastify backend
│       ├── src/
│       │   ├── routes/
│       │   │   ├── auth.ts
│       │   │   ├── users.ts
│       │   │   ├── locations.ts
│       │   │   ├── shifts.ts
│       │   │   ├── assignments.ts
│       │   │   ├── swaps.ts
│       │   │   ├── notifications.ts
│       │   │   ├── analytics.ts
│       │   │   └── audit.ts
│       │   ├── services/                       # Business logic (thin orchestrators)
│       │   │   ├── SchedulingService.ts
│       │   │   ├── SwapService.ts
│       │   │   ├── NotificationService.ts
│       │   │   └── AuditService.ts
│       │   ├── middleware/
│       │   │   ├── authenticate.ts             # JWT extraction + verification
│       │   │   ├── authorize.ts                # Role + location ownership checks
│       │   │   └── rateLimit.ts
│       │   ├── websocket/
│       │   │   ├── index.ts                    # Socket.IO setup
│       │   │   └── events.ts                   # Event emission helpers
│       │   └── jobs/
│       │       └── swapExpiry.ts               # cron-job every 15min
│       └── package.json
│
├── packages/
│   └── constraint-engine/            # Shared pure TypeScript library
│       ├── src/
│       │   ├── index.ts              # Public API: evaluateAssignment()
│       │   ├── checks/
│       │   │   ├── skillMatch.ts
│       │   │   ├── locationCert.ts
│       │   │   ├── availability.ts   # DST-safe clock-time resolution
│       │   │   ├── doubleBooking.ts  # Half-open interval overlap detection
│       │   │   ├── restPeriod.ts
│       │   │   ├── dailyHours.ts
│       │   │   ├── weeklyHours.ts
│       │   │   └── consecutiveDays.ts
│       │   └── types.ts
│       └── __tests__/
│           ├── skillMatch.test.ts
│           ├── availability.test.ts   # DST edge cases
│           ├── doubleBooking.test.ts  # Overnight shift overlap cases
│           ├── consecutiveDays.test.ts
│           └── integration.test.ts   # Full constraint engine scenarios
│
├── prisma/
│   ├── schema.prisma
│   └── migrations/
│       └── 001_initial_schema.sql
│
├── seed/
│   └── seed.ts                       # Comprehensive realistic seed data
│
└── turbo.json
```

---

## 3. 72-Hour Development Timeline

Structured to ensure the highest-weight evaluation criteria are built and testable first.

### Phase 1: Foundation (Hours 0–16)

**Goal:** Database up, auth working, users and locations CRUD, availability API.

| Task | Notes |
|---|---|
| Prisma schema + initial migration | Full schema from DB Architecture document |
| Seed data (Phase 1) | 4 locations, 2 managers, 8 staff, skills, certifications |
| Auth routes: login / logout / refresh | JWT (RS256) in HttpOnly cookie; Redis session store |
| `GET/POST/PUT/DELETE /api/v1/users` | With skill and certification sub-routes |
| `GET/POST /api/v1/locations` | |
| `GET/PUT /api/v1/users/:id/availability` | Recurring + exceptions |
| RBAC middleware | Role + location ownership enforcement |
| React app scaffold | Auth flow, role-based routing, layout shell |

**Exit criteria:** Can create users with skills and certifications; managers are scoped to locations; availability can be set.

---

### Phase 2: Core Scheduling (Hours 16–36)

**Goal:** Constraint engine complete and tested; shifts created; assignments enforced. This is 25% of the evaluation score.

| Task | Notes |
|---|---|
| **Constraint Engine** (pure TS package) | All 8 checks; collects ALL violations; returns suggestions |
| Unit tests for constraint engine | DST edge cases; overnight shifts; 6th/7th day; cross-TZ availability |
| `GET/POST/PUT/DELETE /shifts` | Location-scoped; create in `draft` |
| `POST /shifts/:id/assignments` | Full constraint enforcement; advisory lock; 422 with detailed violations + suggestions |
| `GET /shifts/:id/assignments/preview` | Non-mutating what-if preview |
| `POST /shifts/publish-week` | Sets `edit_cutoff_utc`; triggers WebSocket event |
| `POST /shifts/:id/unpublish` | Cutoff enforcement; override path |
| Audit logging | Every mutation within transaction |
| React: Schedule Builder page | FullCalendar weekly view; shift creation modal |
| React: Assignment Modal | Constraint violation display + suggestions list + what-if panel |

**Exit criteria:** Constraint engine correctly blocks/warns on all 8 rules. Assignment API returns human-readable violations. What-if preview shows projected hours + OT cost.

---

### Phase 3: Swap/Drop + Real-Time (Hours 36–52)

**Goal:** Complete swap/drop state machine; all WebSocket events working; concurrent conflict detection.

| Task | Notes |
|---|---|
| Swap request state machine | All transitions per state machine diagram |
| `POST /swap-requests` | Max 3 pending validation |
| `PUT /swap-requests/:id/accept|reject|cancel|approve|decline` | Role enforcement per state |
| `POST /drop-requests` | Sets `expires_at = shift.start_utc - 24hr` |
| `GET /drop-requests/available` | Server-side qualification filtering |
| `POST /drop-requests/:id/pickup` | Constraint check on pickup staff |
| Drop expiry cron job | `node-cron` every 15min; defensive check at pickup time too |
| Socket.IO setup | Auth on connect; room assignment |
| WebSocket events: `schedule.published`, `assignment.changed`, `swap.status_changed`, `notification.new`, `assignment.conflict` | |
| Concurrent conflict detection | Advisory lock + `HTTP 409` + `assignment.conflict` WS event |
| Notification persistence | Insert in same transaction as mutation |
| `GET/PUT /notifications` | Unread count + paginated list |
| React: WebSocket hook | Auto-reconnect; event handlers → React Query cache invalidation |
| React: Notification Center | Badge + popover list |
| React: Swap Request Flow | Step-by-step UI for initiation → acceptance → manager approval |

**Exit criteria:** Two managers assigning the same bartender simultaneously → one sees conflict notification immediately. Swap regret scenario (Scenario 6) works correctly.

---

### Phase 4: Analytics & Dashboards (Hours 52–62)

**Goal:** All analytics endpoints; overtime dashboard; fairness report; on-duty view.

| Task | Notes |
|---|---|
| `GET /analytics/overtime-dashboard` | Per-staff weekly projection + offending assignments |
| `GET /analytics/fairness-report` | Premium shift counts + fairness score (std dev) + variance % |
| `GET /analytics/hours-distribution` | Hours per staff for date range |
| `GET /on-duty` | Current active staff per location |
| `GET /audit-logs` + CSV export | Streaming CSV for admin export |
| Seed data (Phase 4) | Historical 4-week data with deliberately unfair premium distribution |
| React: Overtime Dashboard | Highlighted staff + projected cost widget |
| React: Fairness Report | Distribution table + fairness score + visual indicator |
| React: On-Duty Now | Live-updating per-location staff view |
| React: Audit Log viewer | Filterable table with before/after state expansion |

**Exit criteria:** Fairness complaint scenario (Scenario 5) — manager can verify that staff member has 0 premium shifts vs. team average in < 3 clicks.

---

### Phase 5: QA, Polish & Deploy (Hours 62–72)

**Goal:** All 6 evaluation scenarios demonstrable; documented; deployed to public URL.

| Task | Notes |
|---|---|
| **Walk all 6 evaluation scenarios** | Sunday Night Chaos, Overtime Trap, Timezone Tangle, Simultaneous Assignment, Fairness Complaint, Regret Swap |
| Seed data validation | Confirm each scenario is playable from seed state |
| Complete seed data | De-certified staff with history; staff at OT threshold; pending swap |
| Documentation | Login credentials for each role; known limitations; assumption log |
| Deploy to public URL | Railway / Render — PostgreSQL addon + Redis addon |
| README | Quick start; seed; login accounts; architecture summary |

---

## 4. Constraint Engine — Implementation

The constraint engine is the single most important module in the system (25% of evaluation weight). It is built as a **pure TypeScript package** with no side effects and no database access — making it fully testable in isolation.

```typescript
// packages/constraint-engine/src/index.ts

export interface Shift {
  id: string;
  locationId: string;
  requiredSkillId: string;
  startUtc: Date;
  endUtc: Date;
}

export interface UserWithDetails {
  id: string;
  homeTimezone: string;        // IANA: 'America/Los_Angeles'
  skills: string[];            // skill IDs
  activeLocationIds: string[]; // certified location IDs (revoked_at IS NULL)
  availability: AvailabilityEntry[];
}

export interface ExistingAssignment {
  shiftId: string;
  startUtc: Date;
  endUtc: Date;
  shiftDate: string;           // 'YYYY-MM-DD' in location's TZ
}

export interface Violation {
  rule: ConstraintRule;
  severity: 'HARD_BLOCK' | 'WARNING' | 'OVERRIDE_REQUIRED';
  description: string;         // Human-readable, specific values included
}

export interface ConstraintResult {
  valid: boolean;              // true only if zero HARD_BLOCK violations
  violations: Violation[];     // All violations collected — no short-circuit
  warnings: Violation[];       // WARNING severity items
  requiresOverride: boolean;   // true if any OVERRIDE_REQUIRED violations present
  suggestions: UserSuggestion[]; // Populated by caller after getting result
}

export function evaluateAssignment(
  shift: Shift,
  user: UserWithDetails,
  existingAssignments: ExistingAssignment[]
): ConstraintResult {
  const violations: Violation[] = [];
  const warnings: Violation[] = [];

  // 1. Skill match
  if (!user.skills.includes(shift.requiredSkillId)) {
    violations.push({
      rule: 'SKILL_MATCH',
      severity: 'HARD_BLOCK',
      description: `${user.name} does not have the required skill: ${shift.requiredSkillName}.`
    });
  }

  // 2. Location certification
  if (!user.activeLocationIds.includes(shift.locationId)) {
    violations.push({
      rule: 'LOCATION_CERT',
      severity: 'HARD_BLOCK',
      description: `${user.name} is not certified to work at ${shift.locationName}.`
    });
  }

  // 3. Availability (DST-safe clock-time resolution)
  const availabilityResult = checkAvailability(shift, user);
  if (!availabilityResult.available) {
    violations.push({
      rule: 'AVAILABILITY',
      severity: 'HARD_BLOCK',
      description: availabilityResult.message
    });
  }

  // 4. Double-booking (half-open interval: [start, end))
  const overlap = existingAssignments.find(a =>
    a.startUtc < shift.endUtc && a.endUtc > shift.startUtc
  );
  if (overlap) {
    violations.push({
      rule: 'DOUBLE_BOOKING',
      severity: 'HARD_BLOCK',
      description: `${user.name} is already assigned to an overlapping shift from ${formatLocal(overlap.startUtc)} to ${formatLocal(overlap.endUtc)}.`
    });
  }

  // 5. Rest period (10hr minimum gap)
  const restResult = checkRestPeriod(shift, existingAssignments);
  if (!restResult.ok) {
    violations.push({
      rule: 'REST_PERIOD',
      severity: 'HARD_BLOCK',
      description: restResult.message
    });
  }

  // 6. Daily hours
  const dailyResult = checkDailyHours(shift, existingAssignments);
  if (dailyResult.hardBlock) {
    violations.push({ rule: 'DAILY_HOURS', severity: 'HARD_BLOCK', description: dailyResult.message });
  } else if (dailyResult.warn) {
    warnings.push({ rule: 'DAILY_HOURS', severity: 'WARNING', description: dailyResult.message });
  }

  // 7. Weekly hours
  const weeklyResult = checkWeeklyHours(shift, existingAssignments);
  if (weeklyResult.warn) {
    warnings.push({ rule: 'WEEKLY_HOURS', severity: 'WARNING', description: weeklyResult.message });
  }

  // 8. Consecutive days
  const consecutiveResult = checkConsecutiveDays(shift, existingAssignments);
  if (consecutiveResult.overrideRequired) {
    violations.push({ rule: 'CONSECUTIVE_DAYS', severity: 'OVERRIDE_REQUIRED', description: consecutiveResult.message });
  } else if (consecutiveResult.warn) {
    warnings.push({ rule: 'CONSECUTIVE_DAYS', severity: 'WARNING', description: consecutiveResult.message });
  }

  const hardBlocks = violations.filter(v => v.severity === 'HARD_BLOCK');
  const overrideRequired = violations.filter(v => v.severity === 'OVERRIDE_REQUIRED');

  return {
    valid: hardBlocks.length === 0,
    violations,
    warnings,
    requiresOverride: overrideRequired.length > 0,
    suggestions: []  // Populated by SchedulingService after engine returns
  };
}
```

---

## 5. DST-Safe Availability Implementation

This is the most error-prone part of the system. Handled exclusively in the application layer for testability:

```typescript
// packages/constraint-engine/src/checks/availability.ts
import { fromZonedTime, toZonedTime } from 'date-fns-tz';
import { format, getDay } from 'date-fns';

export function checkAvailability(shift: Shift, user: UserWithDetails): AvailabilityResult {
  // For overnight shifts (11pm → 3am), split into segments:
  // Segment A: shift start → midnight (calendar day of shift_date)
  // Segment B: midnight → shift end (calendar day of shift_date + 1)
  const segments = splitOvernightShift(shift);

  for (const segment of segments) {
    // Determine the calendar date of this segment in the user's home timezone
    const segmentDateInUserTZ = toZonedTime(segment.startUtc, user.homeTimezone);
    const dateStr = format(segmentDateInUserTZ, 'yyyy-MM-dd');
    const dayOfWeek = getDay(segmentDateInUserTZ); // 0=Sun ... 6=Sat

    // Check for exception first [AR-05 precedence]
    const exception = user.availability.find(
      a => a.availType === 'exception' && a.specificDate === dateStr
    );

    let window: { start: Date; end: Date } | null = null;

    if (exception) {
      if (!exception.isAvailable) {
        return { available: false, message: `${user.name} has marked ${dateStr} as unavailable.` };
      }
      window = resolveClockWindow(exception, dateStr, user.homeTimezone);
    } else {
      // Fall back to recurring availability for this day of week
      const recurring = user.availability.find(
        a => a.availType === 'recurring' && a.dayOfWeek === dayOfWeek && a.isAvailable
      );
      if (!recurring) {
        return {
          available: false,
          message: `${user.name} has no availability set for ${getDayName(dayOfWeek)}s.`
        };
      }
      window = resolveClockWindow(recurring, dateStr, user.homeTimezone);
    }

    // Check if segment falls within the window
    if (segment.startUtc < window.start || segment.endUtc > window.end) {
      return {
        available: false,
        message: `${user.name}'s availability on ${dateStr} is ${formatTime(window.start, user.homeTimezone)}–${formatTime(window.end, user.homeTimezone)}. This shift segment falls outside that window.`
      };
    }
  }

  return { available: true };
}

function resolveClockWindow(
  entry: AvailabilityEntry,
  dateStr: string,
  timezone: string
): { start: Date; end: Date } {
  // fromZonedTime handles DST correctly:
  // '09:00 America/Los_Angeles' on Nov 3 2024 (fall-back day) → UTC-8 offset
  // '09:00 America/Los_Angeles' on Mar 9 2025 (spring-forward day) → UTC-8 offset
  return {
    start: fromZonedTime(`${dateStr}T${entry.startClock}`, timezone),
    end:   fromZonedTime(`${dateStr}T${entry.endClock}`, timezone),
  };
}
```

---

## 6. Seed Data Plan

The seed data must cover all 6 evaluation scenarios and the documented ambiguity cases.

```typescript
// seed/seed.ts — structure

const LOCATIONS = [
  { name: "Ocean Ave",       address: "123 Ocean Ave, Santa Monica CA",    ianaTimezone: "America/Los_Angeles" },
  { name: "Pier 39",         address: "39 Pier Blvd, San Francisco CA",     ianaTimezone: "America/Los_Angeles" },
  { name: "Midtown Bistro",  address: "456 5th Ave, New York NY",            ianaTimezone: "America/New_York" },
  { name: "Brooklyn Tap",    address: "789 Atlantic Ave, Brooklyn NY",       ianaTimezone: "America/New_York" },
];

const USERS = [
  // Admin
  { name: "Admin User",     role: "admin",   email: "admin@coastaleats.com",   locations: ALL },

  // Managers
  { name: "Jordan Lee",     role: "manager", email: "jordan@coastaleats.com",  locations: ["Ocean Ave", "Midtown Bistro"] },
  { name: "Sam Rivera",     role: "manager", email: "sam@coastaleats.com",     locations: ["Pier 39",   "Brooklyn Tap"]   },

  // Staff — cross-TZ cert (for Scenario 3)
  { name: "Carlos Rivera",  role: "staff",   skills: ["bartender"],           locations: ["Ocean Ave", "Midtown Bistro"],
    homeTimezone: "America/Los_Angeles", availability: { MON: "09:00-17:00", TUE: "09:00-17:00", SAT: "17:00-23:59", SUN: "17:00-23:59" } },

  // Staff — near OT threshold (for Scenario 2)
  { name: "Maria Torres",   role: "staff",   skills: ["bartender", "server"], locations: ["Ocean Ave"],
    currentWeekHours: 35,  // Seed with 35h of existing assignments this week
    desiredHoursPerWeek: 40 },

  // Staff — consecutive days near limit (for consecutive day constraint)
  { name: "Alex Kim",       role: "staff",   skills: ["line cook"],           locations: ["Ocean Ave"],
    currentConsecutiveDays: 5 },  // Seed with 5 consecutive days worked

  // Staff — zero premium shifts (for Scenario 5 - fairness complaint)
  { name: "Amy Chen",       role: "staff",   skills: ["server", "host"],      locations: ["Ocean Ave"],
    historicalPremiumShifts: 0 },

  // Staff — 8 premium shifts (for Scenario 5 contrast)
  { name: "Ben Nguyen",     role: "staff",   skills: ["server"],              locations: ["Ocean Ave"],
    historicalPremiumShifts: 8 },

  // Staff — de-certified (for AR-01 demonstration)
  { name: "Dana Park",      role: "staff",   skills: ["bartender"],           locations: ["Ocean Ave"],
    certification: { locationId: "Pier 39", revokedAt: "2025-07-01", hasHistoricalShifts: true } },

  // Staff — active swap request (for Scenario 6 - Regret Swap)
  { name: "Finn Walsh",     role: "staff",   skills: ["host"],                locations: ["Ocean Ave"],
    pendingSwapStatus: "PENDING_MANAGER" },

  // + 5 more generic staff for operational coverage
];

// Pre-seeded conflicts for constraint demonstration:
const CONSTRAINT_VIOLATIONS_IN_SEED = [
  // Shift A and Shift B assigned to same staff member 6 hours apart (violates rest period)
  // Staff member with 42h already this week assigned to a 5h shift (violates weekly warning)
  // Staff member scheduled for 13h in one day (violates daily hard block — for demo purposes, this one is blocked at seed time)
];
```

**Login credentials for documentation:**
```
Admin:   admin@coastaleats.com   / password: Admin123!
Manager: jordan@coastaleats.com  / password: Manager123!  (Ocean Ave + Midtown)
Manager: sam@coastaleats.com     / password: Manager123!  (Pier 39 + Brooklyn Tap)
Staff:   carlos@coastaleats.com  / password: Staff123!    (Cross-TZ scenario)
Staff:   maria@coastaleats.com   / password: Staff123!    (Near-OT scenario)
Staff:   amy@coastaleats.com     / password: Staff123!    (Zero premium shifts)
```

---

## 7. Known Limitations (For Submission Documentation)

| # | Limitation | Decision / Justification |
|---|---|---|
| L1 | Email notifications are simulated | Stored as DB records. No real SMTP integration. Simulated email is sufficient per assessment scope. |
| L2 | On-Duty Now uses shift time windows | Based on `start_utc ≤ NOW() ≤ end_utc`, not actual clock-in events. No biometric time clock. |
| L3 | No split-timezone locations supported | One canonical IANA TZ per location. `[AR-06]` Restaurants near state lines not modeled. |
| L4 | Fairness score = simple standard deviation | Not weighted by location headcount size differences. Documented simplification. |
| L5 | Web-only (no native mobile app) | Responsive web design. Assessment specifies web-based platform. |
| L6 | Availability resolution is application-layer | DST-safe but requires test coverage for edge-case dates (spring-forward, fall-back, midnight cross). |

---

## 8. Quality Gates

### Before Deploying

- [ ] All 8 constraint rules have unit tests with ≥3 test cases each (including edge cases)
- [ ] DST edge cases covered: spring-forward date, fall-back date, overnight shift crossing midnight
- [ ] All 6 evaluation scenarios are playable from seed state without manual data manipulation
- [ ] Double-booking prevention verified with concurrent API calls (use a test that fires two simultaneous requests)
- [ ] Audit log entries verified for: shift create, assign, publish, swap approve, cert revoke
- [ ] WebSocket events received correctly on a second browser tab when manager publishes schedule
- [ ] CSV audit export downloads correctly for a 30-day range

### Code Organization (10% of evaluation score)

- Services (business logic) are separated from routes (HTTP handling)
- Constraint engine is in a separate package with no dependencies on database or HTTP
- Every mutation is wrapped in a transaction that includes audit logging
- TypeScript strict mode enabled — no `any` types in service layer
- Zod schemas shared between frontend and backend for type-safe API contracts
