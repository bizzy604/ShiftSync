# ShiftSync — System Design
### FAANG-Grade Architecture | Priority Soft Assessment

---

> **Skill Applied:** `faang-system-design`
> **Input:** PRD from `solutions-architect-prd`
> **Approach:** Constraints-first. Simplest viable architecture. Trade-offs explicit throughout.

---

## 1. Requirements Summary

### Functional (from PRD)
- Multi-role scheduling platform (Admin / Manager / Staff) across 4 locations / 2 timezones
- Constraint-enforced shift assignment with human-readable violation messages
- Shift swap/drop multi-party approval workflow
- Overtime tracking with hard blocks and warnings
- Schedule fairness analytics
- Real-time WebSocket updates for schedule changes, swap events, and concurrent conflicts
- Immutable audit trail with CSV export

### Non-Functional
- API p95 < 300ms
- WebSocket delivery < 2 seconds
- 100 concurrent users peak
- Zero double-bookings (no constraint bypass without explicit override)
- Audit log immutability — append-only, no deletes
- Timezone-correct computation for all datetimes

---

## 2. Capacity Estimation

Starting with honest, defensible math before picking an architecture.

| Metric | Estimate | Reasoning |
|---|---|---|
| Total users | ~150–200 | 4 locations × ~35–50 staff + managers |
| Peak concurrent users | ~60–80 | Dinner rush + schedule publication events |
| Read/Write ratio | 80/20 | Schedule reads dominate; writes on publish + assignment |
| API requests at peak | ~600 req/hr | Schedule reads + assignment confirmations |
| WebSocket connections | ~30–80 | Active managers + staff during peak hours |
| Shifts created/year | ~10,400 | 4 locations × 50 shifts/week × 52 weeks |
| Audit log entries/year | ~18,000 | ~50 changes/day × 365 |
| Notification records/year | ~110,000 | ~300/day × 365 |
| Total data growth/year | **< 5 GB** | Entirely manageable on a single PostgreSQL instance |

**Conclusion:** This is a small-to-medium internal tool. The correct architecture is a **well-structured modular monolith** — not microservices, not Kafka, not multi-region replication. We accept this trade-off explicitly: simpler operations, simpler transactions, zero cross-service network calls within the constraint engine.

---

## 3. Architecture Decision: Modular Monolith

### Why not microservices?

| Consideration | Analysis |
|---|---|
| Domain coupling | The Constraint Engine needs availability, certifications, and assignments in a single atomic transaction. Splitting this across services breaks atomicity or requires distributed sagas — enormous added complexity with zero user benefit. |
| Scale | 100 concurrent users does not justify the ops overhead of service discovery, inter-service auth, and distributed tracing. |
| Extraction path | Code is organized as independent modules (SchedulingService, SwapService, NotificationService, AuditService, AnalyticsService). Any module can be extracted to a separate service if scale demands it. |

**We accept** the trade-off: modular monolith is harder to scale individual components independently. At < 200 users, this cost never materializes.

---

## 4. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                             │
│         React SPA (Web Browser — Chrome / Firefox / Safari)     │
│         Socket.IO WebSocket Client                              │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS / WSS
┌────────────────────────────▼────────────────────────────────────┐
│                  API GATEWAY / REVERSE PROXY                    │
│                       (Nginx)                                   │
└──────────┬──────────────────────────────────────┬───────────────┘
           │ REST/HTTP                            │ WebSocket
┌──────────▼──────────────┐           ┌───────────▼───────────────┐
│     REST API Server     │           │    WebSocket Server        │
│   (Python / FastAPI)   │           │    (Socket.IO)             │
│   Stateless · RBAC      │           │    Same Node process (v1)  │
└──────────┬──────────────┘           └───────────┬───────────────┘
           │                                      │
┌──────────▼──────────────────────────────────────▼───────────────┐
│                        SERVICE LAYER                            │
│                                                                 │
│   ConstraintEngine  │  SchedulingService  │  SwapService        │
│   NotificationService  │  AuditService  │  AnalyticsService     │
└──────────────────────────────┬──────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
┌───────▼────────┐   ┌─────────▼────────┐   ┌────────▼───────────┐
│  PostgreSQL 15 │   │  PostgreSQL Read  │   │      Redis 7       │
│  (Primary)     │   │  Replica          │   │  Sessions / WS     │
│  Transactional │   │  Analytics queries│   │  Rate limiting     │
└────────────────┘   └──────────────────┘   └────────────────────┘
```

**Data flow summary:**
- All writes → REST API → Service Layer → PostgreSQL Primary (transactional)
- Analytics reads → REST API → AnalyticsService → PostgreSQL Read Replica
- Real-time events → WebSocket Server → Socket.IO rooms → connected clients
- Session validation → Redis (sub-millisecond lookup)

---

## 5. Detailed Component Design

### 5.1 Constraint Engine

The most critical component. Designed as a **pure, stateless TypeScript module** with zero side effects — it never writes to the database and can be unit-tested in complete isolation.

```
Input:
  { shift, user, existingAssignments }

Processing:
  Runs all 8 constraint checks in sequence
  Collects ALL violations — does NOT short-circuit on first failure
  (Managers need to see the complete picture)

Output:
  {
    valid: boolean,
    violations: [{ rule, severity, description }],
    warnings:   [{ rule, description }],
    suggestions: [{ userId, name, reason }]
  }
```

**The 8 checks (in execution order):**

| # | Check | Data Required |
|---|---|---|
| 1 | Skill match | `user.skills`, `shift.requiredSkillId` |
| 2 | Location certification | `user.certifications`, `shift.locationId` |
| 3 | Availability (DST-safe) | `user.availability`, `user.homeTimezone`, `shift.startUtc`, `shift.endUtc` |
| 4 | No double-booking (half-open interval overlap) | `existingAssignments` (all user assignments ±24h of proposed) |
| 5 | Rest period (10hr minimum gap) | `existingAssignments` nearest before/after |
| 6 | Daily hours (8hr warn / 12hr hard block) | `existingAssignments` on same calendar day |
| 7 | Weekly hours (35hr warning threshold) | `existingAssignments` in same Mon–Sun week |
| 8 | Consecutive days (6th warn / 7th override) | `existingAssignments` prior 6 calendar days |

**Why application layer, not database triggers?**
Richer error messages with specific values, alternative suggestions, and the ability to run "what-if" previews without writing to the database. Database-level `UNIQUE(shift_id, user_id)` constraint serves as the final backstop.

---

### 5.2 Concurrency Control — Simultaneous Assignment

Two managers assigning the same bartender at the same time (Evaluation Scenario 4):

```sql
BEGIN;
  -- Acquire per-user advisory lock for the duration of this transaction
  -- Second concurrent transaction blocks here until first commits
  SELECT pg_advisory_xact_lock(hashtext(:userId));
  
  -- Constraint engine reads run inside the lock
  -- (guarantees reads are consistent with the write that follows)
  
  INSERT INTO shift_assignments (...) VALUES (...);
  INSERT INTO audit_logs (...) VALUES (...);
  INSERT INTO notifications (...) VALUES (...);
COMMIT;

-- After commit: fire WebSocket events
-- (never fire events for rolled-back transactions)
```

When the second writer acquires the lock after the first commits, the constraint engine detects the newly created overlapping assignment → returns `HTTP 409` → server emits `assignment.conflict` WebSocket event to the second manager's client.

**Trade-off:** Advisory locks are per-PostgreSQL-instance. Under horizontal API scaling, we would switch to `SELECT FOR UPDATE` row locking or Redis distributed locks. Not needed at this scale.

---

### 5.3 Swap Request State Machine

```
                          ┌─────────────────────┐
                          │   PENDING_ACCEPTEE  │  (initial state)
                          └─────────┬───────────┘
                                    │
              ┌─────────────────────┼──────────────────────┐
              │ Staff B accepts     │ Staff B rejects       │ Staff A cancels
              ▼                     ▼                       ▼
   ┌──────────────────┐     ┌──────────────┐       ┌─────────────┐
   │ PENDING_MANAGER  │     │   REJECTED   │       │  CANCELLED  │
   └────────┬─────────┘     └──────────────┘       └─────────────┘
            │
  ┌─────────┼──────────────────────────────────┐
  │ Approve │ Reject       │ Staff A cancels    │ Shift edited by manager
  ▼         ▼              ▼                    ▼
APPROVED  REJECTED     CANCELLED            CANCELLED (auto-notify all)
```

**Drop requests** follow a simplified path: `OPEN → PENDING_MANAGER → APPROVED | REJECTED | EXPIRED`

Expiry is handled by a background job running every 15 minutes:
```sql
UPDATE swap_requests
SET status = 'EXPIRED'
WHERE type = 'drop'
  AND status IN ('OPEN', 'PENDING_MANAGER')
  AND expires_at < NOW();
```

Expiry is also double-checked defensively at pickup time — guard against cron failure.

---

### 5.4 Real-Time WebSocket Architecture

```
On client connect:
  1. Authenticate via JWT
  2. Auto-join: room "user:{userId}"
  3. If Manager: auto-join "location:{locationId}" for each assigned location

Event routing:
  schedule.published     → location:{locationId} room
  schedule.updated       → location:{locationId} room
  assignment.changed     → user:{affectedUserId} room
  swap.status_changed    → user:{allInvolvedUserIds} rooms
  notification.new       → user:{recipientId} room
  assignment.conflict    → user:{conflictingManagerId} room (not broadcast)
```

**Horizontal scaling path** (not needed for v1): Extract WebSocket server to separate process. Use Redis Pub/Sub for cross-process event delivery. API servers publish events to Redis channel; WebSocket process subscribes and fans out to connected clients.

---

### 5.5 Audit Service

Called within every mutating database transaction:

```typescript
// Called synchronously INSIDE the transaction — not after
await AuditService.log({
  actorId:     req.user.id,
  actionType:  'shift.assign',
  entityType:  'assignment',
  entityId:    assignment.id,
  beforeState: null,           // null for creates
  afterState:  assignment,
  reason:      overrideReason ?? null,
  locationId:  shift.locationId,
});
```

**Immutability enforcement:** The application role in PostgreSQL has `INSERT`-only access on `audit_logs`. No `UPDATE` or `DELETE` is possible from application code. Admin CSV exports stream query results directly — no in-memory aggregation of large datasets.

---

## 6. Scalability Plan

For current scale (< 200 users, single org):

| Component | Current Approach | Scale-Up Path |
|---|---|---|
| API Server | Single FastAPI process | Horizontal scaling behind Nginx; sticky sessions for WebSocket or extract to separate process |
| Database | Single PostgreSQL instance + connection pooling (PgBouncer) | Add read replica (analytics only); partition `audit_logs` by year at ~10M rows |
| WebSocket | Socket.IO in same Node process | Extract to separate process + Redis Pub/Sub for cross-process fan-out |
| Cache | Redis single instance | Redis Cluster if session volume grows |
| Analytics queries | Read replica | Materialized views refreshed every 5 minutes for heavy fairness reports |

---

## 7. Reliability & Fault Tolerance

| Failure Scenario | Detection | Response |
|---|---|---|
| DB connection lost | Connection pool error | API returns `503`; client retries with exponential backoff |
| WebSocket disconnect | Socket.IO heartbeat timeout | Client auto-reconnects; on reconnect, REST API polls for missed events |
| Constraint engine bug (false pass) | `UNIQUE(shift_id, user_id)` DB constraint | Transaction rolls back with `23505` unique violation → API returns `409` |
| Two managers, same staff, simultaneous | PostgreSQL advisory lock | Second writer blocked until first commits; conflict detected and reported |
| Swap expiry cron failure | Defensive check at pickup time | Even if cron misses, expired drops are rejected at the pickup API call |
| Long analytics query blocking writes | Read replica routing | Analytics endpoints routed to replica; writes never blocked |
| Node process crash | Process manager (PM2) | Auto-restart within seconds; Redis sessions survive restart |

**ACID guarantee on every assignment write:** Constraint check reads + assignment insert + audit log insert + notification insert — all in a single PostgreSQL transaction. Either all succeed or all roll back. WebSocket events fire only after successful commit.

---

## 8. Consistency & Data Integrity

**Strong consistency** is required for all scheduling operations — there is no acceptable scenario where a double-booking appears temporarily valid.

**Strategy:**
- PostgreSQL `READ COMMITTED` isolation (default) combined with advisory locks provides correct behavior for our access patterns
- `UNIQUE(shift_id, user_id)` constraint = database-level absolute backstop
- All schedule mutations are synchronous and transactional — no eventual consistency in the write path
- Optimistic locking (`version` field on `shift_assignments`) for swap state transitions

**We accept eventual consistency only for:** notification delivery (notifications persisted in the same transaction, but WebSocket delivery is best-effort with fallback to read on reconnect) and analytics reports (read replica lag up to ~100ms).

---

## 9. Security Architecture

| Layer | Control |
|---|---|
| Transport | HTTPS/TLS 1.2+ enforced on all traffic; HSTS headers |
| Authentication | JWT (RS256); stored in HttpOnly cookie — prevents XSS token theft |
| Authorization | Role extracted from verified JWT server-side; never trusted from request body |
| SQL Injection | All queries via parameterized statements (ORM-enforced) |
| Audit attribution | `actor_id` written from verified JWT, never from client-supplied request field |
| Rate limiting | 10 req/min on auth endpoints; 300 req/min on general API; enforced at Nginx |
| DB access control | App role has no `DROP`, no DDL, no `DELETE` on `audit_logs` |
| PII protection | No raw DB exports outside authorized API flows |

---

## 10. Observability & Operations

| Concern | Approach |
|---|---|
| **Logging** | Structured JSON logs (Winston/Pino); request ID propagated through all service calls |
| **Metrics** | Node.js process metrics + PostgreSQL slow query log; custom metric for constraint violation rate |
| **Error tracking** | Unhandled exceptions captured with full stack traces |
| **Health checks** | `GET /health` → checks DB connection + Redis ping; used by load balancer |
| **SLO** | API p95 < 300ms; WebSocket delivery < 2s; tracked via response time logging |
| **Alerts** | Alert on: DB connection failures, error rate > 1%, advisory lock wait time > 500ms |

---

## 11. Trade-Off Summary

| Decision | We Chose | We Gave Up | Justified Because |
|---|---|---|---|
| Modular monolith | Simpler transactions, simpler ops | Independent component scaling | Scale doesn't require it at < 200 users |
| App-layer constraint engine | Rich error messages + suggestions | Bypass protection if DB accessed directly | `UNIQUE` constraint is DB-level backstop |
| PostgreSQL advisory locks | Strong consistency, simple implementation | Doesn't work across multiple DB nodes | Single DB node is correct at this scale |
| Socket.IO over raw WebSockets | Auto-reconnect, rooms, polling fallback | Minor protocol overhead | Reliability > micro-optimization |
| Clock-time availability storage | Correct DST behavior | Must re-compute per schedule evaluation | Evaluation is cheap; correctness is mandatory |
| Read replica for analytics | Protects write path from heavy reads | 100ms replication lag on analytics | Analytics data doesn't need real-time accuracy |

---

## 12. Future Improvements

- **Extract Constraint Engine** as a shared library if a mobile app is added
- **Materialized views** for fairness score pre-computation if report latency becomes noticeable
- **Redis Pub/Sub** for WebSocket fan-out when API tier scales horizontally
- **Elasticsearch** for full-text search across audit logs at scale
- **Partitioned `audit_logs`** by year when row count exceeds ~5M
- **Multi-tenant architecture** if Coastal Eats expands to a franchise model
