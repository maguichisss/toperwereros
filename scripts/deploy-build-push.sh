#!/bin/bash
# ──────────────────────────────────────────────────────────────
# deploy-build-push.sh — Build Docker images and push to Artifact Registry
# ──────────────────────────────────────────────────────────────
set -euo pipefail

PROJECT_ID="${GCP_PROJECT:?Set GCP_PROJECT env var}"
REGION="${GCP_REGION:-us-central1}"
AR_REPO="store-catalog"
TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD)}"
AR_HOST="${REGION}-docker.pkg.dev"

echo "=== Building & Pushing Docker Images ==="
echo "Project: ${PROJECT_ID}"
echo "Region:  ${REGION}"
echo "Tag:     ${TAG}"
echo ""

# ── 1. Configure Docker for Artifact Registry ────────────────
echo "▶ Configuring Docker authentication..."
gcloud auth configure-docker "${AR_HOST}" --quiet

# ── 2. Build backend image ──────────────────────────────────
BACKEND_IMAGE="${AR_HOST}/${PROJECT_ID}/${AR_REPO}/backend:${TAG}"
echo "▶ Building backend image: ${BACKEND_IMAGE}"
docker build \
    --target backend-prod \
    -t "${BACKEND_IMAGE}" \
    ./backend

# ── 3. Build frontend image ─────────────────────────────────
FRONTEND_IMAGE="${AR_HOST}/${PROJECT_ID}/${AR_REPO}/frontend:${TAG}"
echo "▶ Building frontend image: ${FRONTEND_IMAGE}"
docker build \
    --target frontend-prod \
    -t "${FRONTEND_IMAGE}" \
    ./frontend

# ── 4. Push images ──────────────────────────────────────────
echo "▶ Pushing backend image..."
docker push "${BACKEND_IMAGE}"

echo "▶ Pushing frontend image..."
docker push "${FRONTEND_IMAGE}"

echo ""
echo "=== Build & push complete ==="
echo "Backend:  ${BACKEND_IMAGE}"
echo "Frontend: ${FRONTEND_IMAGE}"
echo ""
echo "Next step: scripts/deploy-cloud-run.sh"
