#!/bin/bash
# ──────────────────────────────────────────────────────────────
# deploy-setup-infra.sh — One-time GCP infrastructure provisioning
# ──────────────────────────────────────────────────────────────
set -euo pipefail

# ── Configuration (edit these) ────────────────────────────────
PROJECT_ID="${GCP_PROJECT:?Set GCP_PROJECT env var}"
REGION="${GCP_REGION:-us-central1}"
INSTANCE_NAME="store-catalog"
DB_NAME="store_catalog"
DB_PASSWORD="${DB_PASSWORD:?Set DB_PASSWORD env var}"
BUCKET_NAME="${GCS_BUCKET:?Set GCS_BUCKET env var}"
BACKEND_SA="store-catalog-backend"
BACKEND_SA_EMAIL="${BACKEND_SA}@${PROJECT_ID}.iam.gserviceaccount.com"
AR_REPO="store-catalog"

echo "=== GCP Infrastructure Setup ==="
echo "Project:  ${PROJECT_ID}"
echo "Region:   ${REGION}"
echo "Instance: ${INSTANCE_NAME}"
echo "Bucket:   ${BUCKET_NAME}"
echo ""

# ── 1. Set active project ────────────────────────────────────
echo "▶ Setting active project..."
gcloud config set project "${PROJECT_ID}"

# ── 2. Enable required APIs ──────────────────────────────────
echo "▶ Enabling APIs..."
gcloud services enable \
    run.googleapis.com \
    sqladmin.googleapis.com \
    storage.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com \
    iamcredentials.googleapis.com

# ── 3. Create Artifact Registry repo ─────────────────────────
echo "▶ Creating Artifact Registry repo..."
gcloud artifacts repositories create "${AR_REPO}" \
    --repository-format=docker \
    --location="${REGION}" \
    --description="Store Catalog Docker images" \
    2>/dev/null || echo "  (already exists, skipping)"

# ── 4. Create Cloud SQL instance ─────────────────────────────
echo "▶ Creating Cloud SQL instance..."
if gcloud sql instances describe "${INSTANCE_NAME}" --project="${PROJECT_ID}" &>/dev/null; then
    echo "  (already exists, skipping)"
else
    gcloud sql instances create "${INSTANCE_NAME}" \
        --database-version=POSTGRES_16 \
        --region="${REGION}" \
        --tier=db-f1-micro \
        --storage-size=10GB \
        --storage-auto-increase \
        --backup-start-time=03:00 \
        --no-assign-ip \
        --root-password="${DB_PASSWORD}"
fi

# ── 5. Create database ──────────────────────────────────────
echo "▶ Creating database..."
gcloud sql databases create "${DB_NAME}" --instance="${INSTANCE_NAME}" \
    2>/dev/null || echo "  (already exists, skipping)"

# ── 6. Create GCS bucket ────────────────────────────────────
echo "▶ Creating GCS bucket..."
gsutil mb -l "${REGION}" -b on "gs://${BUCKET_NAME}" \
    2>/dev/null || echo "  (already exists, skipping)"

# ── 7. Create service account ────────────────────────────────
echo "▶ Creating backend service account..."
gcloud iam service-accounts create "${BACKEND_SA}" \
    --display-name="Store Catalog Backend" \
    2>/dev/null || echo "  (already exists, skipping)"

# ── 8. Grant IAM roles ──────────────────────────────────────
echo "▶ Granting IAM roles..."
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${BACKEND_SA_EMAIL}" \
    --role="roles/cloudsql.client" \
    --condition=None >/dev/null 2>&1

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${BACKEND_SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor" \
    --condition=None >/dev/null 2>&1

gsutil iam ch "serviceAccount:${BACKEND_SA_EMAIL}:objectAdmin" \
    "gs://${BUCKET_NAME}" 2>/dev/null || true

# ── 9. Create secrets in Secret Manager ─────────────────────
echo "▶ Creating secrets in Secret Manager..."
create_secret() {
    local NAME="$1"
    local VALUE="$2"
    if gcloud secrets describe "${NAME}" --project="${PROJECT_ID}" &>/dev/null; then
        echo "  Secret '${NAME}' exists, adding new version..."
        echo -n "${VALUE}" | gcloud secrets versions add "${NAME}" --data-file=- 2>/dev/null
    else
        echo -n "${VALUE}" | gcloud secrets create "${NAME}" --data-file=- 2>/dev/null
    fi
}

JWT_SECRET_VAL="${JWT_SECRET:?Set JWT_SECRET env var}"
ADMIN_PASSWORD_VAL="${DEFAULT_ADMIN_PASSWORD:?Set DEFAULT_ADMIN_PASSWORD env var}"

create_secret "jwt-secret" "${JWT_SECRET_VAL}"
create_secret "admin-password" "${ADMIN_PASSWORD_VAL}"
create_secret "db-password" "${DB_PASSWORD}"
create_secret "db-url" "postgresql://postgres:${DB_PASSWORD}@127.0.0.1:5432/${DB_NAME}"

# ── 10. Grant Secret Manager access to service account ──────
echo "▶ Granting Secret Manager access..."
for SECRET_NAME in jwt-secret admin-password db-password db-url; do
    gcloud secrets add-iam-policy-binding "${SECRET_NAME}" \
        --member="serviceAccount:${BACKEND_SA_EMAIL}" \
        --role="roles/secretmanager.secretAccessor" \
        --condition=None >/dev/null 2>&1
done

echo ""
echo "=== Infrastructure setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Run: scripts/deploy-build-push.sh"
echo "  2. Run: scripts/deploy-cloud-run.sh"
