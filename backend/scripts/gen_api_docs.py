"""Render docs/api-reference.md into backend/docs.html.

The repo Markdown API reference is the single source of truth for the public
API contract. This script converts it to the styled HTML page served at
``/docs`` (same visual design as the previous hand-maintained page).

Usage (from anywhere in the repo)::

    python backend/scripts/gen_api_docs.py

Use ``--output`` to write to a different path (used by tests to keep the
generator deterministic).

Guarded by ``backend/tests/test_docs_generated.py``, which fails if the
committed ``backend/docs.html`` ever drifts from the regenerated output.
"""

from __future__ import annotations

import argparse
import json
import os
import re

import markdown

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_MD_PATH = os.path.join(REPO_ROOT, "docs", "api-reference.md")
DEFAULT_OUT_PATH = os.path.join(REPO_ROOT, "backend", "docs.html")

_CSS = """\
    :root {
      --bg: #0f172a; --surface: #1e293b; --border: #334155;
      --text: #e2e8f0; --muted: #94a3b8; --accent: #38bdf8;
      --green: #4ade80; --yellow: #fbbf24; --red: #f87171;
      --purple: #a78bfa; --orange: #fb923c;
    }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }
    .container { max-width: 1100px; margin: 0 auto; padding: 2rem 1.5rem; }
    h1 { font-size: 2rem; margin-bottom: 0.5rem; }
    h1 span { color: var(--accent); }
    h2 { font-size: 1.3rem; color: var(--accent); margin: 2.5rem 0 1rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; }
    h3 { font-size: 1.05rem; margin: 1.5rem 0 0.5rem; color: var(--green); }
    p, li { color: var(--muted); font-size: 0.92rem; }
    a { color: var(--accent); text-decoration: none; }
    a:hover { text-decoration: underline; }
    .subtitle { color: var(--muted); margin-bottom: 2rem; font-size: 0.95rem; }
    .links { display: flex; gap: 1rem; margin-bottom: 2rem; flex-wrap: wrap; }
    .links a { background: var(--surface); border: 1px solid var(--border); padding: 0.5rem 1rem; border-radius: 6px; font-size: 0.85rem; }
    .links a:hover { border-color: var(--accent); text-decoration: none; }
    table { width: 100%; border-collapse: collapse; margin: 0.75rem 0 1.5rem; font-size: 0.85rem; }
    th, td { text-align: left; padding: 0.5rem 0.75rem; border-bottom: 1px solid var(--border); }
    th { color: var(--accent); font-weight: 600; background: var(--surface); }
    td { color: var(--text); }
    .perm { font-family: 'Courier New', monospace; font-size: 0.78rem; color: var(--orange); }
    code { font-family: 'Courier New', monospace; background: var(--surface); padding: 0.1rem 0.3rem; border-radius: 3px; font-size: 0.82rem; color: var(--accent); }
    pre { background: var(--surface); border: 1px solid var(--border); border-radius: 6px; padding: 0.75rem 1rem; margin: 0.75rem 0 1.5rem; overflow-x: auto; }
    pre code { background: transparent; padding: 0; color: var(--muted); }
    ul { padding-left: 1.5rem; margin: 0.5rem 0; }
    li { margin: 0.25rem 0; }
    blockquote { border-left: 3px solid var(--border); margin: 1rem 0; padding: 0.25rem 1rem; color: var(--muted); font-size: 0.9rem; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 1rem 0; }
    .stat { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; text-align: center; }
    .stat .num { font-size: 1.8rem; font-weight: 700; color: var(--accent); }
    .stat .label { font-size: 0.8rem; color: var(--muted); }
    footer { margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--border); text-align: center; font-size: 0.8rem; color: var(--muted); }
"""

_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Store Catalog API — Documentation</title>
<style>
{css}
</style>
</head>
<body>
<div class="container">

<h1><span>Store Catalog</span> API Documentation</h1>
<p class="subtitle">FastAPI backend &mdash; authentication, product catalog, sales, layaways, and PDF generation.</p>

<div class="links">
  <a href="/swagger">Swagger UI</a>
  <a href="/redoc">ReDoc</a>
  <a href="/openapi.json">OpenAPI JSON</a>
</div>

{stat_cards}
{body}
<footer>Store Catalog API &mdash; FastAPI + SQLAlchemy 2.0 + PostgreSQL</footer>
</div>
</body>
</html>
"""

_META_LABELS = {
    "endpoints": "Endpoints",
    "modules": "Modules",
    "roles": "Roles",
    "permissions": "Permissions",
}


def extract_meta(md_text: str) -> dict | None:
    """Return the ``API-META`` stats object, or ``None`` if absent."""
    match = re.search(r"<!-- API-META:\s*(\{.*?\})\s*-->", md_text, flags=re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def _render_stat_cards(meta: dict | None) -> str:
    if not meta:
        return ""
    cards = []
    for key in ("endpoints", "modules", "roles", "permissions"):
        if key in meta:
            cards.append(
                '<div class="stat"><div class="num">{}</div>'
                '<div class="label">{}</div></div>'.format(
                    meta[key], _META_LABELS[key]
                )
            )
    if not cards:
        return ""
    return '<div class="grid">\n{}\n</div>'.format("\n".join(cards))


def render_html(md_text: str) -> str:
    """Convert the reference Markdown to the full styled HTML document."""
    meta = extract_meta(md_text)
    body = markdown.markdown(
        re.sub(r"<!-- API-META:.*?-->", "", md_text, flags=re.S),
        extensions=["tables", "fenced_code", "sane_lists"],
    )
    return _PAGE_TEMPLATE.format(
        css=_CSS,
        stat_cards=_render_stat_cards(meta),
        body=body,
    )


def generate(md_path: str = DEFAULT_MD_PATH, out_path: str = DEFAULT_OUT_PATH) -> str:
    """Read *md_path*, render to HTML, and write *out_path*."""
    with open(md_path, "r", encoding="utf-8") as fh:
        html = render_html(fh.read())
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render the Markdown API reference into backend/docs.html."
    )
    parser.add_argument(
        "--output", default=DEFAULT_OUT_PATH, help="Output HTML path (default: backend/docs.html)"
    )
    args = parser.parse_args()
    print(generate(out_path=args.output))


if __name__ == "__main__":
    main()