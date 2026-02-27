"""
MODULE: /apps/api/app/services/timezone_utils.py

FUNCTION:
    Implements reusable domain service logic for `timezone_utils` workflows.

DEPENDENCIES:
    - /apps/api/app/api/routes/analytics.py
    - /apps/api/app/api/routes/assignments.py
    - /apps/api/app/api/routes/shifts.py
    - /apps/api/app/api/routes/swaps.py

IMPORTANCE:
    This module keeps domain logic reusable and consistent across routes, workers, and
    future extensions.
"""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


def parse_shift_local_range(
    shift_date: date,
    start_time_hhmm: str,
    end_time_hhmm: str,
    timezone_name: str,
) -> tuple[datetime, datetime]:
    """Parse shift local range.
    
    Args:
        shift_date: Input parameter `shift_date` used by this operation.
        start_time_hhmm: Input parameter `start_time_hhmm` used by this operation.
        end_time_hhmm: Input parameter `end_time_hhmm` used by this operation.
        timezone_name: Input parameter `timezone_name` used by this operation.
    
    Returns:
        Result typed as `tuple[datetime, datetime]`.
    """
    tz = ZoneInfo(timezone_name)
    start_hour, start_minute = [int(part) for part in start_time_hhmm.split(":")]
    end_hour, end_minute = [int(part) for part in end_time_hhmm.split(":")]

    local_start = datetime.combine(shift_date, time(start_hour, start_minute), tzinfo=tz)
    local_end = datetime.combine(shift_date, time(end_hour, end_minute), tzinfo=tz)
    if local_end <= local_start:
        local_end += timedelta(days=1)

    return local_start.astimezone(timezone.utc), local_end.astimezone(timezone.utc)


def week_start_monday(value: date) -> date:
    """Week start monday.
    
    Args:
        value: Input parameter `value` used by this operation.
    
    Returns:
        Result typed as `date`.
    """
    return value - timedelta(days=value.weekday())


def format_local_iso(value_utc: datetime, timezone_name: str) -> str:
    """Format local iso.
    
    Args:
        value_utc: Input parameter `value_utc` used by this operation.
        timezone_name: Input parameter `timezone_name` used by this operation.
    
    Returns:
        Result typed as `str`.
    """
    local = value_utc.astimezone(ZoneInfo(timezone_name))
    return local.isoformat()
