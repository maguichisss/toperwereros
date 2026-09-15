# Scripts

Occasion-driven maintenance and operational utilities. Nothing here runs as
part of the app — every script is meant for a specific, infrequent task. Most
are thin wrappers that drive **docker compose** (`COMPOSE_FILE` overrides the
compose file, default `docker-compose.yml`) against the running stack.

## Reference

| Script | What it does | When to run |
| --- | --- | --- |
| [backup.sh](backup.sh) | `pg_dump` + uploads copy into `backups/<timestamp>/`. | Scheduled / on-demand backup |
| [restore.sh](restore.sh) | Stop backend, drop/recreate DB from a backup, restore uploads. | Disaster recovery / migration |
| [seed.sh](seed.sh) | Idempotent re-seed of categories, colors, roles, default admin (`python seed.py` in the container). | After a raw DB wipe outside the normal compose flow |
| [db-diff-images.sh](db-diff-images.sh) | Report (or `--delete`) images out of sync between the uploads volume and `products.image_url` (wraps `db_diff_imgs.py`). | Image-hygiene check/cleanup |
| [gen-docs.sh](gen-docs.sh) | Regenerate `backend/docs.html` from `docs/api-reference.md` and run the two docs-drift tests (needs `backend/.venv`). | After editing the API reference |
| [reset-admin-password.sh](reset-admin-password.sh) `<pw>` | Reset the seeded `admin` user's bcrypt password. | Forgotten admin credentials |
| [db-reset-dev.sh](db-reset-dev.sh) | Drop/recreate the dev database and restart the backend (entrypoint rebuilds schema + seeds). Requires typing `RESET`; refuses non-dev `COMPOSE_FILE` unless `ALLOW_REMOTE=1`. | Dev DB nuke |
| [check-doc-links.py](check-doc-links.py) | Verifies every relative Markdown link in `README.md` and `docs/` resolves. | Before committing doc changes |
| [db-report.sh](db-report.sh) | Read-only business snapshot: products/stock, inventory value, sales today/week/month, apartados balances. | Pre-meeting / reconciliation |
| [rotate-backups.sh](rotate-backups.sh) `[keep=N]` | Prune `backups/` directories, keeping the newest N (default 5). | Scheduled retention |
| [verify-backup.sh](verify-backup.sh) `[dir]` | Check a backup's SQL dump is valid gzip, non-empty, and uploads are present. | Post-backup assurance |
| [stack-status.sh](stack-status.sh) | `docker compose ps` + backend `/api/health` check (`BACKEND_URL` overrides). | Quick health sanity |
| [export-openapi.sh](export-openapi.sh) | Snapshot the backend OpenAPI schema to stdout (`JWT_SECRET` env only). | API contract diffing / tooling |
| [init-env.sh](init-env.sh) | Create `backend/.env` from `.env.example` with a fresh random `JWT_SECRET`. Never overwrites an existing `.env`. | Fresh local / Pi setup |
| [preview-catalog.sh](preview-catalog.sh) `[theme]` | Login (`ADMIN_USER`/`ADMIN_PASSWORD` or the seeded default) and download a themed catalog PDF to `./catalogo-preview.pdf`. | Eyeball the printable catalog |
| [deploy.sh](deploy.sh) | GCP deploy master: runs infra setup, build/push, and Cloud Run deploy in sequence. Requires `GCP_PROJECT`, `DB_PASSWORD`, `GCS_BUCKET`, `JWT_SECRET`, `DEFAULT_ADMIN_PASSWORD`. | Full Cloud Run deployment |
| [deploy-setup-infra.sh](deploy-setup-infra.sh) | One-time GCP provisioning: APIs, Artifact Registry, Cloud SQL, GCS bucket, backend SA, Secret Manager secrets. | First deploy / new project |
| [deploy-build-push.sh](deploy-build-push.sh) | Build `backend-prod`/`frontend-prod` and push to Artifact Registry (`IMAGE_TAG` defaults to the short SHA). | Image build/push step |
| [deploy-cloud-run.sh](deploy-cloud-run.sh) | Deploy backend/frontend services to Cloud Run with secrets, proxy, and CORS wiring. | Cloud Run deploy step |

## Conventions & notes

- All scripts are `set -e` and exit non-zero on failure.
- `COMPOSE_FILE` selects the compose file (`docker-compose.yml`,
  `docker-compose.pi.yml`, `docker-compose.prod.yml`).
- **`reset-admin-password.sh` and `preview-catalog.sh` take passwords on the
  command line / environment — avoid them in shared shells and never log them.**
- **`db-reset-dev.sh` is destructive** by design and guarded; it targets the
  local dev database only.
- `backup.sh` / `restore.sh` live here; usage is documented in
  [deployment.md](../docs/technical/deployment.md).
- Backend Python utilities (`backend/scripts/gen_api_docs.py`,
  `backend/db_diff_imgs.py`, `backend/seed.py`) stay under `backend/`; these
  scripts wrap them for the live stack.