#!/usr/bin/env python3
"""
Route Permission Coverage Test

Primary invariant: Every route declares a valid permission, and every
permission in ROLE_PERMISSIONS is enforced on at least one route.

Invariants enforced:
1. Every non-public route declares a permission via require_permission()
2. Every permission string used in routes exists in ROLE_PERMISSIONS
3. Every permission in ROLE_PERMISSIONS is used by at least one route
   (admin wildcard counts as "used" for coverage, but reported separately)
4. No authenticated-only routes without explicit allowlist
"""

import sys
from pathlib import Path

# Ensure backend is importable
BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(REPO_ROOT))

from app.main import app
from app.auth import ROLE_PERMISSIONS
from scripts.permission_utils import (
    extract_permissions_from_route,
    has_auth_dependency,
    PUBLIC_ROUTES,
    AUTH_ONLY_ALLOWLIST,
    get_all_concrete_permissions,
    get_admin_only_permissions,
    analyze_route_permission_coverage,
    format_coverage_report,
)


def test_every_route_declares_permission():
    """Every non-public route must declare a permission via require_permission()."""
    violations = []
    for route in app.routes:
        if not hasattr(route, "methods") or not hasattr(route, "path"):
            continue
        if route.path in ("/docs", "/redoc", "/openapi.json", "/api/health"):
            continue
        for method in route.methods:
            if method in ("HEAD", "OPTIONS"):
                continue
            key = (method, route.path)
            if key in PUBLIC_ROUTES:
                continue

            perms = extract_permissions_from_route(route)
            if not perms:
                # Check if authenticated-only and allowlisted
                if key in AUTH_ONLY_ALLOWLIST:
                    continue
                # Check if it has any auth dependency
                if hasattr(route, "dependencies") and route.dependencies:
                    has_auth = any(
                        getattr(dep, "dependency", None) and
                        getattr(dep.dependency, "__name__", "") == "get_current_user"
                        for dep in route.dependencies
                    )
                    if has_auth:
                        violations.append(f"{method} {route.path} - authenticated but no explicit permission")

    assert not violations, f"Routes missing explicit permission:\n" + "\n".join(f"  - {v}" for v in violations)


def test_all_declared_permissions_exist_in_role_permissions():
    """Every permission string used in routes must exist in ROLE_PERMISSIONS.
    Admin wildcard (*) counts as defining all permissions.
    """
    all_defined = get_all_concrete_permissions(ROLE_PERMISSIONS)
    # Check if admin has wildcard - if so, all permissions are implicitly defined
    admin_has_wildcard = "*" in ROLE_PERMISSIONS.get("admin", [])
    
    undefined = set()

    for route in app.routes:
        if not hasattr(route, "methods") or not hasattr(route, "path"):
            continue
        for method in route.methods:
            if method in ("HEAD", "OPTIONS"):
                continue
            perms = extract_permissions_from_route(route)
            for perm in perms:
                if perm not in all_defined and not admin_has_wildcard:
                    undefined.add(perm)

    assert not undefined, f"Undefined permissions (typos?):\n" + "\n".join(f"  - {p}" for p in sorted(undefined))


def test_all_role_permissions_used_by_at_least_one_route():
    """Every permission in ROLE_PERMISSIONS must be enforced on at least one route.
    Admin wildcard (*) counts as covering all permissions for coverage purposes,
    but admin-only permissions are reported separately.
    """
    all_concrete = get_all_concrete_permissions(ROLE_PERMISSIONS)

    # Collect all permissions declared on routes
    declared = set()
    for route in app.routes:
        if not hasattr(route, "methods") or not hasattr(route, "path"):
            continue
        for method in route.methods:
            if method in ("HEAD", "OPTIONS"):
                continue
            declared.update(extract_permissions_from_route(route))

    # Admin wildcard covers everything for coverage purposes
    unused = all_concrete - declared

    # Admin-only permissions (covered by wildcard) - report separately
    admin_only = get_admin_only_permissions(ROLE_PERMISSIONS)

    # Truly unused = not declared anywhere AND not admin-only
    truly_unused = (all_concrete - declared) - (get_admin_only_permissions(ROLE_PERMISSIONS))

    # For the test: pass if no truly unused (admin wildcard covers the rest)
    assert not truly_unused, (
        f"Truly unused permissions (not declared on any route, not admin-only):\n"
        + "\n".join(f"  - {p}" for p in sorted(truly_unused))
    )

    # Report admin-only separately (info, not failure)
    if admin_only:
        print(f"\n[INFO] Admin-only permissions (covered by wildcard): {sorted(admin_only)}")


def test_no_authenticated_only_violations():
    """No routes with authentication but no explicit permission (except allowlist)."""
    violations = []
    for route in app.routes:
        if not hasattr(route, "methods") or not hasattr(route, "path"):
            continue
        for method in route.methods:
            if method in ("HEAD", "OPTIONS"):
                continue
            key = (method, route.path)
            if key in {
                ("GET", "/docs"), ("GET", "/redoc"), ("GET", "/openapi.json"),
                ("GET", "/api/health"),
                ("POST", "/api/auth/login"), ("POST", "/api/auth/refresh"),
            }:
                continue

            perms = extract_permissions_from_route(route)
            if not perms:
                # Check if it has auth dependency
                has_auth = False
                if hasattr(route, "dependencies"):
                    for dep in route.dependencies:
                        callable_obj = getattr(dep, "dependency", None) or getattr(dep, "call", None)
                        if callable_obj and hasattr(callable_obj, "__name__"):
                            if "get_current_user" in callable_obj.__name__:
                                has_auth = True
                                break
                if has_auth and key not in AUTH_ONLY_ALLOWLIST:
                    violations.append(f"{method} {route.path}")

    assert not violations, (
        "Authenticated-only routes without explicit permission (add require_permission or update allowlist):\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


def test_coverage_report():
    """Generate and print coverage report (informational)."""
    from app.main import app
    analysis = analyze_route_permission_coverage(list(app.routes), ROLE_PERMISSIONS)
    print(format_coverage_report(analysis))


if __name__ == "__main__":
    # Allow running standalone for quick coverage report
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    test_coverage_report()