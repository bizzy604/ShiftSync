"""
MODULE: /scripts/check_module_boundaries.py

FUNCTION:
    Validates modular-monolith import boundaries so cross-domain imports only use each domain's
    public package boundary.

DEPENDENCIES:
    - /apps/api/pyproject.toml

IMPORTANCE:
    This check prevents accidental coupling between domain internals during migration and keeps
    the modular-monolith boundaries enforceable over time.
"""

from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
MODULES_ROOT = REPO_ROOT / "apps" / "api" / "app" / "modules"


def _iter_module_files() -> list[Path]:
    return sorted(
        p
        for p in MODULES_ROOT.rglob("*.py")
        if "__pycache__" not in p.parts
    )


def _domain_from_path(path: Path) -> str | None:
    try:
        rel = path.relative_to(MODULES_ROOT)
    except ValueError:
        return None
    if len(rel.parts) < 2:
        return None
    return rel.parts[0]


def _is_internal_submodule_import(target_module: str) -> bool:
    """Return True when import targets another domain's internal module path."""
    # Allowed public import shape:
    # - app.modules.<domain>
    # - app.modules.<domain>.__init__
    parts = target_module.split(".")
    if len(parts) < 3:
        return False
    if parts[0] != "app" or parts[1] != "modules":
        return False
    if len(parts) == 3:
        return False
    if len(parts) == 4 and parts[3] == "__init__":
        return False
    return True


def _collect_violations() -> list[str]:
    violations: list[str] = []
    for file_path in _iter_module_files():
        importer_domain = _domain_from_path(file_path)
        if importer_domain is None:
            continue

        source = file_path.read_text(encoding="utf-8-sig")
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            violations.append(
                f"{file_path.as_posix()}: syntax error while parsing ({exc.msg})"
            )
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target = alias.name
                    if not target.startswith("app.modules."):
                        continue
                    parts = target.split(".")
                    if len(parts) < 3:
                        continue
                    target_domain = parts[2]
                    if target_domain == importer_domain:
                        continue
                    if _is_internal_submodule_import(target):
                        violations.append(
                            f"{file_path.as_posix()}:{node.lineno} imports internal cross-domain module '{target}'. "
                            "Import through app.modules.<domain> instead."
                        )

            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.level:
                    # Relative imports within domain internals are allowed.
                    continue
                if not module.startswith("app.modules."):
                    continue
                parts = module.split(".")
                if len(parts) < 3:
                    continue
                target_domain = parts[2]
                if target_domain == importer_domain:
                    continue

                if _is_internal_submodule_import(module):
                    violations.append(
                        f"{file_path.as_posix()}:{node.lineno} imports from internal cross-domain module '{module}'. "
                        "Import through app.modules.<domain> instead."
                    )

                for alias in node.names:
                    if alias.name == "*":
                        continue
                    candidate = f"{module}.{alias.name}"
                    if _is_internal_submodule_import(candidate):
                        violations.append(
                            f"{file_path.as_posix()}:{node.lineno} imports internal symbol '{candidate}' across domains. "
                            "Import from app.modules.<domain> public boundary."
                        )

    return violations


def main() -> int:
    violations = _collect_violations()
    if violations:
        print("Module boundary violations detected:")
        for item in violations:
            print(f"- {item}")
        return 1

    print("Module boundary check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
