"""
MODULE: /apps/api/app/modules/__init__.py

FUNCTION:
    Defines the root package for domain modules in the modular-monolith architecture.

DEPENDENCIES:
    - /apps/api/app/api/router.py

IMPORTANCE:
    This package is the top-level namespace for domain boundaries and helps decouple
    transport layers from domain internals during migration.
"""

__all__: list[str] = []
