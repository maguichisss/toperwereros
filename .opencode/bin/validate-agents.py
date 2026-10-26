#!/usr/bin/env python3
"""Validate opencode agent frontmatter.

Checks that every .md under .opencode/agent/ has parseable YAML frontmatter,
declares a description and a mode, and that every permission leaf is one of
allow, ask or deny.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ACTIONS = {"allow", "ask", "deny"}
MODES = {"primary", "subagent", "all"}
AGENT_DIR = Path(__file__).resolve().parent.parent / "agent"


def frontmatter(path: Path) -> dict:
    text = path.read_text()
    if not text.startswith("---\n"):
        raise ValueError("missing opening frontmatter delimiter")
    try:
        _, raw, _ = text.split("---\n", 2)
    except ValueError as exc:
        raise ValueError("unterminated frontmatter") from exc
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise ValueError("frontmatter is not a mapping")
    return data


def check_permissions(node, path: str, errors: list[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            check_permissions(value, f"{path}.{key}" if path else str(key), errors)
    elif isinstance(node, str):
        if node not in ACTIONS:
            errors.append(f"{path}: invalid action {node!r} (expected allow/ask/deny)")
    else:
        errors.append(f"{path}: expected action or mapping, got {type(node).__name__}")


def check_agent(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        meta = frontmatter(path)
    except (ValueError, yaml.YAMLError) as exc:
        return [f"{path.name}: {exc}"]

    if not meta.get("description"):
        errors.append(f"{path.name}: missing description")
    if meta.get("mode") not in MODES:
        errors.append(f"{path.name}: invalid mode {meta.get('mode')!r}")

    steps = meta.get("steps")
    if steps is not None and (not isinstance(steps, int) or isinstance(steps, bool) or steps < 1):
        errors.append(f"{path.name}: steps must be a positive integer")

    temperature = meta.get("temperature")
    if temperature is not None and (
        not isinstance(temperature, (int, float)) or isinstance(temperature, bool)
    ):
        errors.append(f"{path.name}: temperature must be a number")

    if "permission" in meta:
        check_permissions(meta["permission"], f"{path.name}.permission", errors)

    return errors


def main() -> int:
    files = sorted(AGENT_DIR.glob("*.md"))
    if not files:
        print(f"no agent files found in {AGENT_DIR}", file=sys.stderr)
        return 1

    errors: list[str] = []
    for path in files:
        errors.extend(check_agent(path))

    if errors:
        for error in errors:
            print(f"FAIL {error}", file=sys.stderr)
        return 1

    print(f"OK {len(files)} agent files validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
