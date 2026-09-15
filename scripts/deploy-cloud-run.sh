#!/bin/bash
# ──────────────────────────────────────────────────────────────
# deploy-cloud-run.sh — Deploy backend and frontend to Cloud Run
# ──────────────────────────────────────────────────────────────
set -euo pipefail

PROJECT_ID="${GCP_PROJECT:?Set GCP_PROJECT env var}"
REGION="${GCP_REGION:-us-central1}"
AR_REPO="store-catalog"
TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD)}"
AR_HOST="${REGION}-docker.pkg.dev"
INSTANCE_NAME="store-catalog"
DB_NAME="store_catalog"
BACKEND_SA="store-catalog-backend@${PROJECT_ID}.iam.gserviceaccount.com"

BACKEND_IMAGE="${AR_HOST}/${PROJECT_ID}/${AR_REPO}/backend:${TAG}"
FRONTEND_IMAGE="${AR_HOST}/${PROJECT_ID}/${AR_REPO}/frontend:${TAG}"

# Read DB_PASSWORD from Secret Manager (fallback to env var)
# Kept for backward compatibility; DATABASE_URL itself is now a secret.
DB_PASSWORD="${DB_PASSWORD:-}"
if [ -z "$DB_PASSWORD" ]; then
    DB_PASSWORD=$(gcloud secrets versions access latest --secret="db-password" 2>/dev/null || true)
fi

echo "=== Deploying to Cloud Run ==="
echo "Project: ${PROJECT_ID}"
echo "Region:  ${REGION}"
echo "Tag:     ${TAG}"
echo ""

# ── 1. Deploy backend ───────────────────────────────────────
echo "▶ Deploying backend to Cloud Run..."
BACKEND_URL=$(gcloud run deploy store-catalog-backend \
    --image="${BACKEND_IMAGE}" \
    --region="${REGION}" \
    --platform=managed \
    --service-account="${BACKEND_SA}" \
    --add-cloudsql-instances="${PROJECT_ID}:${REGION}:${INSTANCE_NAME}" \
    --set-secrets="JWT_SECRET=jwt-secret:latest,DEFAULT_ADMIN_PASSWORD=admin-password:latest,DATABASE_URL=db-url:latest" \
    --set-env-vars="CLOUD_SQL_CONNECTION_STRING=${PROJECT_ID}:${REGION}:${INSTANCE_NAME},GCS_BUCKET=${GCS_BUCKET},GCP_PROJECT=${PROJECT_ID},CORS_ORIGINS=*,LOG_LEVEL=WARNING" \
    --port=8080 \
    --memory=512Mi \
    --cpu=1 \
    --min-instances=0 \
    --max-instances=10 \
    --no-allow-unauthenticated \
    --format='value(status.url)' 2>&1)

# Extract just the URL (gcloud outputs deployment info to stderr, URL to stdout)
BACKEND_URL=$(gcloud run services describe store-catalog-backend \
    --region="${REGION}" \
    --format='value(status.url)' 2>/dev/null)

echo "  Backend deployed: ${BACKEND_URL}"

# ── 2. Update CORS_ORIGINS with actual frontend URL ─────────
echo "▶ Updating backend CORS_ORIGINS..."
# We don't know the frontend URL yet, so use * for now.
# After frontend deploy, re-run with the actual URL:
# gcloud run services update store-catalog-backend --set-env-vars="CORS_ORIGINS=https://FRONTEND_URL" --region=REGION

# ── 3. Deploy frontend ─────────────────────────────────────
echo "▶ Deploying frontend to Cloud Run..."
FRONTEND_URL=$(gcloud run deploy store-catalog-frontend \
    --image="${FRONTEND_IMAGE}" \
    --region="${REGION}" \
    --platform=managed \
    --set-env-vars="BACKEND_URL=${BACKEND_URL}" \
    --port=8080 \
    --memory=256Mi \
    --cpu=1 \
    --min-instances=0 \
    --max-instances=5 \
    --allow-unauthenticated \
    --format='value(status.url)' 2>&1)

FRONTEND_URL=$(gcloud run services describe store-catalog-frontend \
    --region="${REGION}" \
    --format='value(status.url)' 2>/dev/null)

echo "  Frontend deployed: ${FRONTEND_URL}"

# ── 4. Update backend CORS with frontend URL ────────────────
echo "▶ Updating backend CORS_ORIGINS with frontend URL..."
gcloud run services update store-catalog-backend \
    --region="${REGION}" \
    --set-env-vars="CORS_ORIGINS=${FRONTEND_URL},LOG_LEVEL=WARNING" \
    --quiet

echo ""
echo "=== Deployment complete ==="
echo ""
echo "Frontend: ${FRONTEND_URL}"
echo "Backend:  ${BACKEND_URL}"
echo "Health:   ${BACKEND_URL}/api/health"
echo "Docs:     ${BACKEND_URL}/swagger"
