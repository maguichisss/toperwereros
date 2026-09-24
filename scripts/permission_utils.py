#!/usr/bin/env python3
"""
Shared permission extraction utilities.

Single source for extracting permissions from FastAPI route dependencies.
Used by both the docs generator and the route coverage test.
"""

from __future__ import annotations

import re
from typing import Any, Set, Tuple, Dict, List

# ──────────────────────────────────────────────────────────────────────
# Public route allowlist — explicitly public (no auth, no permission)
# ──────────────────────────────────────────────────────────────────────
PUBLIC_ROUTES: set[Tuple[str, str]] = {
    ("GET", "/docs"),
    ("GET", "/redoc"),
    ("GET", "/openapi.json"),
    ("GET", "/api/health"),
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/refresh"),
}

# ──────────────────────────────────────────────────────────────────────
# Authenticated-only allowlist — routes that intentionally have auth
# but no specific permission (documented exceptions)
# ──────────────────────────────────────────────────────────────────────
AUTH_ONLY_ALLOWLIST: set[Tuple[str, str]] = {
    ("GET", "/api/auth/me"),
    ("PATCH", "/api/auth/profile"),
    ("POST", "/api/auth/change-password"),
    ("POST", "/api/auth/avatar"),
    ("POST", "/api/auth/logout"),
}

# ──────────────────────────────────────────────────────────────────────
# Permission extraction
# ──────────────────────────────────────────────────────────────────────
# Permission extraction
# ──────────────────────────────────────────────────────────────────────

def _extract_permissions_from_dependant(dependant: Any) -> Set[str]:
    """Recursively extract permissions from a FastAPI Dependant tree."""
    perms: set[str] = set()
    if not hasattr(dependant, "dependencies"):
        return perms
    
    for dep in dependant.dependencies:
        callable_obj = getattr(dep, "call", None)
        if callable_obj is None:
            continue

        # Check if it's a require_permission factory (name contains "require_permission" or is the inner "dependency" function)
        if hasattr(callable_obj, "__name__"):
            name = callable_obj.__name__
            if "require_permission" in name or name == "dependency":
                # Extract permissions from closure
                if hasattr(callable_obj, "__closure__") and callable_obj.__closure__:
                    for cell in callable_obj.__closure__:
                        val = cell.cell_contents
                        if isinstance(val, tuple):
                            for item in val:
                                if isinstance(item, str):
                                    perms.add(item)
                        elif isinstance(val, str):
                            perms.add(val)
        
        # Recurse into nested dependants
        if hasattr(dep, "dependencies") and dep.dependencies:
            perms.update(_extract_permissions_from_dependant(dep))
    
    return perms


def extract_permissions_from_route(route: Any) -> Set[str]:
    """
    Extract ALL permission strings from a route's dependencies.

    Handles:
      - require_permission("perm")           -> {"perm"}
      - require_permission("a", "b", "c")    -> {"a", "b", "c"}  (OR logic)
      - require_permission("a") | require_permission("b")  (multiple deps) -> {"a", "b"}

    Returns empty set if no require_permission dependency found.
    """
    if not hasattr(route, "dependant") or route.dependant is None:
        return set()
    return _extract_permissions_from_dependant(route.dependant)


def has_auth_dependency(route: Any) -> bool:
    """Check if route has any authentication dependency (get_current_user or require_permission)."""
    if not hasattr(route, "dependant") or route.dependant is None:
        return False
    
    def _check(dependant: Any) -> bool:
        if not hasattr(dependant, "dependencies"):
            return False
        for dep in dependant.dependencies:
            callable_obj = getattr(dep, "call", None)
            if callable_obj and hasattr(callable_obj, "__name__"):
                name = callable_obj.__name__
                if name in ("get_current_user",) or "require_permission" in name or name == "dependency":
                    return True
            if hasattr(dep, "dependencies") and dep.dependencies:
                if _check(dep):
                    return True
        return False
    
    return _check(route.dependant)


def get_route_permission_classification(route: Any) -> str:
    """
    Classify a route's permission state.

    Returns:
        "public"           - No auth, no permission (in PUBLIC_ROUTES)
        "permission:X"     - Has require_permission("X") or require_permission("a","b")
        "authenticated"    - Has auth dependency but no explicit permission
        "unknown"          - Has dependencies but unrecognized
    """
    key = (route.method, route.path) if hasattr(route, "method") else None

    if key in PUBLIC_ROUTES:
        return "public"

    perms = extract_permissions_from_route(route)
    if perms:
        return f"permission:{sorted(perms)[0]}"

    if has_auth_dependency(route):
        return "authenticated"

    return "unknown"


# ──────────────────────────────────────────────────────────────────────
# ROLE_PERMISSIONS analysis
# ──────────────────────────────────────────────────────────────────────

def get_all_concrete_permissions(role_permissions: dict[str, list[str]]) -> set[str]:
    """Get all non-wildcard permissions defined in the system."""
    return {p for perms in role_permissions.values() for p in perms if p != "*"}


def get_all_effective_permissions(role_permissions: dict[str, list[str]]) -> dict[str, set[str]]:
    """
    Expand wildcards to get effective permissions per role.

    Returns: {role: {effective_permissions}}
    """
    concrete = get_all_concrete_permissions(role_permissions)
    effective = {}
    for role, perms in role_permissions.items():
        if "*" in perms:
            effective[role] = set(concrete)  # Wildcard = all concrete perms
        else:
            effective[role] = {p for p in perms if p != "*"}
    return effective


def get_admin_only_permissions(role_permissions: dict[str, list[str]]) -> set[str]:
    """Permissions that ONLY admin has (via wildcard), not explicitly granted to other roles."""
    effective = get_all_effective_permissions(role_permissions)
    admin_perms = effective.get("admin", set())
    other_perms = set()
    for role, perms in effective.items():
        if role != "admin":
            other_perms.update(perms)
    return admin_perms - other_perms


# ──────────────────────────────────────────────────────────────────────
# Coverage analysis
# ──────────────────────────────────────────────────────────────────────

def analyze_route_permission_coverage(
    app_routes: list[Any],
    role_permissions: dict[str, list[str]],
) -> dict:
    """
    Comprehensive coverage analysis of route permissions.

    The admin `*` wildcard implicitly defines every permission the system
    uses, so the canonical "inventory" is ``declared_permissions ∪ explicit
    concrete permissions``.

    Returns:
        {
            "routes_total": int,
            "routes_public": int,
            "routes_with_permission": int,
            "routes_authenticated_only": int,
            "routes_authenticated_only_allowlisted": int,
            "routes_authenticated_only_violations": list[dict],
            "declared_permissions": set[str],
            "all_defined_permissions": set[str],   # inventory (declared ∪ concrete)
            "undefined_permissions": set[str],
            "unused_permissions": set[str],
            "admin_only_permissions": set[str],
            "coverage_tiers": {
                "explicitly_assigned": int,
                "admin_only_wildcard": int,
                "truly_unused": int,
            }
        }
    """
    results = {
        "routes_total": 0,
        "routes_public": 0,
        "routes_with_permission": 0,
        "routes_authenticated_only": 0,
        "routes_authenticated_only_allowlisted": 0,
        "routes_authenticated_only_violations": [],
        "declared_permissions": set(),
        "all_defined_permissions": set(),
        "undefined_permissions": set(),
        "unused_permissions": set(),
        "admin_only_permissions": set(),
        "coverage_tiers": {
            "explicitly_assigned": 0,
            "admin_only_wildcard": 0,
            "truly_unused": 0,
        }
    }

    for route in app_routes:
        if not hasattr(route, "methods") or not hasattr(route, "path"):
            continue
        if route.path in ("/docs", "/redoc", "/openapi.json", "/api/health"):
            continue
        for method in route.methods:
            if method in ("HEAD", "OPTIONS"):
                continue

            results["routes_total"] += 1
            key = (method, route.path)

            if key in PUBLIC_ROUTES:
                results["routes_public"] += 1
                continue

            perms = extract_permissions_from_route(route)

            if perms:
                results["routes_with_permission"] += 1
                results["declared_permissions"].update(perms)
                continue

            # No explicit permission
            if has_auth_dependency(route):
                results["routes_authenticated_only"] += 1
                if key in AUTH_ONLY_ALLOWLIST:
                    results["routes_authenticated_only_allowlisted"] += 1
                else:
                    results["routes_authenticated_only_violations"].append({
                        "method": method,
                        "path": route.path,
                    })

    # Post-processing: a permission is "real" if it is explicitly named in
    # ROLE_PERMISSIONS or declared on a route (admin `*` wildcard legitimizes
    # any declared permission).
    declared = results["declared_permissions"]
    concrete = get_all_concrete_permissions(role_permissions)
    inventory = declared | concrete

    # Permissions explicitly granted to a non-admin role.
    non_admin_explicit = set()
    for role, perms in role_permissions.items():
        if role == "admin":
            continue
        non_admin_explicit.update(p for p in perms if p != "*")

    admin_only = inventory - non_admin_explicit
    truly_unused = inventory - declared

    results["all_defined_permissions"] = inventory
    results["undefined_permissions"] = declared - inventory
    results["unused_permissions"] = truly_unused
    results["admin_only_permissions"] = admin_only
    results["coverage_tiers"] = {
        "explicitly_assigned": len(inventory - admin_only),
        "admin_only_wildcard": len(admin_only),
        "truly_unused": len(truly_unused),
    }

    return results


def format_coverage_report(analysis: dict) -> str:
    """Generate human-readable coverage report."""
    lines = [
        "Permission Coverage Report",
        "=" * 50,
        f"Total routes analyzed:    {analysis['routes_total']}",
        f"  Public:                 {analysis['routes_public']}",
        f"  With permission:        {analysis['routes_with_permission']}",
        f"  Authenticated only:     {analysis['routes_authenticated_only']}",
        f"  (allowlisted):          {analysis['routes_authenticated_only_allowlisted']}",
        f"  (violations):           {len(analysis['routes_authenticated_only_violations'])}",
        "",
        "Permissions:",
        f"  In inventory (declared ∪ explicit): {len(analysis['all_defined_permissions'])}",
        f"  Declared on routes:                 {len(analysis['declared_permissions'])}",
        f"  Undefined (not in inventory):       {len(analysis['undefined_permissions'])}",
        f"  Truly unused:                       {len(analysis['unused_permissions'])}",
        f"  Admin-only (wildcard):              {len(analysis['admin_only_permissions'])}",
        "",
        "Coverage Tiers:",
        f"  ✅ Explicitly assigned:   {analysis['coverage_tiers']['explicitly_assigned']:3d}   (explicitly given to employee/viewer)",
        f"  🔑 Admin-only (wildcard): {analysis['coverage_tiers']['admin_only_wildcard']:3d}   (only admin reaches them)",
        f"  ❌ Truly unused:          {analysis['coverage_tiers']['truly_unused']:3d}   (not declared anywhere)",
        "",
        f"Total: {len(analysis['all_defined_permissions'])} = {analysis['coverage_tiers']['explicitly_assigned']} + {analysis['coverage_tiers']['admin_only_wildcard']} + {analysis['coverage_tiers']['truly_unused']}",
    ]

    if analysis['undefined_permissions']:
        lines.append("\n❌ UNDEFINED PERMISSIONS (typos?):")
        for p in sorted(analysis['undefined_permissions']):
            lines.append(f"  - {p}")

    if analysis['routes_authenticated_only_violations']:
        lines.append("\n❌ AUTHENTICATED-ONLY VIOLATIONS:")
        for v in analysis['routes_authenticated_only_violations']:
            lines.append(f"  - {v['method']} {v['path']}")

    return "\n".join(lines)