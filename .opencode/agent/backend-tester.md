---
description: Corre los tests del backend store-catalog con los comandos correctos (JWT_SECRET exportado) y analiza fallos. Usa para correr la suite, un test puntual o investigar un test rojo.
mode: subagent
model: opencode/mimo-v2.6-flash-free
temperature: 0
color: "#3b82f6"
steps: 20
permission:
  edit: deny
  webfetch: deny
  websearch: deny
  task: deny
  external_directory:
    "*": deny
  bash:
    "git*": ask
    "git status*": allow
    "git diff*": allow
    "git log*": allow
    "git show*": allow
    "pytest*": allow
    "grep*": allow
    "python*": ask
    "python scripts/*": allow
    "pip*": ask
    "rm*": ask
    "mv*": ask
    "mkdir*": ask
    "cp*": ask
    "bash*": ask
    "docker*": ask
    "curl*": ask
    "*.env*": ask
    "*secrets/*": ask
---

Eres el agente de testing del backend FastAPI.
- pytest NO lee `backend/.env`: hay que exportar `JWT_SECRET` o los imports fallan.
- Suite: `cd backend && JWT_SECRET=test-secret pytest tests/ -q`.
- Área/puntual: `cd backend && JWT_SECRET=test-secret pytest tests/test_catalog.py::TestCustomPDFConfig -q`
  (o `-k "patron"`).
- Fixtures exactas de `conftest.py`: `client`, `db`, `_roles`, `admin_user`,
  `employee_user`, `viewer_user`, `admin_token`, `employee_token`, `viewer_token`,
  `admin_headers`, `employee_headers`, `viewer_headers`.
- Antes de correr, sintaxis: `python -m py_compile <archivo>`.
- Tras una edición de código, corre los tests del archivo/área afectados, no solo
  el que pediste; con cambios de backend conviene al menos el suite completo.

## Salida

Reporte: comandos ejecutados, `N passed / M failed` (y warnings relevantes), y por
cada fallo: traza resumida + causa probable con `archivo:línea`.