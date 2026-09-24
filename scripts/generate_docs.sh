#!/usr/bin/env bash
# scripts/generate_docs.sh
# Build API documentation artifacts.
#
# Usage:
#   generate_docs.sh                 # both (default)
#   generate_docs.sh --markdown      # generate docs/api-reference.md only
#   generate_docs.sh --html          # render backend/docs.html only
#   generate_docs.sh --check         # verify no drift (exit 1 if drift)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${REPO_ROOT}/backend"

MODE="all"
CHECK=0

for arg in "$@"; do
  case "$arg" in
    --markdown)  MODE="markdown" ;;
    --html)      MODE="html" ;;
    --all)       MODE="all" ;;
    --check)     CHECK=1 ;;
    -h|--help)
      echo "Usage: generate_docs.sh [--markdown|--html|--all|--check]"
      echo "  --markdown   Generate docs/api-reference.md from code"
      echo "  --html       Render backend/docs.html from markdown"
      echo "  --all        Both (default)"
      echo "  --check      Verify no drift; exit 1 if artifacts differ"
      exit 0
      ;;
    *) echo "Unknown option: $arg" >&2; exit 1 ;;
  esac
done

cd "${REPO_ROOT}"

# Load JWT_SECRET from .env if available
if [[ -f "${BACKEND_DIR}/.env" ]]; then
  set -a
  source "${BACKEND_DIR}/.env"
  set +a
fi

# Ensure scripts/ is in Python path
export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH:-}"

run_with_check() {
  local desc="$1" cmd="$2" output_file="$3"
  if [[ $CHECK -eq 1 ]]; then
    local tmp=$(mktemp)
    eval "$cmd" > "$tmp"
    if ! diff -q "$tmp" "$output_file" >/dev/null 2>&1; then
      echo "DRIFT: $desc ($output_file)" >&2
      rm -f "$tmp"
      return 1
    fi
    rm -f "$tmp"
  else
    eval "$cmd"
  fi
}

if [[ "$MODE" == "markdown" || "$MODE" == "all" ]]; then
  echo "📝 Generating markdown: docs/api-reference.md"
  if [[ $CHECK -eq 1 ]]; then
    run_with_check "api-reference.md" \
      "python scripts/generate_api_reference.py --output -" \
      "${REPO_ROOT}/docs/api-reference.md"
  else
    python scripts/generate_api_reference.py
  fi
fi

if [[ "$MODE" == "html" || "$MODE" == "all" ]]; then
  echo "🎨 Rendering HTML: backend/docs.html"
  if [[ $CHECK -eq 1 ]]; then
    run_with_check "backend/docs.html" \
      "python scripts/generate_docs_html.py --output -" \
      "${BACKEND_DIR}/docs.html"
  else
    python scripts/generate_docs_html.py
  fi
fi

[[ $CHECK -eq 1 ]] && echo "✅ All artifacts in sync."