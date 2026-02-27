"""
MODULE: /apps/api/app/modules/analytics/__init__.py

FUNCTION:
    Defines the public API boundary and exported contracts for the analytics domain.

DEPENDENCIES:
    - /apps/api/app/api/router.py
    - /apps/api/app/modules/analytics/router.py

IMPORTANCE:
    Exporting a stable surface here prevents external callers from depending on private
    module internals.
"""

from app.modules.analytics.router import (
    fairness_report,
    hours_distribution,
    on_duty,
    overtime_dashboard,
    router,
)
from app.modules.analytics.service import (
    fairness_report as fairness_report_record,
    hours_distribution as hours_distribution_record,
    on_duty as on_duty_record,
    overtime_dashboard as overtime_dashboard_record,
)

__all__ = [
    "router",
    "overtime_dashboard",
    "fairness_report",
    "hours_distribution",
    "on_duty",
    "overtime_dashboard_record",
    "fairness_report_record",
    "hours_distribution_record",
    "on_duty_record",
]
