import asyncio
import json
import os
import subprocess
import time
import traceback
from typing import Any
from datetime import date, timedelta
from pathlib import Path

import httpx
import websockets


ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "apps" / "api"
PORT = int(os.getenv("SMOKE_PORT", "8015"))
BASE = f"http://127.0.0.1:{PORT}"
WS_BASE = f"ws://127.0.0.1:{PORT}/api/v1/realtime/ws"


def wait_for_health(timeout_seconds: int = 60) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            response = httpx.get(f"{BASE}/health", timeout=2.0)
            if response.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError("API health check timed out.")


async def login(client: httpx.AsyncClient, email: str, password: str) -> None:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    if response.status_code != 200:
        raise RuntimeError(f"Login failed for {email}: {response.status_code} {response.text}")


async def recv_events(ws: Any, seconds: float) -> list[str]:
    events: list[str] = []
    end = time.monotonic() + seconds
    while True:
        remaining = end - time.monotonic()
        if remaining <= 0:
            break
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
        except asyncio.TimeoutError:
            break
        message = json.loads(raw)
        event = message.get("event")
        if isinstance(event, str):
            events.append(event)
    return events


def _next_monday(today: date) -> date:
    days_to_next_monday = (7 - today.weekday()) % 7
    next_monday = today + timedelta(days=days_to_next_monday)
    if next_monday <= today:
        next_monday += timedelta(days=7)
    return next_monday


async def run_smoke() -> dict:
    async with (
        httpx.AsyncClient(base_url=BASE, timeout=25.0) as admin,
        httpx.AsyncClient(base_url=BASE, timeout=25.0) as manager,
        httpx.AsyncClient(base_url=BASE, timeout=25.0) as carlos,
        httpx.AsyncClient(base_url=BASE, timeout=25.0) as maria,
    ):
        await login(admin, "admin@coastaleats.com", "Admin123!")
        await login(manager, "jordan@coastaleats.com", "Manager123!")
        await login(carlos, "carlos@coastaleats.com", "Staff123!")
        await login(maria, "maria@coastaleats.com", "Staff123!")

        # Phase 1 checks
        users_response = await admin.get("/api/v1/users")
        assert users_response.status_code == 200, users_response.text
        users = users_response.json()["users"]
        by_email = {item["email"]: item for item in users}
        carlos_id = by_email["carlos@coastaleats.com"]["id"]
        maria_id = by_email["maria@coastaleats.com"]["id"]
        dana_id = by_email["dana@coastaleats.com"]["id"]

        locations_response = await admin.get("/api/v1/locations")
        assert locations_response.status_code == 200, locations_response.text
        locations = locations_response.json()["locations"]
        ocean = next(item for item in locations if item["name"] == "Ocean Ave")
        pier = next(item for item in locations if item["name"] == "Pier 39")
        location_id = ocean["id"]
        pier_id = pier["id"]

        get_availability = await carlos.get(f"/api/v1/users/{carlos_id}/availability")
        assert get_availability.status_code == 200, get_availability.text

        put_availability = await carlos.put(
            f"/api/v1/users/{carlos_id}/availability",
            json={
                "recurring": [
                    {"day_of_week": 1, "start_clock_time": "09:00", "end_clock_time": "17:00"},
                    {"day_of_week": 2, "start_clock_time": "09:00", "end_clock_time": "17:00"},
                    {"day_of_week": 6, "start_clock_time": "17:00", "end_clock_time": "23:59"},
                ],
                "exceptions": [],
            },
        )
        assert put_availability.status_code == 200, put_availability.text

        maria_availability = await maria.put(
            f"/api/v1/users/{maria_id}/availability",
            json={
                "recurring": [
                    {"day_of_week": 0, "start_clock_time": "08:00", "end_clock_time": "23:59"},
                    {"day_of_week": 1, "start_clock_time": "08:00", "end_clock_time": "23:59"},
                    {"day_of_week": 2, "start_clock_time": "08:00", "end_clock_time": "23:59"},
                    {"day_of_week": 3, "start_clock_time": "08:00", "end_clock_time": "23:59"},
                    {"day_of_week": 4, "start_clock_time": "08:00", "end_clock_time": "23:59"},
                    {"day_of_week": 5, "start_clock_time": "08:00", "end_clock_time": "23:59"},
                    {"day_of_week": 6, "start_clock_time": "08:00", "end_clock_time": "23:59"},
                ],
                "exceptions": [],
            },
        )
        assert maria_availability.status_code == 200, maria_availability.text

        skills_response = await admin.get(f"/api/v1/users/{carlos_id}/skills")
        assert skills_response.status_code == 200, skills_response.text
        required_skill_id = skills_response.json()[0]["skill_id"]

        # Phase 2 setup
        monday = _next_monday(date.today())
        day_1 = monday + timedelta(days=1)
        day_2 = monday + timedelta(days=2)
        day_3 = monday + timedelta(days=5)
        day_4 = monday + timedelta(days=6)

        async def create_shift(shift_date: date, start_time: str, end_time: str) -> dict:
            response = await manager.post(
                "/api/v1/shifts",
                params={"location_id": location_id},
                json={
                    "date": shift_date.isoformat(),
                    "start_time": start_time,
                    "end_time": end_time,
                    "required_skill_id": required_skill_id,
                    "headcount_needed": 1,
                },
            )
            assert response.status_code == 200, response.text
            return response.json()

        shift_1 = await create_shift(day_1, "10:00", "14:00")
        shift_2 = await create_shift(day_2, "10:00", "14:00")
        shift_3 = await create_shift(day_3, "18:00", "22:00")
        shift_4 = await create_shift(day_4, "10:00", "14:00")
        shift_5 = await create_shift(day_4, "15:00", "19:00")

        async def assign(shift_id: str, user_id: str, client: httpx.AsyncClient) -> httpx.Response:
            return await client.post("/api/v1/assignments", params={"shift_id": shift_id}, json={"user_id": user_id})

        assignment_1 = await assign(shift_1["id"], carlos_id, manager)
        assert assignment_1.status_code == 200, assignment_1.text
        assignment_1_id = assignment_1.json()["id"]

        assignment_2 = await assign(shift_2["id"], maria_id, manager)
        assert assignment_2.status_code == 200, assignment_2.text
        assignment_2_id = assignment_2.json()["id"]

        assignment_3 = await assign(shift_3["id"], carlos_id, manager)
        assert assignment_3.status_code == 200, assignment_3.text
        assignment_3_id = assignment_3.json()["id"]

        # Phase 3 swap flow
        swap_create = await carlos.post(
            "/api/v1/swaps",
            json={
                "my_assignment_id": assignment_1_id,
                "target_user_id": maria_id,
                "target_assignment_id": assignment_2_id,
            },
        )
        assert swap_create.status_code == 200, swap_create.text
        swap_id = swap_create.json()["id"]

        swap_accept = await maria.post(f"/api/v1/swaps/{swap_id}/accept", json={"note": "ok"})
        assert swap_accept.status_code == 200, swap_accept.text

        swap_approve = await manager.post(f"/api/v1/swaps/{swap_id}/approve", json={"note": "approved"})
        assert swap_approve.status_code == 200, swap_approve.text

        shift_1_assignments = await manager.get("/api/v1/assignments", params={"shift_id": shift_1["id"]})
        assert shift_1_assignments.status_code == 200, shift_1_assignments.text
        assert any(item["user_id"] == maria_id for item in shift_1_assignments.json()["assignments"])

        # Phase 3 drop flow
        drop_create = await carlos.post("/api/v1/swaps/drops", json={"assignment_id": assignment_3_id})
        assert drop_create.status_code == 200, drop_create.text
        drop_id = drop_create.json()["id"]

        drops_available = await maria.get("/api/v1/swaps/drops/available")
        assert drops_available.status_code == 200, drops_available.text
        assert any(item["drop_request_id"] == drop_id for item in drops_available.json()["available"])

        drop_pickup = await maria.post(f"/api/v1/swaps/drops/{drop_id}/pickup", json={"note": "can cover"})
        assert drop_pickup.status_code == 200, drop_pickup.text

        drop_approve = await manager.post(f"/api/v1/swaps/drops/{drop_id}/approve", json={"note": "approved"})
        assert drop_approve.status_code == 200, drop_approve.text

        shift_3_assignments = await manager.get("/api/v1/assignments", params={"shift_id": shift_3["id"]})
        assert shift_3_assignments.status_code == 200, shift_3_assignments.text
        assert any(item["user_id"] == maria_id for item in shift_3_assignments.json()["assignments"])

        # Notifications API
        notifications = await maria.get("/api/v1/notifications")
        assert notifications.status_code == 200, notifications.text
        notifications_json = notifications.json()

        preferences_get = await maria.get("/api/v1/notifications/preferences")
        assert preferences_get.status_code == 200, preferences_get.text

        preferences_put = await maria.put(
            "/api/v1/notifications/preferences",
            json={"notification_pref": "in_app_email"},
        )
        assert preferences_put.status_code == 200, preferences_put.text

        if notifications_json["notifications"]:
            first_notification_id = notifications_json["notifications"][0]["id"]
            mark_one = await maria.put(f"/api/v1/notifications/{first_notification_id}/read")
            assert mark_one.status_code == 200, mark_one.text

        mark_all = await maria.put("/api/v1/notifications/read-all")
        assert mark_all.status_code == 200, mark_all.text

        # WebSocket checks
        manager_token = manager.cookies.get("shiftsync_token")
        maria_token = maria.cookies.get("shiftsync_token")
        assert manager_token and maria_token

        async with (
            websockets.connect(f"{WS_BASE}?token={manager_token}") as manager_ws,
            websockets.connect(f"{WS_BASE}?token={maria_token}") as maria_ws,
        ):
            await manager_ws.send(json.dumps({"event": "ping", "payload": {}}))
            pong = json.loads(await asyncio.wait_for(manager_ws.recv(), timeout=3))
            assert pong.get("event") == "pong", pong

            publish = await manager.post(
                "/api/v1/shifts/publish",
                params={"location_id": location_id},
                json={"week_start": monday.isoformat()},
            )
            assert publish.status_code == 200, publish.text

            manager_events = await recv_events(manager_ws, 2.0)
            maria_events = await recv_events(maria_ws, 2.0)
            assert "schedule.published" in manager_events, manager_events
            assert "schedule.published" in maria_events, maria_events

        # Conflict event check (real concurrent writers)
        admin_token = admin.cookies.get("shiftsync_token")
        manager_token = manager.cookies.get("shiftsync_token")
        assert admin_token and manager_token
        async with (
            websockets.connect(f"{WS_BASE}?token={manager_token}") as manager_ws,
            websockets.connect(f"{WS_BASE}?token={admin_token}") as admin_ws,
        ):
            first, second = await asyncio.gather(
                manager.post("/api/v1/assignments", params={"shift_id": shift_5["id"]}, json={"user_id": maria_id}),
                admin.post("/api/v1/assignments", params={"shift_id": shift_5["id"]}, json={"user_id": maria_id}),
            )
            codes = sorted([first.status_code, second.status_code])
            assert codes == [200, 409], (first.status_code, first.text, second.status_code, second.text)
            manager_events = await recv_events(manager_ws, 2.0)
            admin_events = await recv_events(admin_ws, 2.0)
            assert "assignment.conflict" in (manager_events + admin_events), (manager_events, admin_events)

        # Phase 4 analytics + audit checks
        overtime = await manager.get(
            "/api/v1/analytics/overtime-dashboard",
            params={"location_id": location_id, "week_start": monday.isoformat()},
        )
        assert overtime.status_code == 200, overtime.text
        overtime_json = overtime.json()
        assert overtime_json["location_id"] == location_id

        fairness = await manager.get(
            "/api/v1/analytics/fairness-report",
            params={
                "location_id": location_id,
                "start_date": day_1.isoformat(),
                "end_date": day_4.isoformat(),
            },
        )
        assert fairness.status_code == 200, fairness.text
        fairness_json = fairness.json()
        assert fairness_json["location_id"] == location_id

        distribution = await manager.get(
            "/api/v1/analytics/hours-distribution",
            params={
                "location_id": location_id,
                "start_date": day_1.isoformat(),
                "end_date": day_4.isoformat(),
            },
        )
        assert distribution.status_code == 200, distribution.text

        on_duty = await manager.get("/api/v1/analytics/on-duty", params={"location_id": location_id})
        assert on_duty.status_code == 200, on_duty.text

        audit_list = await manager.get("/api/v1/audit/audit-logs", params={"location_id": location_id})
        assert audit_list.status_code == 200, audit_list.text
        audit_json = audit_list.json()
        assert len(audit_json["logs"]) >= 1

        revoke_cert = await admin.delete(f"/api/v1/users/{dana_id}/certifications/{pier_id}")
        assert revoke_cert.status_code == 200, revoke_cert.text
        cert_audit = await admin.get(
            "/api/v1/audit/audit-logs",
            params={"entity_type": "certification", "location_id": pier_id, "limit": 100},
        )
        assert cert_audit.status_code == 200, cert_audit.text
        cert_logs = cert_audit.json()["logs"]
        assert any(log["action_type"] == "cert.revoke" for log in cert_logs), cert_logs

        audit_export = await admin.get(
            "/api/v1/audit/audit-logs/export",
            params={
                "start_date": (date.today() - timedelta(days=30)).isoformat(),
                "end_date": date.today().isoformat(),
            },
        )
        assert audit_export.status_code == 200, audit_export.text
        assert "text/csv" in audit_export.headers.get("content-type", "")

        return {
            "phase1": {
                "users": len(users),
                "locations": len(locations),
                "availability_updated": True,
            },
            "phase2": {
                "shifts_created": 5,
                "assignments_created": 3,
            },
            "phase3": {
                "swap_approved": swap_id,
                "drop_approved": drop_id,
                "notifications_checked": True,
                "websocket_checked": True,
                "assignment_conflict_checked": True,
                "concurrency_codes": codes,
            },
            "phase4": {
                "overtime_rows": len(overtime_json.get("staff", [])),
                "fairness_rows": len(fairness_json.get("staff", [])),
                "hours_distribution_checked": True,
                "on_duty_checked": True,
                "audit_logs_count": len(audit_json.get("logs", [])),
                "audit_csv_checked": True,
                "cert_revoke_audit_checked": True,
            },
        }


def main() -> int:
    env = os.environ.copy()
    env["PORT"] = str(PORT)

    stdout_log = ROOT / "smoke_api.out.log"
    stderr_log = ROOT / "smoke_api.err.log"
    stdout_handle = stdout_log.open("w", encoding="utf-8")
    stderr_handle = stderr_log.open("w", encoding="utf-8")

    process = subprocess.Popen(
        ["python", "run.py"],
        cwd=str(API_DIR),
        env=env,
        stdout=stdout_handle,
        stderr=stderr_handle,
    )
    try:
        wait_for_health()
        result = asyncio.run(run_smoke())
        print("SMOKE_OK")
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:
        print(f"SMOKE_FAILED: {exc}")
        traceback.print_exc()
        try:
            stdout_tail = "\n".join(stdout_log.read_text(encoding="utf-8").splitlines()[-60:])
            stderr_tail = "\n".join(stderr_log.read_text(encoding="utf-8").splitlines()[-60:])
            if stdout_tail:
                print("--- API stdout (tail) ---")
                print(stdout_tail)
            if stderr_tail:
                print("--- API stderr (tail) ---")
                print(stderr_tail)
        except Exception:
            pass
        return 1
    finally:
        process.terminate()
        try:
            process.wait(timeout=8)
        except Exception:
            process.kill()
        stdout_handle.close()
        stderr_handle.close()


if __name__ == "__main__":
    raise SystemExit(main())
