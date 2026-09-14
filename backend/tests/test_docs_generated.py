"""Drift guard: regenerating ``backend/docs.html`` from the Markdown source of
truth must produce a byte-identical file to the one committed in the repo.

After editing ``docs/api-reference.md``, regenerate and commit the output::

    python scripts/gen_api_docs.py      # from backend/
    pytest tests/test_docs_generated.py -q
"""

import importlib.util
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = BACKEND_DIR / "scripts"
REPO_ROOT = BACKEND_DIR.parent
API_REFERENCE = REPO_ROOT / "docs" / "api-reference.md"
COMMITTED_HTML = BACKEND_DIR / "docs.html"


def _load_generator():
    """Import ``scripts/gen_api_docs.py`` by file path (it is not a package)."""
    spec = importlib.util.spec_from_file_location(
        "gen_api_docs", SCRIPTS_DIR / "gen_api_docs.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_regenerated_docs_html_matches_committed() -> None:
    generator = _load_generator()
    md_text = API_REFERENCE.read_text(encoding="utf-8")
    regenerated = generator.render_html(md_text).encode("utf-8")
    committed = COMMITTED_HTML.read_bytes()
    assert committed == regenerated, (
        "backend/docs.html is out of sync with docs/api-reference.md. "
        "Run `python scripts/gen_api_docs.py` (from backend/) and commit the "
        "regenerated file."
    )


def test_api_reference_exists_and_is_nonempty() -> None:
    assert API_REFERENCE.exists()
    assert len(API_REFERENCE.read_text(encoding="utf-8").strip()) > 0