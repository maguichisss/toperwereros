---
description: Corre la verificación de cierre del repo (agentes, pytest, build, docs y links).
agent: build
---

Ejecuta estos pasos desde la raíz, deteniéndote al primer fallo y reportando el resultado de cada uno:

1. `python .opencode/bin/validate-agents.py`
2. `cd backend && JWT_SECRET=test-secret pytest tests/ -q`
3. `cd frontend && npm run build`
4. `bash scripts/generate_docs.sh --check`
5. `python scripts/check-doc-links.py`

Al final resume: OK/FAIL por paso y, si algo falló, el comando exacto y el error.
