# ShiftSync — Database Architecture
### Database Architect | Priority Soft Assessment

---

> **Skill Applied:** `database-architect`
> **Input:** PRD + System Design + API Architecture
> **Philosophy:** Design for change. Optimize for dominant access patterns. Every decision justified.

---

## 1. Executive Summary

| Store | Technology | Purpose |
|---|---|---|
| **Primary DB** | PostgreSQL 15 | All transactional data — shifts, assignments, swaps, users, audit logs |
| **Cache / Sessions** | Redis 7 | JWT session management, WebSocket connection state, rate-limiting counters |
| **Read Replica** | PostgreSQL streaming replica | Analytics queries (overtime dashboard, fairness reports) — isolated from write path |

**Why PostgreSQL over alternatives:**
- ACID transactions are mandatory — the constraint engine, assignment insert, audit log, and notification must all succeed or all fail atomically
- `pg_advisory_lock` provides per-user locking for concurrent assignment safety
- Native `TIMESTAMPTZ` + `AT TIME ZONE` for correct timezone arithmetic
- `JSONB` for flexible audit log before/after state storage
- Partial indexes and expression indexes for efficient access patterns
- Well-understood operational model; straightforward backup and restore

**Why not NoSQL:** The data is highly relational (users ↔ skills ↔ certifications ↔ locations ↔ shifts ↔ assignments). Denormalization would require duplicating constraint-check logic in multiple places, creating drift risk on the most critical correctness guarantee in the system.

---

## 2. Data Domain Overview

### Core Domains

| Domain | Key Entities | Write Frequency | Read Frequency |
|---|---|---|---|
| Identity | users, skills, certifications | Low (admin ops) | High (every constraint check) |
| Scheduling | shifts, shift_assignments | Medium (weekly publish cycles) | Very High (schedule views) |
| Workflow | swap_requests | Medium (staff-initiated) | Medium |
| Communication | notifications | High (every mutation generates notifications) | High (notification polling) |
| Compliance | audit_logs | High (every mutation generates an entry) | Low (on-demand review/export) |
| Availability | availability | Low (staff self-service) | High (every constraint check) |

### Dominant Access Patterns

These patterns drive every indexing and schema decision:

| Pattern | Frequency | Critical For |
|---|---|---|
| "Give me all assignments for user X in the past ±24 hours" | High | Constraint engine double-booking + rest period checks |
| "Give me all shifts for location L in week W" | Very High | Schedule view page load |
| "Give me all active certifications for user X" | High | Constraint engine cert check |
| "Give me user X's availability for a given day-of-week + date" | High | Constraint engine availability check |
| "Give me all shifts for user X in the current Mon–Sun week" | High | Constraint engine weekly hours check |
| "Give me all audit log entries for location L between date A and B" | Low | Admin audit export |
| "Give me all unread notifications for user X" | High | Notification badge on every page load |

---

## 3. Entity Relationship Map

```
users
  ├──< user_skills >── skills
  ├──< user_location_certifications >── locations
  ├──< manager_location_assignments >── locations
  └──< availability

locations
  └──< shifts

shifts
  ├──> locations
  ├──> skills (required_skill_id)
  └──< shift_assignments >── users

shift_assignments
  └──< swap_requests

users ──< notifications

ALL mutations ──────────────────────────> audit_logs
```

---

## 4. Full Schema (PostgreSQL DDL)

### `users`

```sql
CREATE TABLE users (
  id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name                    VARCHAR(255) NOT NULL,
  email                   VARCHAR(255) NOT NULL UNIQUE,
  password_hash           VARCHAR(255) NOT NULL,
  role                    VARCHAR(20)  NOT NULL
                          CHECK (role IN ('admin', 'manager', 'staff')),
  home_timezone           VARCHAR(100) NOT NULL DEFAULT 'America/New_York',
  desired_hours_per_week  INTEGER DEFAULT 40,
  hourly_rate             DECIMAL(8,2),                  -- For overtime cost calculation [A7]
  notification_pref       VARCHAR(20) DEFAULT 'in_app'
                          CHECK (notification_pref IN ('in_app', 'in_app_email')),
  is_active               BOOLEAN DEFAULT TRUE,
  created_at              TIMESTAMPTZ DEFAULT NOW(),
  updated_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_role     ON users(role);
CREATE INDEX idx_users_email    ON users(email);
CREATE INDEX idx_users_active   ON users(is_active) WHERE is_active = TRUE;
```

---

### `locations`

```sql
CREATE TABLE locations (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name            VARCHAR(255) NOT NULL,
  address         TEXT,
  iana_timezone   VARCHAR(100) NOT NULL,   -- e.g., 'America/Los_Angeles', 'America/New_York'
  is_active       BOOLEAN DEFAULT TRUE,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Seed data: 4 locations across 2 timezones
-- 'Ocean Ave'       America/Los_Angeles
-- 'Pier 39'         America/Los_Angeles
-- 'Midtown Bistro'  America/New_York
-- 'Brooklyn Tap'    America/New_York
```

---

### `skills`

```sql
CREATE TABLE skills (
  id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name  VARCHAR(100) NOT NULL UNIQUE
);

-- Seed: 'bartender', 'line cook', 'server', 'host'
-- Admin-extensible [A3]
```

---

### `user_skills`

```sql
CREATE TABLE user_skills (
  user_id   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  skill_id  UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
  PRIMARY KEY (user_id, skill_id)
);

CREATE INDEX idx_user_skills_skill ON user_skills(skill_id);
-- Supports: "which users have skill X?" (used for swap suggestions)
```

---

### `user_location_certifications`

Implements `[AR-01]`: de-certification is non-destructive. `revoked_at IS NULL` = active cert.

```sql
CREATE TABLE user_location_certifications (
  user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  location_id   UUID NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
  certified_at  TIMESTAMPTZ DEFAULT NOW(),
  revoked_at    TIMESTAMPTZ,          -- NULL = active certification
  revoked_by    UUID REFERENCES users(id),
  PRIMARY KEY (user_id, location_id)  -- One record per user-location pair; revocation updates it
);

-- Ensures only one active cert per user per location
CREATE UNIQUE INDEX idx_active_cert_per_user_location
  ON user_location_certifications(user_id, location_id)
  WHERE revoked_at IS NULL;

CREATE INDEX idx_cert_by_location
  ON user_location_certifications(location_id)
  WHERE revoked_at IS NULL;
-- Supports: "which active staff are certified at location X?" (manager user listing)
```

---

### `manager_location_assignments`

```sql
CREATE TABLE manager_location_assignments (
  manager_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  location_id   UUID NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
  assigned_at   TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (manager_id, location_id)
);

CREATE INDEX idx_manager_locations ON manager_location_assignments(manager_id);
-- Supports: JWT population on login — "what locations does this manager own?"
```

---

### `availability`

Stores clock-time semantics for correct DST handling. Resolved to UTC at evaluation time.

```sql
CREATE TABLE availability (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  avail_type      VARCHAR(20) NOT NULL
                  CHECK (avail_type IN ('recurring', 'exception')),

  -- For recurring entries: day of week (0=Sunday ... 6=Saturday)
  day_of_week     SMALLINT CHECK (day_of_week BETWEEN 0 AND 6),

  -- For exception entries: the specific calendar date
  specific_date   DATE,

  -- Clock times in user's home_timezone (NOT UTC)
  -- NULL start_clock + NULL end_clock with is_available=FALSE = unavailable all day
  start_clock     TIME,
  end_clock       TIME,
  is_available    BOOLEAN DEFAULT TRUE,

  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW(),

  CONSTRAINT chk_avail_type CHECK (
    (avail_type = 'recurring' AND day_of_week IS NOT NULL AND specific_date IS NULL)
    OR
    (avail_type = 'exception' AND specific_date IS NOT NULL AND day_of_week IS NULL)
  )
);

CREATE INDEX idx_avail_user_type     ON availability(user_id, avail_type);
CREATE INDEX idx_avail_exception     ON availability(user_id, specific_date)
  WHERE avail_type = 'exception';
-- Supports: "does user X have an exception for date D?" (lookup before falling back to recurring)
```

---

### `shifts`

```sql
CREATE TABLE shifts (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  location_id       UUID NOT NULL REFERENCES locations(id),
  required_skill_id UUID NOT NULL REFERENCES skills(id),

  -- Calendar date in the location's timezone (for display and week grouping)
  shift_date        DATE NOT NULL,

  -- All times stored in UTC
  start_utc         TIMESTAMPTZ NOT NULL,
  end_utc           TIMESTAMPTZ NOT NULL,

  headcount_needed  INTEGER NOT NULL DEFAULT 1 CHECK (headcount_needed >= 1),
  status            VARCHAR(20) NOT NULL DEFAULT 'draft'
                    CHECK (status IN ('draft', 'published', 'cancelled')),

  -- Monday of the schedule week (for weekly grouping queries)
  week_start        DATE NOT NULL,

  published_at      TIMESTAMPTZ,
  -- 48 hours before the earliest shift in the published week [A5]
  edit_cutoff_utc   TIMESTAMPTZ,

  created_by        UUID REFERENCES users(id),
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  updated_at        TIMESTAMPTZ DEFAULT NOW(),

  CONSTRAINT chk_shift_times CHECK (end_utc > start_utc)
);

-- Primary schedule view query
CREATE INDEX idx_shifts_location_week   ON shifts(location_id, week_start);
CREATE INDEX idx_shifts_location_date   ON shifts(location_id, shift_date);

-- Overlap detection for constraint engine
CREATE INDEX idx_shifts_start_utc       ON shifts(start_utc);

-- Status filter for publish/unpublish flows
CREATE INDEX idx_shifts_status          ON shifts(status);

-- Premium shift detection:
-- A shift is "premium" if it starts between 17:00-23:59 in the location's timezone
-- on a Friday or Saturday. Computed at query time using AT TIME ZONE:
-- EXTRACT(DOW FROM start_utc AT TIME ZONE location.iana_timezone) IN (5, 6)
-- AND EXTRACT(HOUR FROM start_utc AT TIME ZONE location.iana_timezone) >= 17
```

---

### `shift_assignments`

```sql
CREATE TABLE shift_assignments (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  shift_id        UUID NOT NULL REFERENCES shifts(id) ON DELETE CASCADE,
  user_id         UUID NOT NULL REFERENCES users(id),

  status          VARCHAR(20) NOT NULL DEFAULT 'assigned'
                  CHECK (status IN ('assigned', 'swap_pending', 'dropped', 'removed')),

  -- Optimistic locking for concurrent swap state transitions
  version         INTEGER NOT NULL DEFAULT 1,

  assigned_by     UUID NOT NULL REFERENCES users(id),
  override_reason TEXT,    -- Required when 7th consecutive day or post-cutoff edit

  assigned_at     TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW(),

  -- DB-level backstop: prevents application-layer constraint bypass
  -- (e.g., direct DB access, bug in constraint engine)
  UNIQUE (shift_id, user_id)
);

-- Critical for constraint engine: "all assignments for user X"
CREATE INDEX idx_assignments_user           ON shift_assignments(user_id);

-- Filtered query: "active assignments for user X" (most common)
CREATE INDEX idx_assignments_user_active    ON shift_assignments(user_id, status)
  WHERE status = 'assigned';

-- Shift assignment list (for managers reviewing a specific shift)
CREATE INDEX idx_assignments_shift          ON shift_assignments(shift_id);
```

---

### `swap_requests`

```sql
CREATE TABLE swap_requests (
  id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  type                      VARCHAR(10) NOT NULL CHECK (type IN ('swap', 'drop')),
  requester_assignment_id   UUID NOT NULL REFERENCES shift_assignments(id),
  target_user_id            UUID REFERENCES users(id),  -- NULL for drop requests

  status                    VARCHAR(30) NOT NULL DEFAULT 'PENDING_ACCEPTEE'
                            CHECK (status IN (
                              'PENDING_ACCEPTEE', 'PENDING_MANAGER',
                              'APPROVED', 'REJECTED', 'CANCELLED', 'EXPIRED'
                            )),

  initiated_at              TIMESTAMPTZ DEFAULT NOW(),
  expires_at                TIMESTAMPTZ,    -- Populated for drop requests: shift.start_utc - 24hr
  resolved_at               TIMESTAMPTZ,
  resolved_by               UUID REFERENCES users(id),
  resolution_note           TEXT,

  CONSTRAINT chk_swap_target CHECK (
    type = 'drop' OR target_user_id IS NOT NULL
  )
);

-- Expiry cron job: find drops due for expiration
CREATE INDEX idx_swap_expires
  ON swap_requests(expires_at)
  WHERE status IN ('PENDING_ACCEPTEE', 'PENDING_MANAGER');

-- Staff viewing their own swap history
CREATE INDEX idx_swap_requester
  ON swap_requests(requester_assignment_id);

-- Staff B seeing incoming swap requests
CREATE INDEX idx_swap_target
  ON swap_requests(target_user_id)
  WHERE status = 'PENDING_ACCEPTEE';

-- Manager approval queue
CREATE INDEX idx_swap_pending_manager
  ON swap_requests(status)
  WHERE status = 'PENDING_MANAGER';
```

---

### `notifications`

```sql
CREATE TABLE notifications (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type        VARCHAR(60) NOT NULL,
  -- Examples: 'shift.assigned', 'swap.approved', 'schedule.published',
  --           'drop.expired', 'overtime.warning'
  payload     JSONB NOT NULL,            -- Flexible event-specific data
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  read_at     TIMESTAMPTZ                -- NULL = unread
);

-- Notification center: paginated list for a user, newest first
CREATE INDEX idx_notif_user_created
  ON notifications(user_id, created_at DESC);

-- Unread badge count: partial index on only unread rows
CREATE INDEX idx_notif_unread
  ON notifications(user_id, read_at)
  WHERE read_at IS NULL;

-- Cleanup job: remove notifications older than 90 days
-- DELETE FROM notifications WHERE created_at < NOW() - INTERVAL '90 days';
```

---

### `audit_logs`

Append-only. No `UPDATE`. No `DELETE`. Application DB role has `INSERT`-only access on this table.

```sql
CREATE TABLE audit_logs (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_id      UUID NOT NULL REFERENCES users(id),
  action_type   VARCHAR(60) NOT NULL,
  -- Examples: 'shift.create', 'shift.assign', 'shift.publish', 'shift.unassign',
  --           'swap.approve', 'swap.cancel', 'availability.update', 'cert.revoke'
  entity_type   VARCHAR(60) NOT NULL,
  -- Examples: 'shift', 'assignment', 'swap_request', 'availability', 'certification'
  entity_id     UUID NOT NULL,
  before_state  JSONB,   -- NULL for CREATE operations
  after_state   JSONB,   -- NULL for DELETE operations
  reason        TEXT,    -- Required for: 7th consecutive day, post-cutoff edit, de-certification
  location_id   UUID REFERENCES locations(id),  -- Denormalized for export filtering
  created_at    TIMESTAMPTZ DEFAULT NOW()
  -- Intentionally no updated_at — this table is APPEND-ONLY
);

-- Admin CSV export: filter by location and date range
CREATE INDEX idx_audit_location_time
  ON audit_logs(location_id, created_at DESC);

-- Shift history view (manager reviewing a specific shift)
CREATE INDEX idx_audit_entity
  ON audit_logs(entity_type, entity_id, created_at DESC);

-- Actor history (who did what — Admin forensic view)
CREATE INDEX idx_audit_actor
  ON audit_logs(actor_id, created_at DESC);
```

---

## 5. Indexing Strategy Summary

| Table | Index | Type | Purpose |
|---|---|---|---|
| `users` | `email` | B-tree unique | O(log n) login lookup |
| `shifts` | `(location_id, week_start)` | B-tree composite | Weekly schedule page — primary access pattern |
| `shifts` | `start_utc` | B-tree | Overlap range scans in constraint engine |
| `shift_assignments` | `user_id` | B-tree | All assignments for a user |
| `shift_assignments` | `(user_id, status) WHERE status='assigned'` | Partial B-tree | Active-only assignments — filters most rows |
| `user_location_certifications` | `(user_id, location_id) WHERE revoked_at IS NULL` | Partial unique | One active cert per user-location pair |
| `availability` | `(user_id, specific_date) WHERE avail_type='exception'` | Partial B-tree | Fast exception lookup before falling back to recurring |
| `swap_requests` | `expires_at WHERE status pending` | Partial B-tree | Cron job expiry scan — only touches relevant rows |
| `notifications` | `(user_id, read_at) WHERE read_at IS NULL` | Partial B-tree | Unread badge count — avoids full table scan |
| `audit_logs` | `(location_id, created_at DESC)` | B-tree | CSV export queries |
| `audit_logs` | `(entity_type, entity_id, created_at DESC)` | B-tree | Shift history panel |

**Partial indexes** are used throughout to keep index size small and maintenance cost low. They are effective here because the most important access patterns filter on status columns with high cardinality in the excluded direction (most assignments are `assigned`, not `swap_pending`; most notifications are `read`, not `null`).

---

## 6. Consistency, Transactions & Integrity

### Assignment Write Transaction

Every assignment creation follows this pattern:

```sql
BEGIN;
  -- 1. Acquire per-user advisory lock (prevents concurrent double-booking for this user)
  SELECT pg_advisory_xact_lock(hashtext(:userId::text));

  -- 2. Constraint engine reads execute INSIDE the lock
  --    (ensures the reads are consistent with what we're about to write)
  --    (reads: user certifications, existing assignments ±24h, weekly hours, consecutive days)

  -- 3. Insert the assignment
  INSERT INTO shift_assignments (shift_id, user_id, status, version, assigned_by, override_reason)
  VALUES (:shiftId, :userId, 'assigned', 1, :managerId, :overrideReason);
  -- If UNIQUE(shift_id, user_id) fires → 23505 → transaction rolls back → HTTP 409

  -- 4. Append audit log entry (same transaction — always consistent with assignment)
  INSERT INTO audit_logs (actor_id, action_type, entity_type, entity_id, after_state, location_id)
  VALUES (:managerId, 'shift.assign', 'assignment', :assignmentId, :afterState, :locationId);

  -- 5. Insert notification records
  INSERT INTO notifications (user_id, type, payload)
  VALUES (:staffId, 'shift.assigned', :payload);

COMMIT;

-- After commit: emit WebSocket events (never emit for rolled-back transactions)
```

### Optimistic Locking for Swap Transitions

```sql
-- Swap state transition (e.g., Staff B accepts)
UPDATE swap_requests
SET    status = 'PENDING_MANAGER', version = version + 1
WHERE  id = :swapRequestId
  AND  version = :expectedVersion;

-- If 0 rows updated → someone else changed it first → HTTP 409
```

### Isolation Level

`READ COMMITTED` (PostgreSQL default) is correct for our access patterns. The advisory lock on `userId` within the transaction prevents the phantom-read scenario that would otherwise require `SERIALIZABLE`. Using `READ COMMITTED` avoids the performance cost of serialization conflicts while achieving the same correctness for our specific case.

---

## 7. Timezone Query Patterns

All times in the database are `TIMESTAMPTZ` (UTC). Display conversion happens at the API layer using the location's `iana_timezone`.

**Premium shift detection query example:**
```sql
SELECT
  sa.user_id,
  COUNT(*) FILTER (
    WHERE
      EXTRACT(DOW FROM s.start_utc AT TIME ZONE l.iana_timezone) IN (5, 6)
      AND EXTRACT(HOUR FROM s.start_utc AT TIME ZONE l.iana_timezone) >= 17
  ) AS premium_shift_count
FROM shift_assignments sa
JOIN shifts s ON s.id = sa.shift_id
JOIN locations l ON l.id = s.location_id
WHERE
  s.location_id = :locationId
  AND s.shift_date BETWEEN :startDate AND :endDate
  AND sa.status = 'assigned'
GROUP BY sa.user_id;
```

**Availability resolution (clock-time to UTC via date-fns-tz at application layer):**
```typescript
// NOT done in SQL — done in application layer for testability and DST safety
import { fromZonedTime } from 'date-fns-tz';

function resolveAvailabilityToUTC(clockTime: string, date: Date, timezone: string): Date {
  const dateStr = format(date, 'yyyy-MM-dd');
  return fromZonedTime(`${dateStr}T${clockTime}`, timezone);
  // date-fns-tz handles DST: '09:00 America/Los_Angeles' on Nov 3 2024
  // correctly resolves to UTC-8 (post-DST), not UTC-7 (pre-DST)
}
```

---

## 8. Scaling & Partitioning

**Current scale (< 5 GB total, < 200 users):** No partitioning needed. Single PostgreSQL instance with connection pooling (PgBouncer, pool size = 20).

**Growth triggers for partitioning:**

| Trigger | Action |
|---|---|
| `audit_logs` > 5M rows | Range-partition by `created_at` year |
| `notifications` cleanup complexity | Range-partition by `created_at` month; drop old partitions instead of bulk deletes |
| Analytics queries > 500ms | Create materialized views refreshed every 5 minutes |

**Materialized view for fairness report (if needed):**
```sql
CREATE MATERIALIZED VIEW mv_premium_shift_counts AS
SELECT
  sa.user_id,
  s.location_id,
  DATE_TRUNC('week', s.shift_date) AS week_start,
  COUNT(*) FILTER (
    WHERE EXTRACT(DOW FROM s.start_utc AT TIME ZONE l.iana_timezone) IN (5, 6)
      AND EXTRACT(HOUR FROM s.start_utc AT TIME ZONE l.iana_timezone) >= 17
  ) AS premium_shifts,
  SUM(EXTRACT(EPOCH FROM (s.end_utc - s.start_utc)) / 3600) AS total_hours
FROM shift_assignments sa
JOIN shifts s ON s.id = sa.shift_id
JOIN locations l ON l.id = s.location_id
WHERE sa.status = 'assigned'
GROUP BY sa.user_id, s.location_id, DATE_TRUNC('week', s.shift_date);

CREATE UNIQUE INDEX ON mv_premium_shift_counts (user_id, location_id, week_start);
-- Refresh: REFRESH MATERIALIZED VIEW CONCURRENTLY mv_premium_shift_counts;
-- Scheduled every 5 minutes via node-cron
```

---

## 9. Data Lifecycle Management

| Entity | Retention | Strategy |
|---|---|---|
| **users** | Indefinite | Soft-delete: `is_active = FALSE`. No hard delete. Historical audit references preserved. |
| **shifts** | Indefinite | Soft-cancel: `status = 'cancelled'`. No hard delete. |
| **shift_assignments** | Indefinite | Status transitions only (`removed`, `dropped`). No hard delete. |
| **swap_requests** | Indefinite | Status-based lifecycle. Terminal states: APPROVED, REJECTED, CANCELLED, EXPIRED. |
| **audit_logs** | Indefinite (append-only) | Archive rows older than 2 years to cold storage. Never delete — compliance requirement. |
| **notifications** | 90 days | Background cleanup: `DELETE WHERE created_at < NOW() - INTERVAL '90 days'` |
| **availability** | Indefinite | Full replace on `PUT /availability` — old records soft-replaced, not hard-deleted |

### Schema Evolution Policy

- Migrations managed with Flyway or `node-pg-migrate`
- **Never** rename or drop a column within a major version — add new column, migrate data, deprecate old column with `_deprecated` suffix, remove in next major version
- All migrations are reversible (each `up` migration has a corresponding `down`)
- Migrations run as part of deployment pipeline before API server starts
- Zero-downtime migrations: additive changes (new nullable columns, new tables) are safe; index creation uses `CREATE INDEX CONCURRENTLY`

---

## 10. Security & Compliance

| Control | Implementation |
|---|---|
| **Encryption at rest** | PostgreSQL disk encryption via cloud provider (at OS/volume level) |
| **Encryption in transit** | TLS 1.2+ for all DB connections; `sslmode=require` enforced |
| **Application role** | `shiftsync_app` role: `SELECT`, `INSERT`, `UPDATE` on operational tables; `INSERT`-only on `audit_logs`; no `DROP`, no DDL |
| **PII protection** | `email`, `name`, `hourly_rate` accessible only via authenticated API endpoints — no direct DB export in normal operations |
| **Audit immutability** | DB role cannot `DELETE` or `UPDATE` on `audit_logs`; enforced at PostgreSQL permission level, not just application logic |
| **Password storage** | `bcrypt` with cost factor 12 in `password_hash` — never stored in plaintext or reversible format |
| **Redis security** | Redis auth token required; bind to localhost only; TTL on all keys (`8hr` for session keys matching JWT expiry) |

---

## 11. Reliability & Operations

| Concern | Approach |
|---|---|
| **Backups** | Daily full dump (`pg_dump`) + continuous WAL archiving for point-in-time recovery |
| **RPO** | < 5 minutes (WAL archiving) |
| **RTO** | < 30 minutes (restore from daily dump + WAL replay) |
| **Connection pooling** | PgBouncer in transaction mode; pool size = 20; prevents connection exhaustion under load |
| **Slow query monitoring** | `log_min_duration_statement = 500ms`; alert on any query > 1s |
| **Health monitoring** | Alert on: replication lag > 30s, disk usage > 80%, connection pool exhaustion |
| **Data corruption** | Checksums enabled (`data_checksums = on`); detected at read time before serving to application |
| **Failover** | Streaming replica promoted to primary; DNS update; < 60 seconds in practice |

---

## 12. Trade-offs & Assumptions

| Decision | Trade-off |
|---|---|
| Availability stored as clock-time (not UTC) | Correct DST behavior; requires application-layer UTC resolution on each constraint check. At this scale, the compute cost is negligible. |
| Advisory locks at application layer | Simpler than `SELECT FOR UPDATE` for our use case; doesn't work across multiple DB nodes — acceptable for single-instance architecture. |
| `JSONB` for audit log before/after state | Flexible schema evolution; no structured query over old states (use case doesn't require it). |
| Denormalized `location_id` on `audit_logs` | Slightly increases storage; dramatically simplifies export queries without joins. |
| `UNIQUE(shift_id, user_id)` as backstop | Last-resort protection if application-layer constraint engine has a bug; does not replace the constraint engine (DB error message is less informative than constraint engine message). |

---

## 13. Risks & Open Questions

- **Risk:** As `audit_logs` grows (18,000+ entries/year), the `(entity_type, entity_id)` index query for shift history panels could slow. Mitigation: composite index already planned; partition by year at 5M rows.
- **Risk:** `availability` table clock-time resolution is done in the application layer — if DST edge cases are not covered in test suite, constraint engine bugs could allow incorrect assignments. Mitigation: comprehensive unit tests on `resolveAvailabilityToUTC()` covering spring-forward and fall-back dates.
- **Open:** For the `notifications` cleanup job (90-day retention), should `read` notifications be cleaned up more aggressively (e.g., 30 days) while `unread` notifications are retained longer? **Decision:** Uniform 90-day retention for both — simplicity over optimization at this scale.
