# Priority Soft Assessment - Access & Test Guide

This file is for evaluators to quickly access ShiftSync, log in by role, and run the required assessment scenarios.

## 1. Application Access

- Public web app: `https://shift-sync-web.vercel.app`
- Backend_url: ``
- Local web app (fallback): `http://localhost:5173`
- Local API docs (fallback): `http://localhost:8000/docs`

If you run locally, use:

```bash
npm install
npm run db:upgrade
python seed/seed.py
python apps/api/run.py
npm run web:dev
```

## 2. Login Accounts

All seeded users have deterministic credentials:

### Admin
- Email: `admin@coastaleats.com`
- Password: `Admin123!`

### Managers
- `jordan@coastaleats.com` / `Manager123!` (Ocean Ave, Midtown Bistro)
- `sam@coastaleats.com` / `Manager123!` (Pier 39, Brooklyn Tap)

### Staff
- `carlos@coastaleats.com` / `Staff123!`
- `maria@coastaleats.com` / `Staff123!`
- `amy@coastaleats.com` / `Staff123!`
- `ben@coastaleats.com` / `Staff123!`
- `alex@coastaleats.com` / `Staff123!`
- `dana@coastaleats.com` / `Staff123!`
- `finn@coastaleats.com` / `Staff123!`
- `luna@coastaleats.com` / `Staff123!`

## 3. Important Seed Notes

- Seed dates are rolling (relative to current week), not hardcoded to one calendar month.
- Scenario data is preloaded for overtime pressure, fairness imbalance, cross-location staffing, and swap/drop workflows.
- Time is stored in UTC and displayed in each location timezone.

## 4. Scenario Playbook (Evaluator Flows)

## Scenario 1: The Sunday Night Chaos
- Login as Manager (`jordan@coastaleats.com`).
- Open `Swap & Drop Requests` (`/manager/swaps`).
- Use an `OPEN` drop request and open **Emergency Coverage**.
- Click **Notify All Qualified** (only enabled while request is `OPEN`).
- Login as a qualified Staff user in another session and open notifications.
- Click the notification and claim from **Open Shifts Available for Pickup**.
- Return to Manager and approve pickup.

Expected:
- Real-time notifications at each step.
- Assignment changes only after manager approval.
- If request is no longer open, staff sees "no longer open for pickup" messaging.

## Scenario 2: The Overtime Trap
- Login as Manager (`jordan@coastaleats.com`).
- In scheduling flow, preview/assign a staff member near weekly threshold (seed includes near-threshold users).
- Open analytics page (`/manager/analytics`).

Expected:
- Warnings at 35+ weekly hours.
- Daily 8h warning and 12h hard block behavior.
- Projected overtime impact visible in analytics.

## Scenario 3: The Timezone Tangle
- Login as Staff (`carlos@coastaleats.com`) to inspect availability setup.
- Login as Manager and attempt assignments across PT/ET certified contexts.

Expected:
- Availability is interpreted in staff home timezone and resolved correctly for shift location timezone.
- Invalid timezone-misaligned assignment attempts are rejected with clear reasons.

## Scenario 4: The Simultaneous Assignment
- Open two sessions:
  - Session A: Manager/Admin assigning a target staff.
  - Session B: Another Manager/Admin assigning same staff to overlapping shift.
- Submit both close together.

Expected:
- One assignment succeeds.
- The conflicting one is rejected with a conflict signal (no silent overwrite).

## Scenario 5: The Fairness Complaint
- Login as Manager (`jordan@coastaleats.com`).
- Open analytics/fairness view (`/manager/analytics`).
- Compare premium shift distribution and hours variance across staff.

Expected:
- Premium (Fri/Sat evening) distribution is visible.
- Fairness score/report supports verifying under/over-allocation claims.

## Scenario 6: The Regret Swap
- Use a pending swap request from seeded data (or create one from Staff schedule).
- Staff A initiates swap, Staff B accepts.
- Before manager approval, Staff A cancels.

Expected:
- Request transitions to `CANCELLED`.
- Original assignment remains unchanged.
- Relevant parties are notified.

## 5. Feature Verification Checklist

- RBAC:
  - Admin sees all.
  - Manager scope restricted to assigned locations.
  - Staff sees only personal workflows.
- Notifications:
  - Persisted and read/unread in notification center.
  - Real-time updates without manual refresh.
- Audit:
  - Admin can inspect/export audit logs (`/admin/audit`).
- Shift history:
  - Manager can review shift-level change history (`/manager/history`).

## 6. Ambiguity Decisions Implemented

- Historical records remain after de-certification; future eligibility is constrained.
- Desired hours are analytics guidance, not a hard assignment gate.
- Consecutive-day logic counts any worked calendar day.
- One canonical timezone per location (no split-timezone location model).

## 7. Known Limits (Scope)

- Email delivery is simulated (in-app notifications are first-class).
- On-duty is schedule-based, not biometric time-clock based.
- Web app only (no native mobile app).
