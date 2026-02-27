from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import get_settings


def should_simulate_email(notification_pref: str | None) -> bool:
    return notification_pref == "in_app_email"


def simulate_email_delivery(
    *,
    user_email: str,
    notif_type: str,
    message: str,
    payload: dict[str, Any],
) -> None:
    settings = get_settings()
    path = Path(settings.simulated_email_log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp_utc": datetime.now(tz=timezone.utc).isoformat(),
        "to": user_email,
        "type": notif_type,
        "message": message,
        "payload": payload,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=True) + "\n")
