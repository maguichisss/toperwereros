"""Drift guard: the permission matrix documented in the API reference must
equal the runtime permission map in ``app.auth.ROLE_PERMISSIONS``.

The authoritative block lives in ``docs/api-reference.md`` between the
``<!-- ROLES:START -->`` and ``<!-- ROLES:END -->`` markers as JSON.
"""

import json
import re
from pathlib import Path

from app.auth import ROLE_PERMISSIONS

REPO_ROOT = Path(__file__).resolve().parents[2]
API_REFERENCE = REPO_ROOT / "docs" / "api-reference.md"


def _documented_roles() -> dict[str, list[str]]:
    text = API_REFERENCE.read_text(encoding="utf-8")
    match = re.search(
        r"<!-- ROLES:START -->\s*```json\s*(.*?)\s*```\s*<!-- ROLES:END -->",
        text,
        flags=re.S,
    )
    assert match, "Could not find the ROLES:START/END JSON block in api-reference.md"
    return json.loads(match.group(1))


def test_documented_roles_match_runtime_permissions() -> None:
    assert _documented_roles() == ROLE_PERMISSIONS


def test_role_names_match_runtime_roles() -> None:
    assert set(_documented_roles().keys()) == set(ROLE_PERMISSIONS.keys())


def test_employee_and_viewer_permission_counts() -> None:
    roles = _documented_roles()
    assert len(roles["employee"]) == 15
    assert len(roles["viewer"]) == 6


def test_admin_wildcard() -> None:
    assert _documented_roles()["admin"] == ["*"]