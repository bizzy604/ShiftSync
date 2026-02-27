# Analytics Module

Modular domain implementation for `analytics`.

## Purpose
- Own analytics read/report workflows:
  - overtime dashboard
  - fairness report
  - hours distribution
  - on-duty view
- Keep report calculations and query orchestration in service/repository layers.

## Public API
- `router`: FastAPI router mounted at `/api/v1/analytics`.
- `overtime_dashboard_record`: service workflow for projected overtime.
- `fairness_report_record`: service workflow for fairness report.
- `hours_distribution_record`: service workflow for hours distribution.
- `on_duty_record`: service workflow for on-duty snapshot.

## Files
- `__init__.py`: public API boundary.
- `router.py`: thin transport orchestration.
- `service.py`: domain workflows.
- `repository.py`: persistence operations.
- `schemas.py`: schema re-exports for discoverability.
- `exceptions.py`: typed domain errors.
- `dependencies.py`: dependency wiring.

## Notes
- Legacy `app/api/routes/*` compatibility shims have been removed. Import directly from this module package.
- Sorting and fairness behavior is protected by integration test `test_analytics_fairness_sort.py`.
