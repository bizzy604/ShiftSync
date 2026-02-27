# ShiftSync — Product Requirements Document (PRD)
### Solutions Architect PRD | Priority Soft Assessment

---

> **Skill Applied:** `solutions-architect-prd`
> **Source:** All requirements derived strictly from the Priority Soft assessment document. Every assumption is labeled `[Ax]`. Every ambiguity resolution is labeled `[ARx]`.

---

## 1. Executive Summary

ShiftSync is a web-based workforce scheduling platform for Coastal Eats, a restaurant group operating **4 locations across 2 time zones** (Pacific and Eastern). It serves three user tiers — Admin, Manager, and Staff — and is built to resolve:

- Staff calling out with no structured coverage path
- Overtime costs spiraling due to poor weekly visibility
- Unfair shift distribution, especially for premium Friday/Saturday evenings
- Managers hoarding high-performing staff across locations
- No single cross-location view of who is working where and when

The system is evaluated on:

| Criterion | Weight |
|---|---|
| Constraint enforcement correctness | 25% |
| Edge case handling | 20% |
| Real-time functionality | 15% |
| User experience & clarity of feedback | 15% |
| Data integrity under concurrent operations | 15% |
| Code organization & maintainability | 10% |

---

## 2. Problem Statement

Coastal Eats operates without a centralized scheduling system, resulting in:

- Staff calling out with no fast-path coverage mechanism
- Managers building schedules without awareness of cumulative weekly hours, leading to surprise overtime
- Premium Friday/Saturday evening shifts distributed inequitably — creating measurable staff dissatisfaction
- Location-level "hoarding" of skilled staff, preventing optimal cross-location coverage
- No Admin-level view across all 4 locations simultaneously

**Why this product exists now:** The assessment requires a deployable solution with seed data covering edge cases, real-time features, and documented architectural decisions — all within 72 hours.

---

## 3. Goals & Non-Goals

### Goals

- Role-based access control: Admin (all locations), Manager (assigned locations only), Staff (self only)
- Fully enforced scheduling constraints with human-readable violation messages and qualified alternative suggestions
- Complete shift swap/drop workflow with a multi-party approval state machine
- Real-time overtime tracking with configurable warnings and hard blocks
- Schedule fairness analytics with premium shift tagging and fairness scoring
- WebSocket-based real-time updates: schedule changes, swap status, concurrent conflict detection
- Timezone-correct storage (all datetimes in UTC) with display in each shift's location timezone
- Immutable audit trail of all schedule changes with Admin CSV export
- Persistent notification system (in-app + simulated email)

### Non-Goals *(explicitly excluded per assessment scope)*

- Payroll processing or payroll system integration
- Biometric time clock or clock-in/clock-out functionality
- Native mobile applications (web-responsive only)
- External calendar sync (Google Calendar, Outlook, etc.)
- Multi-tenant SaaS architecture (single organization deployment)
- HR onboarding or document management

---

## 4. User Personas

### Persona 1: Admin (Corporate Oversight)

- Sees all 4 locations, all staff, all schedules simultaneously
- Exports audit logs for any date range and any location
- No scheduling restrictions — full override capability on all operations
- `[A1]` Admin can perform all Manager actions at any location

### Persona 2: Manager

- Assigned to one or more specific locations; cannot access or modify other managers' locations
- Creates, publishes, edits, and unpublishes shifts for their assigned locations
- Reviews and approves/rejects swap and drop requests
- Views overtime projection dashboard and schedule fairness analytics
- Receives notifications for OT warnings, swap/drop approvals pending, and availability changes

### Persona 3: Staff

- Can be certified to work at 1 or more locations
- Holds one or more skills: `bartender`, `line cook`, `server`, `host`
- Sets recurring weekly availability windows plus one-off date exceptions
- Requests shift swaps with specific colleagues or drops shifts for others to pick up
- Views own schedule, available pickup shifts, and notification feed

---

## 5. Functional Requirements

Each requirement is written as **"The system shall..."** with testable acceptance criteria.

---

### FR-01: Authentication & Role-Based Access Control

**The system shall** enforce three discrete roles with server-side RBAC validation on every request.

| AC | Acceptance Criteria |
|---|---|
| AC-01.1 | A Manager attempting to access a location not in their assigned list receives `HTTP 403` |
| AC-01.2 | A Staff member accessing another staff member's schedule or data receives `HTTP 403` |
| AC-01.3 | Admin users can view and modify all data across all 4 locations |
| AC-01.4 | `[A2]` Session tokens expire after 8 hours of inactivity |

---

### FR-02: Staff Profile Management

**The system shall** maintain staff profiles containing name, email, home timezone, location certifications, skills, desired hours/week, and hourly rate.

| AC | Acceptance Criteria |
|---|---|
| AC-02.1 | Staff can hold active certifications for 1 to N locations simultaneously |
| AC-02.2 | `[A3]` Skills are drawn from a predefined Admin-configurable list: `bartender`, `line cook`, `server`, `host` |
| AC-02.3 | `[AR-01]` On de-certification: historical shifts at that location remain intact and viewable. All future unstarted assignments at that location are immediately unassigned with a manager notification |
| AC-02.4 | Staff member's `desired_hours_per_week` is an integer field, configurable by the staff member |

---

### FR-03: Availability Management

**The system shall** allow staff to define recurring weekly availability windows and one-off date exceptions.

| AC | Acceptance Criteria |
|---|---|
| AC-03.1 | Recurring availability defined as: day-of-week + start clock time + end clock time (e.g., `MON 09:00–17:00`) |
| AC-03.2 | One-off exceptions override recurring availability for a specific calendar date (e.g., unavailable December 24) |
| AC-03.3 | Availability stored as clock time in the staff member's home timezone `[A4]`; resolved to UTC at schedule evaluation time |
| AC-03.4 | DST transitions handled correctly — clock-time semantics, not UTC-offset semantics. Re-evaluated per date |
| AC-03.5 | Overnight shifts (e.g., 11pm–3am) evaluated correctly: end time resolves to the following calendar day |

---

### FR-04: Shift Creation & Management

**The system shall** allow Managers to create, edit, publish, and unpublish shifts.

| AC | Acceptance Criteria |
|---|---|
| AC-04.1 | Each shift record contains: `location_id`, `date`, `start_time`, `end_time`, `required_skill`, `headcount_needed`, `status` (`draft` \| `published`) |
| AC-04.2 | Managers can only create shifts for their assigned locations |
| AC-04.3 | Shifts begin in `draft` status; publishing is an explicit Manager action |
| AC-04.4 | Published shifts are visible to all staff assigned to that shift |
| AC-04.5 | `[A5]` A schedule (logical grouping by week + location) can be unpublished and edited up to 48 hours before the first shift start time in that week |
| AC-04.6 | Editing a published shift after the 48-hour cutoff requires a Manager override with a documented reason, logged to the audit trail |

---

### FR-05: Shift Assignment & Constraint Enforcement

**The system shall** enforce all of the following constraints on every assignment attempt, collecting **all violations simultaneously** (no short-circuit on first failure).

| # | Constraint | Severity | Threshold |
|---|---|---|---|
| 1 | **Skill match:** Staff must possess the required shift skill | Hard Block | Any mismatch |
| 2 | **Location certification:** Staff must be certified at the shift's location | Hard Block | Any mismatch |
| 3 | **Availability:** Shift must fall within staff's available window | Hard Block | Any overlap outside window |
| 4 | **No double-booking:** Staff cannot have overlapping shifts, even across locations | Hard Block | Any overlap |
| 5 | **Rest period:** Minimum gap between consecutive shifts for the same staff member | Hard Block | < 10 hours |
| 6 | **Daily hours:** Per-calendar-day total for this staff member | Warning / Hard Block | 8h warn / 12h block |
| 7 | **Weekly hours:** Projected current-week total | Warning only | 35+ hours |
| 8 | **Consecutive days:** Calendar days worked in a row | Warning / Override | 6th day warn / 7th day override |

| AC | Acceptance Criteria |
|---|---|
| AC-05.1 | Every violation returns a human-readable message identifying the specific rule broken with specific values (e.g., "Only 7hr gap. Minimum required: 10hr") |
| AC-05.2 | After a violation, the system suggests qualified alternatives: staff with matching skill, location cert, availability, and no constraint violations |
| AC-05.3 | `[AR-02]` Consecutive day calculation: any calendar day with at least 1 minute of shift time counts as a worked day — a 1-hour shift counts identically to an 11-hour shift |

---

### FR-06: Shift Swap & Drop Workflow

**The system shall** support a multi-step, manager-approved swap and drop workflow with a formal state machine.

**Swap State Machine:**
```
PENDING_ACCEPTEE → (Staff B accepts) → PENDING_MANAGER → (Manager approves) → APPROVED
                 → (Staff B rejects) → REJECTED
                 → (Staff A cancels) → CANCELLED        [AR-03]
                 → (Shift edited)    → CANCELLED (auto)
```

**Swap Flow:**
1. Staff A initiates swap, selecting Staff B and the shift to exchange
2. Staff B receives in-app notification and accepts or declines
3. If accepted: Manager receives an approval request
4. Manager approves or rejects — original assignment stays active until approval
5. On approval: assignments transfer atomically; all parties notified

**Drop Flow:**
1. Staff A submits a drop request
2. Shift appears as "available for pickup" to all qualified staff (skill + cert + no violations)
3. A qualified staff member picks up the shift
4. Manager approves; assignment transfers atomically

| AC | Acceptance Criteria |
|---|---|
| AC-06.1 | A staff member cannot have more than **3 pending** swap/drop requests simultaneously |
| AC-06.2 | Drop requests expire automatically **24 hours before shift start** if unclaimed; expiry triggers notifications to original staff and manager |
| AC-06.3 | If a manager edits a shift with a pending swap, the swap is auto-cancelled with notifications to all involved parties |
| AC-06.4 | `[AR-03]` **The Regret Swap:** Staff A can cancel before Manager approval, even after Staff B has accepted. The full swap request is cancelled. Staff B is notified. Original assignment remains. |
| AC-06.5 | Staff B accepting a swap is not approval — Manager is the final authority |

---

### FR-07: Overtime & Labor Law Compliance

**The system shall** track and enforce labor rules in real-time at the point of assignment.

| AC | Acceptance Criteria |
|---|---|
| AC-07.1 | `[A6]` Warning fires when projected weekly total ≥ 35 hours (Monday–Sunday workweek) |
| AC-07.2 | Hard block fires when a single assignment would push a staff member past **12 hours** on a calendar day |
| AC-07.3 | Warning fires at **8+ daily hours** |
| AC-07.4 | **6th consecutive day** triggers a warning displayed before the Manager confirms |
| AC-07.5 | **7th consecutive day** requires Manager override with a reason field; reason stored in the audit log |
| AC-07.6 | `[A7]` Dashboard shows projected overtime cost: `hours_over_40 × (hourly_rate × 1.5)` |
| AC-07.7 | **What-if preview:** Before confirming, manager sees projected weekly hours including the proposed new shift |
| AC-07.8 | Dashboard highlights the specific assignment(s) pushing a staff member into overtime |

---

### FR-08: Schedule Fairness Analytics

**The system shall** provide objective fairness reporting tools for managers.

| AC | Acceptance Criteria |
|---|---|
| AC-08.1 | Distribution report shows total hours assigned per staff member for a user-selected date range |
| AC-08.2 | Premium shifts defined as: shifts **starting between 17:00–23:59 on Fridays and Saturdays**, evaluated in the shift's location timezone |
| AC-08.3 | Fairness score = standard deviation of premium shift counts across active staff at a location over the selected period. Lower score = more equitable |
| AC-08.4 | Manager sees staff sorted by scheduling variance vs desired hours: `(actual_hours - desired_hours) / desired_hours × 100%` |
| AC-08.5 | `[AR-04]` Desired hours is **analytics-only** — it does not gate assignment eligibility. A staff member can be assigned beyond their desired hours |

---

### FR-09: Real-Time Features

**The system shall** use WebSocket connections for live updates without page refresh.

| AC | Acceptance Criteria |
|---|---|
| AC-09.1 | Schedule publish/modify events delivered to affected connected staff within **2 seconds** |
| AC-09.2 | Swap request status changes delivered in real-time to all involved parties |
| AC-09.3 | On-Duty Now dashboard shows currently active staff per location (1-minute polling acceptable as fallback) |
| AC-09.4 | **Concurrent conflict:** If two managers simultaneously assign the same staff member to overlapping shifts, the second write fails with an immediate conflict notification — **zero silent overwrites** |

---

### FR-10: Notifications & Communication

**The system shall** maintain a persistent notification center.

| Recipient | Trigger Events |
|---|---|
| **Staff** | New shift assigned, shift changed, swap request received (as Staff B), swap resolved, schedule published, drop picked up, drop expired |
| **Manager** | Swap/drop approval needed, overtime warning, staff availability changed, staff de-certification at their location |

| AC | Acceptance Criteria |
|---|---|
| AC-10.1 | Users configure preferences: in-app only, or in-app + simulated email |
| AC-10.2 | All notifications persisted with `read_at` timestamp (`NULL` = unread) |
| AC-10.3 | Notification center shows unread count badge and paginated list |

---

### FR-11: Timezone & Calendar Handling

**The system shall** correctly handle all timezone operations without data loss or ambiguity.

| AC | Acceptance Criteria |
|---|---|
| AC-11.1 | All datetime values stored in **UTC** in the database. No local times stored |
| AC-11.2 | Shift times displayed to all users in the **shift location's IANA timezone**, not the viewer's local timezone |
| AC-11.3 | Availability stored as day-of-week + clock time; resolved to UTC using staff's home timezone at evaluation time |
| AC-11.4 | `[AR-05]` **Cross-TZ staff:** A staff member with home TZ `America/Los_Angeles` who sets availability as `09:00–17:00` is available for ET shifts starting at 12:00 ET (= 09:00 PT) or later — not at 09:00 ET (= 06:00 PT) |
| AC-11.5 | `[AR-06]` No split-timezone locations. Each location has exactly one canonical IANA timezone identifier. This is a documented limitation |

---

### FR-12: Audit Trail

**The system shall** log all schedule-related mutations as immutable, append-only records.

| AC | Acceptance Criteria |
|---|---|
| AC-12.1 | Every create/update/delete on shifts, assignments, swaps, and availability generates an entry containing: `actor_id`, `action_type`, `entity_type`, `entity_id`, `before_state (JSON)`, `after_state (JSON)`, `timestamp (UTC)`, `reason (if override)` |
| AC-12.2 | Managers can view full change history of any shift within their location |
| AC-12.3 | Admins can export audit logs filtered by date range and location as CSV |

---

## 6. Evaluation Scenario Flows

### Scenario 1 — The Sunday Night Chaos (Call-Out at 6pm for 7pm Shift)

1. Manager marks the calling-out staff's 7pm shift as open for coverage
2. System immediately notifies all **qualified** staff (correct skill + location cert + availability + no constraint violations) via in-app real-time notification
3. Qualified staff see the shift in their "Available Shifts" feed
4. First eligible staff member claims the shift; optimistic lock prevents double-claim
5. Manager reviews and approves; assignment transfers atomically
6. **Failure path:** No qualified staff → system displays: *"No staff meet all requirements. Consider [specific relaxation suggestion]."*

---

### Scenario 2 — The Overtime Trap

1. Manager attempts to assign Staff X, which would bring them to 52 projected hours
2. **Before confirmation**, what-if preview shows: *"Current: 47hrs + this shift: 5hrs = 52hrs projected. Overtime cost: $X"*
3. Warning fires at 35hrs. System does not auto-block at 40hrs (manager may override)
4. Manager must explicitly acknowledge the overtime warning before confirming
5. OT dashboard updates showing Staff X highlighted with 12 projected overtime hours

---

### Scenario 3 — The Timezone Tangle

1. Staff member certified at PT location (America/Los_Angeles) and ET location (America/New_York)
2. Sets availability: `09:00–17:00` (home TZ = America/Los_Angeles)
3. Manager at ET location attempts to assign them to a shift starting at `09:00 ET`
4. System evaluates: `09:00 ET = 06:00 PT` — outside the 09:00 PT availability window → **constraint violation**
5. Manager at ET location assigns to a shift starting at `14:00 ET` = `11:00 PT` → **valid**

---

### Scenario 4 — Simultaneous Assignment (Two Managers, Same Bartender)

1. Manager A (Location 1) and Manager B (Location 2) both open the assignment modal for the same bartender
2. Manager A submits → PostgreSQL advisory lock acquired → assignment created (version = 1)
3. Manager B submits → lock acquired after A commits → system detects overlap → rejects write
4. Manager B's UI immediately receives: *"Assignment conflict: [Name] was just assigned to a conflicting shift by another manager"*
5. Manager B's view refreshes to reflect the bartender as unavailable

---

### Scenario 5 — The Fairness Complaint

1. Manager opens Fairness Analytics, selects the employee and a 4-week date range
2. System shows: premium shift count for that employee (e.g., 0) vs. team average (e.g., 4.2)
3. Fairness score (standard deviation) shown with visual indicator
4. Distribution table lists all staff sorted by premium shift count — objective, verifiable evidence

---

### Scenario 6 — The Regret Swap

1. Staff A requests swap with Staff B → status: `PENDING_ACCEPTEE`
2. Staff B accepts → status: `PENDING_MANAGER`
3. **Staff A cancels before Manager approves** → `[AR-03]` cancellation is allowed
4. Status → `CANCELLED`; Staff B notified; Manager notified; original assignments remain unchanged

---

## 7. Non-Functional Requirements

| Category | Specification |
|---|---|
| **API Latency** | p95 response time < 300ms for non-real-time requests |
| **WebSocket Delivery** | Real-time events delivered within 2 seconds of trigger |
| **Availability** | 99.5% uptime (internal tool, single org) |
| **Concurrent Users** | Support up to 100 concurrent users across 4 locations |
| **Data Integrity** | Zero tolerance for double-booking or constraint bypass without explicit override |
| **Security** | HTTPS only; JWT auth; RBAC enforced server-side; no client-side role trust |
| **Audit Immutability** | Audit log entries are append-only — no updates, no deletes |
| **Browser Support** | Latest 2 versions: Chrome, Firefox, Safari, Edge |

---

## 8. Documented Assumptions

| ID | Assumption |
|---|---|
| A1 | Admin can perform all Manager actions at any location |
| A2 | Session token expiry: 8 hours of inactivity |
| A3 | Skill list is Admin-configurable |
| A4 | Staff home timezone stored on their user profile |
| A5 | "Schedule" is a logical grouping per week per location |
| A6 | Workweek is Monday–Sunday for overtime calculations |
| A7 | Hourly rate stored per staff profile for OT cost calculation |

---

## 9. Documented Ambiguity Resolutions

| ID | Ambiguity (from Assessment) | Resolution |
|---|---|---|
| AR-01 | What happens to historical data when a staff member is de-certified? | Non-destructive. History preserved. Future shifts unassigned with notification. |
| AR-02 | Does a 1-hour shift count the same as 11 hours for consecutive days? | Yes. Any calendar day with ≥1 minute of shift time counts as a worked day. |
| AR-03 | If a swap is pending and Staff A changes their mind? | Staff A can cancel before Manager approval, even post-Staff B acceptance. |
| AR-04 | How should "desired hours" interact with availability windows? | Desired hours is analytics-only. Not an assignment eligibility gate. |
| AR-05 | Staff certified at PT and ET location sets availability as "9am-5pm" — what happens? | Interpreted in staff's home timezone. Resolved to UTC at evaluation. |
| AR-06 | How should the system handle a location spanning a timezone boundary? | Not supported. One canonical IANA TZ per location. Documented limitation. |

---

## 10. Risks & Open Questions

- **Risk:** DST transition edge cases (spring-forward/fall-back) could produce ambiguous availability windows — requires explicit test coverage
- **Risk:** Real-time concurrency under horizontal API scaling would require Redis Pub/Sub for WebSocket fan-out (not needed at current scale)
- **Open Question:** Should "published" status be per-shift or per-week-schedule block? **Decision:** Per-week publishing is more operationally intuitive; individual shift editing remains possible post-publish with 48hr cutoff enforcement

---

## 11. Success Metrics

| Metric | Target |
|---|---|
| Constraint enforcement accuracy | 100% — no false passes on hard rules |
| Double-booking prevention | 0 double-books allowed through the system |
| Real-time delivery latency | < 2 seconds p95 |
| Overtime detection coverage | 100% of tested evaluation scenarios |
| Concurrent conflict detection | 100% — zero silent overwrites |
| Fairness analytics accuracy | Matches manual calculation against seed dataset |
