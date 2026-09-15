#!/usr/bin/env python3
"""Check that every relative Markdown link under the repo resolves to a real
file. Skips bare http(s), mailto, root-relative, and anchor-only links.

Run before committing documentation changes:

    python3 scripts/check-doc-links.py
"""

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCAN = (
    [REPO / "README.md", REPO / "scripts" / "README.md"]
    + sorted((REPO / "docs").rglob("*.md"))
)
LINK_RE = re.compile(r"\]\(([^)#]+?)(?:#[^)]*)?\)")


def main() -> int:
    broken: list[tuple[str, str]] = []
    for f in SCAN:
        if not f.exists():
            broken.append((str(f.relative_to(REPO)), "(file missing)"))
            continue
        text = f.read_text(encoding="utf-8")
        for m in LINK_RE.finditer(text):
            target = m.group(1)
            if target.startswith(("http://", "https://", "mailto:", "/")):
                continue
            if not (f.parent / target).exists():
                broken.append((str(f.relative_to(REPO)), target))

    if broken:
        print(f"{len(broken)} broken link(s):")
        for src, tgt in broken:
            print(f"  {src} -> {tgt}")
        return 1
    print(f"OK: all links resolve across {len(SCAN)} file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())