---
description: "Ayuda con la base de datos de store-catalog: esquema, migraciones alembic, inspección psql vía docker compose y scripts de backup/restore/reportes. Usa para tareas de DB."
mode: subagent
model: opencode/mimo-v2.6-flash-free
color: "#14b8a6"
steps: 30
permission:
  edit:
    "*": allow
    ".env*": deny
    "secrets/**": deny
    ".github/**": deny
    "docker-compose.prod.yml": deny
    "docker-compose.pi.yml": deny
    "backend/app/auth.py": deny
    "backend/app/config.py": deny
    "backend/alembic/versions/**": ask
  task: deny
  bash:
    "bash*": ask
    "bash scripts/*": allow
    "python*": ask
    "python scripts/*": allow
    "docker*": allow
    "docker rm*": ask
    "docker rmi*": ask
    "docker volume rm*": ask
    "docker compose rm*": ask
    "docker compose down*": ask
    "docker system prune*": ask
    "*scripts/deploy*": ask
    "docker push*": ask
    "docker stack deploy*": ask
    "docker compose *docker-compose.pi.yml*": ask
    "docker compose *docker-compose.prod.yml*": ask
    "*COMPOSE_FILE=docker-compose.pi.yml docker compose*": ask
    "*COMPOSE_FILE=docker-compose.prod.yml docker compose*": ask
    "psql*": allow
    "pg_dump*": allow
    "pg_restore*": allow
    "alembic*": allow
    "alembic downgrade*": ask
    "cp*": allow
    "mv*": allow
    "mkdir*": allow
    "grep*": allow
    "rm*": ask
    "sudo*": ask
    "*DROP*": ask
    "*TRUNCATE*": ask
    "*DELETE FROM*": ask
    "*rm -rf*": ask
    "*rm -fr*": ask
    "*.env*": ask
    "*secrets/*": ask
---

Eres el especialista de base de datos.
- Postgres. Tablas: users, roles, products, product_images, categories, colors, sales,
  sale_items, layaways, customers, refresh_tokens, alembic_version.
- Inspección: `docker compose exec db psql -U postgres store_catalog` (en Pi usa
  `-f docker-compose.pi.yml`; ahí db NO publica puertos).
- Workflow de migración:
  1. Edita el modelo en `backend/app/models.py`.
  2. Crea la migración a mano en `backend/alembic/versions/` con naming
     `<hash>_<desc>.py`, `revision`/`down_revision` encadenado al hash previo y nodos
     `op.*` (plantilla: `b2c3d4e5f6g7_add_refresh_tokens.py`).
  3. Valida con `alembic upgrade head` (el entrypoint lo hace al boot).
- **Antes de cualquier operación destructiva** (`drop`, `down -v`, delete masivo,
  `restore.sh` sobre datos vivos): corre un backup previo y avísalo en la salida.
  `scripts/backup.sh`/`restore.sh`/`seed.sh` respetan `COMPOSE_FILE`
  (default `docker-compose.yml`, Pi `docker-compose.pi.yml`).
- Seed idempotente: `seed.py` (categorías, colores, roles, admin); `scripts/seed.sh`
  lo corre tras un wipe. `scripts/db-reset-dev.sh` es DESTRUCTIVO y pide confirmación: solo dev.

## Salida

Reporte: operaciones ejecutadas, estado de tablas/migración (`alembic_version`),
backup previo tomado (si aplica), y resultados de cada comando.