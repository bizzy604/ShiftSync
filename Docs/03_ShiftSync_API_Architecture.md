# ShiftSync — API Architecture & Specifications
### API Architect | Priority Soft Assessment

---

> **Skill Applied:** `api-architect`
> **Input:** PRD (`solutions-architect-prd`) + System Design (`faang-system-design`)
> **Philosophy:** APIs as long-term contracts. Predictable. Explicit. Safe to evolve.

---

## 1. Executive Summary

| Decision | Choice | Rationale |
|---|---|---|
| **API Style** | REST | Browser-first app with clear CRUD resources. GraphQL adds flexibility without need at this scale. gRPC is inappropriate for browser clients. |
| **Versioning** | URI-based `/api/v1/` | Simplest for browser clients; unambiguous deprecation path to `/api/v2/` |
| **Authentication** | JWT (RS256) in HttpOnly cookie | HttpOnly prevents XSS token theft vs localStorage. RS256 allows public-key verification. |
| **Datetime format** | UTC ISO 8601 in all request/response bodies | All times on the wire in UTC; display conversion happens client-side using location's IANA TZ |
| **Error format** | Structured JSON with `code`, `details[]`, `suggestions[]` | Enables frontend to render specific constraint violation messages, not just generic errors |
| **Real-time** | WebSocket (Socket.IO) alongside REST | REST for CRUD operations; WebSocket for push events. Clean separation of concerns. |

---

## 2. API Consumers & Access Patterns

| Consumer | Access Pattern | Notes |
|---|---|---|
| React SPA (Admin) | Read-heavy; all locations and users | Full cross-location visibility |
| React SPA (Manager) | Read/write on assigned locations | Assignment writes are the critical hot path |
| React SPA (Staff) | Read-heavy; self-scoped with swap actions | Primarily reads own schedule + available pickups |
| Background job (cron) | Internal write to expire swap requests | Not an external API consumer |

**Read/write ratio:** ~80/20. Schedule reads dominate. The critical write path is `POST /api/v1/shifts/:id/assignments` — this is where constraint enforcement, advisory locking, audit logging, and notification creation all happen in a single transaction.

---

## 3. Standard Error Format

Every API error returns this structure:

```json
{
  "error": {
    "code": "CONSTRAINT_VIOLATION",
    "message": "Cannot assign Maria Torres to this shift.",
    "details": [
      {
        "rule": "REST_PERIOD",
        "description": "Her previous shift ends at 07:00. This shift starts at 14:00. Only 7 hours gap. Minimum required: 10 hours.",
        "severity": "HARD_BLOCK"
      },
      {
        "rule": "WEEKLY_HOURS",
        "description": "This assignment would bring her to 41 projected hours this week.",
        "severity": "WARNING"
      }
    ],
    "suggestions": [
      { "userId": "usr_456", "name": "John Kim", "reason": "Meets all requirements" },
      { "userId": "usr_789", "name": "Amy Chen", "reason": "Meets all requirements" }
    ]
  }
}
```

**Key design decisions:**
- All constraint violations are returned simultaneously — managers see the complete picture, not one error at a time
- `severity: "HARD_BLOCK"` cannot be bypassed without an override payload
- `suggestions[]` is always populated when a violation occurs and qualified alternatives exist

---

## 4. HTTP Status Code Standards

| Code | Meaning | Usage |
|---|---|---|
| `200 OK` | Success | GET, PUT |
| `201 Created` | Resource created | POST |
| `204 No Content` | Success, no body | DELETE |
| `400 Bad Request` | Input validation failure | Missing fields, invalid formats |
| `401 Unauthorized` | Missing or expired JWT | Redirect to login |
| `403 Forbidden` | Valid JWT, insufficient role | Manager accessing another location |
| `404 Not Found` | Resource does not exist | Invalid IDs |
| `409 Conflict` | Concurrent write conflict | Two managers assigned same staff simultaneously |
| `422 Unprocessable Entity` | Business logic failure | Constraint violation |
| `429 Too Many Requests` | Rate limit exceeded | Auth or API throttle hit |
| `500 Internal Server Error` | Unexpected failure | Never expose stack trace to client |

---

## 5. Authentication & Authorization

### Auth Flow

```
POST /api/v1/auth/login
  → Validates credentials
  → Issues JWT (RS256, 8hr expiry)
  → Sets HttpOnly cookie: "shiftsync_token"
  → Returns: { user: { id, name, role, locationIds } }

Every subsequent request:
  → Middleware extracts JWT from cookie
  → Verifies RS256 signature
  → Attaches req.user = { id, role, locationIds[] }
  → Role check happens per-endpoint in route handler
```

### Authorization Rules

| Role | Can Access |
|---|---|
| `admin` | All endpoints, all locations, all users |
| `manager` | Endpoints scoped to `req.user.locationIds[]` only |
| `staff` | Self-scoped endpoints only (own schedule, own availability, own swap requests) |

**Critical rule:** Role is read from the verified JWT — never from the request body. A `role` field in a request body is ignored.

### Auth Endpoints

```
POST   /api/v1/auth/login
POST   /api/v1/auth/logout
POST   /api/v1/auth/refresh
```

**POST /api/v1/auth/login**
```json
// Request
{ "email": "string", "password": "string" }

// Response 200
{
  "user": {
    "id": "usr_abc123",
    "name": "Maria Torres",
    "role": "manager",
    "locationIds": ["loc_ocean_ave", "loc_pier39"]
  }
}
// JWT set as HttpOnly cookie — not in response body
```

---

## 6. Core Endpoint Specifications

### 6.1 Users

```
GET    /api/v1/users                                 [admin, manager]
POST   /api/v1/users                                 [admin]
GET    /api/v1/users/:userId                         [admin, manager, self]
PUT    /api/v1/users/:userId                         [admin, self-limited]
DELETE /api/v1/users/:userId                         [admin]

GET    /api/v1/users/:userId/skills                  [admin, manager]
POST   /api/v1/users/:userId/skills                  [admin]
DELETE /api/v1/users/:userId/skills/:skillId         [admin]

GET    /api/v1/users/:userId/certifications          [admin, manager]
POST   /api/v1/users/:userId/certifications          [admin]
DELETE /api/v1/users/:userId/certifications/:locationId  [admin]

GET    /api/v1/users/:userId/availability            [admin, manager, self]
PUT    /api/v1/users/:userId/availability            [admin, self]
```

**GET /api/v1/users** — Query parameters:
- `?locationId=loc_abc` — filter by location certification
- `?skillId=skl_bartender` — filter by skill
- `?page=1&limit=25` — pagination

**POST /api/v1/users**
```json
// Request
{
  "name": "Carlos Rivera",
  "email": "carlos@coastaleats.com",
  "password": "••••••••",
  "role": "staff",
  "homeTimezone": "America/Los_Angeles",
  "desiredHoursPerWeek": 32,
  "hourlyRate": 18.50
}

// Response 201
{
  "id": "usr_carlos_01",
  "name": "Carlos Rivera",
  "email": "carlos@coastaleats.com",
  "role": "staff",
  "homeTimezone": "America/Los_Angeles",
  "desiredHoursPerWeek": 32,
  "hourlyRate": 18.50,
  "isActive": true,
  "createdAt": "2025-08-01T18:00:00Z"
}
```

**PUT /api/v1/users/:userId/availability**
```json
// Request
{
  "recurring": [
    { "dayOfWeek": "MON", "startClockTime": "09:00", "endClockTime": "17:00" },
    { "dayOfWeek": "WED", "startClockTime": "14:00", "endClockTime": "22:00" },
    { "dayOfWeek": "FRI", "startClockTime": "17:00", "endClockTime": "23:59" }
  ],
  "exceptions": [
    { "date": "2025-12-24", "isAvailable": false },
    { "date": "2025-12-31", "startClockTime": "10:00", "endClockTime": "15:00" }
  ]
}

// Response 200
{ "updated": true, "effectiveFrom": "2025-08-05" }
```

---

### 6.2 Locations

```
GET    /api/v1/locations               [all roles]
POST   /api/v1/locations               [admin]
GET    /api/v1/locations/:locationId   [all roles]
PUT    /api/v1/locations/:locationId   [admin]
```

**Location response schema:**
```json
{
  "id": "loc_ocean_ave",
  "name": "Ocean Ave",
  "address": "123 Ocean Ave, Santa Monica, CA 90401",
  "ianaTimezone": "America/Los_Angeles",
  "isActive": true
}
```

---

### 6.3 Shifts

```
GET    /api/v1/locations/:locationId/shifts                      [admin, manager-own, staff-own-assigned]
POST   /api/v1/locations/:locationId/shifts                      [admin, manager-own]
GET    /api/v1/locations/:locationId/shifts/:shiftId             [admin, manager-own, staff-assigned]
PUT    /api/v1/locations/:locationId/shifts/:shiftId             [admin, manager-own]
DELETE /api/v1/locations/:locationId/shifts/:shiftId             [admin, manager-own]

POST   /api/v1/locations/:locationId/shifts/publish-week         [admin, manager-own]
POST   /api/v1/locations/:locationId/shifts/:shiftId/unpublish   [admin, manager-own]
```

**GET /api/v1/locations/:locationId/shifts** — Query parameters:
- `?weekStart=2025-08-11` — required; returns all shifts in that Mon–Sun week
- `?status=draft|published` — filter by status

**POST /api/v1/locations/:locationId/shifts** — Times submitted in location's local time; stored in UTC:
```json
// Request
{
  "date": "2025-08-15",
  "startTime": "18:00",
  "endTime": "23:00",
  "requiredSkillId": "skl_bartender",
  "headcountNeeded": 2
}

// Response 201
{
  "id": "shf_sat_eve_01",
  "locationId": "loc_ocean_ave",
  "date": "2025-08-15",
  "startUtc": "2025-08-16T01:00:00Z",
  "endUtc": "2025-08-16T06:00:00Z",
  "startLocal": "2025-08-15T18:00:00-07:00",
  "endLocal": "2025-08-15T23:00:00-07:00",
  "requiredSkill": { "id": "skl_bartender", "name": "bartender" },
  "headcountNeeded": 2,
  "status": "draft",
  "weekStart": "2025-08-11",
  "editCutoffUtc": null,
  "createdAt": "2025-08-01T18:30:00Z"
}
```

**POST /api/v1/locations/:locationId/shifts/publish-week**
```json
// Request
{ "weekStart": "2025-08-11" }

// Response 200
{
  "publishedShifts": 14,
  "editCutoffUtc": "2025-08-13T01:00:00Z",
  "notifiedStaffCount": 11
}

// Triggers: schedule.published WebSocket event to all affected staff
```

---

### 6.4 Assignments — The Critical Write Endpoint

```
GET    /api/v1/shifts/:shiftId/assignments                       [admin, manager-own, staff-own]
POST   /api/v1/shifts/:shiftId/assignments                       [admin, manager-own]
DELETE /api/v1/shifts/:shiftId/assignments/:assignmentId         [admin, manager-own]
GET    /api/v1/shifts/:shiftId/assignments/preview               [admin, manager-own]
```

**POST /api/v1/shifts/:shiftId/assignments** — Full constraint enforcement on every call:

```json
// Request (standard assignment)
{ "userId": "usr_carlos_01" }

// Request (with override for 7th consecutive day or post-cutoff edit)
{
  "userId": "usr_carlos_01",
  "overrideReason": "Emergency coverage — only available bartender"
}

// Response 201 — success
{
  "id": "asgn_xyz_001",
  "shiftId": "shf_sat_eve_01",
  "userId": "usr_carlos_01",
  "userName": "Carlos Rivera",
  "status": "assigned",
  "version": 1,
  "assignedBy": "usr_manager_01",
  "assignedAt": "2025-08-01T19:00:00Z"
}

// Response 422 — constraint violation
{
  "error": {
    "code": "CONSTRAINT_VIOLATION",
    "message": "Cannot assign Carlos Rivera to this shift.",
    "details": [
      {
        "rule": "REST_PERIOD",
        "description": "Carlos's previous shift ends at 23:00. This shift starts at 07:00. Only 8 hours gap. Minimum required: 10 hours.",
        "severity": "HARD_BLOCK"
      }
    ],
    "suggestions": [
      { "userId": "usr_john_02", "name": "John Kim", "reason": "Has bartender skill, certified at Ocean Ave, available 07:00-15:00" },
      { "userId": "usr_amy_03", "name": "Amy Chen", "reason": "Has bartender skill, certified at Ocean Ave, available 07:00-12:00" }
    ]
  }
}

// Response 409 — concurrent conflict
{
  "error": {
    "code": "CONCURRENT_CONFLICT",
    "message": "Assignment conflict: Carlos Rivera was just assigned to a conflicting shift at Pier 39 by another manager."
  }
}
```

**GET /api/v1/shifts/:shiftId/assignments/preview** — Non-mutating what-if check:
```
?userId=usr_carlos_01

// Response 200
{
  "userId": "usr_carlos_01",
  "userName": "Carlos Rivera",
  "valid": true,
  "violations": [],
  "warnings": [
    {
      "rule": "WEEKLY_HOURS",
      "description": "This assignment would bring Carlos to 38 projected hours this week.",
      "severity": "WARNING"
    }
  ],
  "projectedWeeklyHours": 38.0,
  "projectedDailyHours": 7.5,
  "projectedOvertimeCost": 0.00
}
```

---

### 6.5 Swap & Drop Requests

```
GET    /api/v1/swap-requests                                     [admin, manager-own, staff-own]
POST   /api/v1/swap-requests                                     [staff]
GET    /api/v1/swap-requests/:requestId                          [involved parties only]
PUT    /api/v1/swap-requests/:requestId/accept                   [target staff only]
PUT    /api/v1/swap-requests/:requestId/reject                   [target staff only]
PUT    /api/v1/swap-requests/:requestId/cancel                   [requesting staff, admin]
PUT    /api/v1/swap-requests/:requestId/approve                  [manager, admin]
PUT    /api/v1/swap-requests/:requestId/decline                  [manager, admin]

POST   /api/v1/drop-requests                                     [staff]
GET    /api/v1/drop-requests/available                           [staff — filtered to qualified only]
POST   /api/v1/drop-requests/:requestId/pickup                   [staff — must be qualified]
PUT    /api/v1/drop-requests/:requestId/approve                  [manager, admin]
PUT    /api/v1/drop-requests/:requestId/decline                  [manager, admin]
```

**POST /api/v1/swap-requests**
```json
// Request
{
  "myAssignmentId": "asgn_abc_001",
  "targetUserId": "usr_john_02"
}

// Response 201
{
  "id": "swap_001",
  "type": "swap",
  "status": "PENDING_ACCEPTEE",
  "requesterAssignmentId": "asgn_abc_001",
  "targetUserId": "usr_john_02",
  "initiatedAt": "2025-08-04T14:00:00Z",
  "expiresAt": null
}

// Response 422 — max pending requests
{
  "error": {
    "code": "MAX_PENDING_REQUESTS",
    "message": "You already have 3 pending swap/drop requests. Resolve existing requests before creating new ones."
  }
}
```

**GET /api/v1/drop-requests/available** — Server enforces qualification:
- Only returns drops where the requesting staff member has the required skill
- Only returns drops at locations where they are certified
- Only returns drops where constraint engine passes (availability, no double-booking, rest period, etc.)
- A staff member never sees drops they cannot legally pick up

```json
// Response 200
{
  "available": [
    {
      "dropRequestId": "drop_002",
      "shift": {
        "id": "shf_sun_eve_01",
        "date": "2025-08-10",
        "startLocal": "2025-08-10T19:00:00-07:00",
        "endLocal": "2025-08-10T23:00:00-07:00",
        "location": { "name": "Ocean Ave" },
        "requiredSkill": "bartender"
      },
      "originalStaff": { "name": "Maria Torres" },
      "expiresAt": "2025-08-10T18:00:00Z"
    }
  ]
}
```

---

### 6.6 Notifications

```
GET    /api/v1/notifications                         [self]
PUT    /api/v1/notifications/read-all                [self]
PUT    /api/v1/notifications/:notificationId/read    [self]
GET    /api/v1/notifications/preferences             [self]
PUT    /api/v1/notifications/preferences             [self]
```

**GET /api/v1/notifications** — Query params: `?page=1&limit=20&unreadOnly=true`

```json
// Response 200
{
  "unreadCount": 3,
  "notifications": [
    {
      "id": "notif_001",
      "type": "shift.assigned",
      "message": "You have been assigned to Saturday Aug 10, 6pm–11pm at Ocean Ave.",
      "payload": { "shiftId": "shf_sat_01", "locationId": "loc_ocean_ave" },
      "createdAt": "2025-08-04T15:00:00Z",
      "readAt": null
    }
  ],
  "pagination": { "page": 1, "limit": 20, "total": 12 }
}
```

---

### 6.7 Analytics

```
GET /api/v1/analytics/overtime-dashboard     [admin, manager-own]
GET /api/v1/analytics/fairness-report        [admin, manager-own]
GET /api/v1/analytics/hours-distribution     [admin, manager-own]
GET /api/v1/on-duty                          [admin, manager-own]
```

**GET /api/v1/analytics/overtime-dashboard** — Query params: `?locationId=loc_abc&weekStart=2025-08-11`

```json
// Response 200
{
  "weekStart": "2025-08-11",
  "locationId": "loc_ocean_ave",
  "totalProjectedOvertimeCost": 270.00,
  "staff": [
    {
      "userId": "usr_carlos_01",
      "name": "Carlos Rivera",
      "projectedWeeklyHours": 52.0,
      "overtimeHours": 12.0,
      "projectedOvertimeCost": 270.00,
      "offendingAssignmentIds": ["asgn_thu_01", "asgn_fri_01"]
    }
  ]
}
```

**GET /api/v1/analytics/fairness-report** — Query params: `?locationId=loc_abc&startDate=2025-07-01&endDate=2025-08-01`

```json
// Response 200
{
  "period": { "startDate": "2025-07-01", "endDate": "2025-08-01" },
  "locationId": "loc_ocean_ave",
  "fairnessScore": 2.4,
  "fairnessGrade": "POOR",
  "staff": [
    {
      "userId": "usr_carlos_01",
      "name": "Carlos Rivera",
      "totalHours": 128.0,
      "desiredHoursPerWeek": 32,
      "schedulingVariancePct": 0.0,
      "premiumShiftCount": 8,
      "premiumShiftPct": 40.0
    },
    {
      "userId": "usr_amy_03",
      "name": "Amy Chen",
      "totalHours": 64.0,
      "desiredHoursPerWeek": 32,
      "schedulingVariancePct": -50.0,
      "premiumShiftCount": 0,
      "premiumShiftPct": 0.0
    }
  ]
}
```

**GET /api/v1/on-duty** — Query params: `?locationId=loc_abc` (optional; Admin gets all locations)

```json
// Response 200
{
  "asOf": "2025-08-10T22:30:00Z",
  "locations": [
    {
      "locationId": "loc_ocean_ave",
      "locationName": "Ocean Ave",
      "ianaTimezone": "America/Los_Angeles",
      "localTime": "2025-08-10T15:30:00-07:00",
      "currentShift": { "id": "shf_sat_eve_01", "startLocal": "18:00", "endLocal": "23:00" },
      "onDutyStaff": [
        { "userId": "usr_carlos_01", "name": "Carlos Rivera", "skill": "bartender" },
        { "userId": "usr_amy_03", "name": "Amy Chen", "skill": "server" }
      ]
    }
  ]
}
```

---

### 6.8 Audit Logs

```
GET    /api/v1/audit-logs            [admin: all; manager: own locations]
GET    /api/v1/audit-logs/export     [admin only — streams CSV]
```

**GET /api/v1/audit-logs** — Query params: `?entityType=shift&entityId=shf_001&locationId=loc_abc&startDate=2025-08-01&endDate=2025-08-31&page=1&limit=50`

```json
// Response 200
{
  "logs": [
    {
      "id": "audit_001",
      "actorId": "usr_manager_01",
      "actorName": "Jordan Lee",
      "actionType": "shift.assign",
      "entityType": "assignment",
      "entityId": "asgn_xyz_001",
      "beforeState": null,
      "afterState": { "userId": "usr_carlos_01", "shiftId": "shf_sat_01", "status": "assigned" },
      "reason": null,
      "locationId": "loc_ocean_ave",
      "createdAt": "2025-08-04T19:00:00Z"
    }
  ],
  "pagination": { "page": 1, "limit": 50, "total": 87 }
}
```

**GET /api/v1/audit-logs/export** — Streams a CSV file directly:
- `Content-Type: text/csv`
- `Content-Disposition: attachment; filename="audit_log_2025-08-01_2025-08-31.csv"`

---

## 7. WebSocket Event Catalog

Clients authenticate the WebSocket connection on connect by passing their JWT. They auto-join relevant rooms.

### Events: Server → Client

| Event | Trigger | Room | Payload |
|---|---|---|---|
| `schedule.published` | Manager publishes a week | `location:{locationId}` | `{ locationId, weekStart, affectedUserIds[] }` |
| `schedule.updated` | Manager edits a published shift | `location:{locationId}` | `{ locationId, shiftId, changes }` |
| `assignment.changed` | Assignment created, updated, or removed | `user:{userId}` | `{ shiftId, userId, status, changedBy }` |
| `swap.status_changed` | Any swap state transition | `user:{userId}` for each involved party | `{ swapRequestId, newStatus, message }` |
| `notification.new` | Any notification created | `user:{userId}` | `{ notificationId, type, message }` |
| `assignment.conflict` | Second writer loses concurrent race | `user:{conflictingManagerId}` | `{ shiftId, conflictingUserId, message }` |

### Events: Client → Server

| Event | Sent By | Purpose |
|---|---|---|
| `authenticate` | All clients on connect | `{ token }` — validates JWT, assigns rooms |
| `join_location` | Managers | `{ locationId }` — subscribes to location room |

---

## 8. Versioning & Deprecation Strategy

| Aspect | Policy |
|---|---|
| **Current version** | `/api/v1/` |
| **Breaking changes** | Increment to `/api/v2/`; run both versions in parallel for a deprecation window |
| **Deprecation notice** | 3-month minimum notice; `Deprecation: true` response header on deprecated endpoints |
| **Non-breaking additions** | New optional fields in response bodies; new optional query parameters — these do not require version bump |
| **Backward compatibility** | Response schemas are additive only; existing fields are never renamed or removed within a version |

---

## 9. Rate Limiting

| Endpoint Group | Limit | Response Headers |
|---|---|---|
| Auth endpoints (`/auth/login`, `/auth/refresh`) | 10 req/min per IP | `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` |
| General API endpoints | 300 req/min per authenticated user | `X-RateLimit-Remaining`, `X-RateLimit-Reset` |
| Analytics endpoints | 30 req/min per user | `X-RateLimit-Remaining` |
| WebSocket connections | 1 active connection per authenticated user | N/A |

On limit exceeded: `HTTP 429` with `Retry-After` header.

---

## 10. Security Considerations

| Concern | Control |
|---|---|
| **XSS token theft** | JWT in HttpOnly cookie — inaccessible to JavaScript |
| **CSRF** | SameSite=Strict cookie attribute; CSRF token on state-mutating requests |
| **SQL injection** | All queries via ORM parameterized statements — no string interpolation |
| **Role escalation** | Role never accepted from request body — always from verified JWT |
| **Audit bypass** | `actor_id` written from JWT in middleware — cannot be spoofed by client |
| **Sensitive field exposure** | `password_hash` never returned in any API response |
| **Replay attacks** | JWT `jti` claim + Redis blacklist for logout tokens |
| **Input validation** | All request bodies validated with JSON Schema before reaching service layer |

---

## 11. Trade-offs & Assumptions

| Decision | Trade-off |
|---|---|
| UTC in transit, display conversion client-side | Simpler server logic; requires client to correctly apply location IANA TZ for display |
| All violations returned simultaneously | Slightly more complex constraint engine; significantly better UX for managers building schedules |
| `GET /drop-requests/available` filtered server-side | Higher server compute per request; prevents client-side filtering bugs that could expose invalid pickups |
| Audit log export as streaming CSV | Memory-efficient for large exports; cannot be cached by standard HTTP caching |
| HttpOnly cookie over Authorization header | Prevents XSS; slightly complicates non-browser clients (not a concern — this is a browser-only app) |

---

## 12. Open Questions & Risks

- **Risk:** `GET /drop-requests/available` runs the constraint engine for every active drop against the requesting staff member — at scale with many open drops, this could become slow. Mitigation: pre-filter by skill and location before running constraint engine; add index on `(swap_requests.type, status, expires_at)`.
- **Risk:** Audit log CSV export for large date ranges could be slow. Mitigation: streaming query + server-side pagination with `cursor`-based approach for very large exports.
- **Open:** Should `GET /api/v1/users` for a Manager return all staff at their location, or only staff currently certified? **Decision:** All staff with an active certification at any of the manager's locations, regardless of whether they are currently scheduled.
