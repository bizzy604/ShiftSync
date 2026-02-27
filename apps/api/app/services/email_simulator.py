"""
MODULE: /apps/api/app/services/email_simulator.py

FUNCTION:
    Implements reusable domain service logic for `email_simulator` workflows.

DEPENDENCIES:
    - /apps/api/app/services/notifications.py
    - /apps/api/tests/unit/test_email_simulator.py

IMPORTANCE:
    This module keeps domain logic reusable and consistent across routes, workers, and
    future extensions.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import get_settings


def should_simulate_email(notification_pref: str | None) -> bool:
    """Should simulate email.
    
    Args:
        notification_pref: Input parameter `notification_pref` used by this operation.
    
    Returns:
        True when the operation succeeds, otherwise False.
    """
    return notification_pref == "in_app_email"


def simulate_email_delivery(
    *,
    user_email: str,
    notif_type: str,
    message: str,
    payload: dict[str, Any],
) -> None:
    """Simulate email delivery.
    
    Args:
        user_email: Input parameter `user_email` used by this operation.
        notif_type: Input parameter `notif_type` used by this operation.
        message: Input parameter `message` used by this operation.
        payload: Validated request payload model.
    
    Returns:
        None.
    """
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
