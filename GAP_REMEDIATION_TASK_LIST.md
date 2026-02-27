# ShiftSync Gap Remediation Task List

## Scope
Close the functional gaps identified in the PRD traceability audit and add regression coverage.

## Priority P0 (Core Correctness / Data Integrity)
- [x] Implement true atomic swap transfer (two assignments exchanged in one transaction).
- [x] Preserve shift assignment integrity + audit trail during swap approvals.
- [x] Auto-cancel pending swaps when a related shift is edited.
- [x] On staff de-certification, unassign all future assignments at that location and notify managers.
- [x] Add missing audit entries for background/automatic state transitions (drop expiry).

## Priority P1 (Real-Time + Workflow Reliability)
- [x] Emit realtime shift-change events to affected staff users in addition to location subscribers.
- [x] Align frontend websocket event names with backend (`schedule.published`, `schedule.updated`).
- [x] Ensure concurrent assignment conflict paths produce explicit conflict events.
- [x] Add manager notifications for drop-expiry events.

## Priority P2 (Compliance / UX Completeness)
- [x] Implement simulated email dispatch path for users with `in_app_email` preference.
- [x] Add notification triggers for availability changes and de-certification impact.
- [x] Sort fairness report rows by scheduling variance (vs desired hours), not name.
- [x] Add optional 1-minute polling fallback for on-duty dashboard when websocket is unavailable.
- [x] Add session activity refresh hook to approximate inactivity-based expiration.

## Tests (Required)
- [ ] Unit tests for new helper/business logic:
  - [x] Swap atomic transfer helper behavior.
  - [x] Shift-edit pending swap cancellation helper.
  - [ ] De-certification future-unassignment helper.
  - [x] Simulated email dispatch selection logic.
- [ ] Integration/API tests for:
  - [x] Swap approval exchanges assignments atomically.
  - [ ] Shift update auto-cancels pending swaps.
  - [ ] De-certification revokes future assignments and emits notifications.
  - [x] Drop expiry records audit + notifications.
  - [x] Fairness endpoint ordering by variance.
- [ ] End-to-end smoke:
  - [x] Update smoke script to current API routes.
  - [ ] Validate realtime event delivery names.
  - [ ] Validate critical PRD scenarios continue to pass.

## Completion Criteria
- [x] All P0 items completed.
- [x] P1/P2 items completed or explicitly documented as deferred.
- [x] New tests pass locally.
- [x] Existing tests pass locally.
