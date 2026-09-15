#!/bin/bash
# ──────────────────────────────────────────────────────────────
# deploy.sh — Master deployment script
# Runs infrastructure setup, build/push, and Cloud Run deployment
# ──────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "============================================"
echo "  Store Catalog — GCP Deployment"
echo "============================================"
echo ""

# Check required env vars
for VAR in GCP_PROJECT DB_PASSWORD GCS_BUCKET JWT_SECRET DEFAULT_ADMIN_PASSWORD; do
    if [ -z "${!VAR:-}" ]; then
        echo "ERROR: ${VAR} is not set. Export it before running."
        exit 1
    fi
done

# Step 1: Infrastructure
echo "━━━ Step 1/3: Infrastructure Setup ━━━"
bash "${SCRIPT_DIR}/deploy-setup-infra.sh"
echo ""

# Step 2: Build & Push
echo "━━━ Step 2/3: Build & Push ━━━"
bash "${SCRIPT_DIR}/deploy-build-push.sh"
echo ""

# Step 3: Deploy
echo "━━━ Step 3/3: Cloud Run Deploy ━━━"
bash "${SCRIPT_DIR}/deploy-cloud-run.sh"
echo ""

echo "============================================"
echo "  Deployment complete!"
echo "============================================"
