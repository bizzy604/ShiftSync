"""
MODULE: /apps/api/app/modules/audit/__init__.py

FUNCTION:
    Defines the public API boundary and exported contracts for the audit domain.

DEPENDENCIES:
    - /apps/api/app/api/router.py
    - /apps/api/app/modules/audit/router.py

IMPORTANCE:
    Exporting a stable surface here prevents external callers from depending on private
    module internals.
"""

from app.modules.audit.router import export_audit_logs, list_audit_logs, router
from app.modules.audit.service import (
    export_audit_logs as export_audit_logs_record,
    list_audit_logs as list_audit_logs_record,
)

__all__ = [
    "router",
    "list_audit_logs",
    "export_audit_logs",
    "list_audit_logs_record",
    "export_audit_logs_record",
]
