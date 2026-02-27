import json
from types import SimpleNamespace

from app.services import email_simulator


def test_should_simulate_email_only_for_in_app_email() -> None:
    assert email_simulator.should_simulate_email("in_app_email") is True
    assert email_simulator.should_simulate_email("in_app") is False
    assert email_simulator.should_simulate_email(None) is False


def test_simulate_email_delivery_writes_jsonl(tmp_path) -> None:
    log_path = tmp_path / "emails.log"
    email_simulator.get_settings.cache_clear()
    original_get_settings = email_simulator.get_settings
    try:
        email_simulator.get_settings = lambda: SimpleNamespace(simulated_email_log_path=str(log_path))
        email_simulator.simulate_email_delivery(
            user_email="test@example.com",
            notif_type="swap.approved",
            message="Swap approved",
            payload={"requestId": "req-1"},
        )
    finally:
        email_simulator.get_settings = original_get_settings

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["to"] == "test@example.com"
    assert record["type"] == "swap.approved"
    assert record["message"] == "Swap approved"
    assert record["payload"] == {"requestId": "req-1"}
    assert record["timestamp_utc"].endswith("+00:00")
