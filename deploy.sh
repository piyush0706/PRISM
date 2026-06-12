#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# PRISM — Google Cloud Run deployment script
# Usage: bash deploy.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Configuration — edit these ────────────────────────────────────────────────
PROJECT_ID="your-gcp-project-id"        # gcloud projects list
REGION="us-central1"                    # cheapest multi-tenant region
SERVICE_NAME="prism-review-bot"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Secrets — fill in your real values or export them before running
GITHUB_TOKEN="${GITHUB_TOKEN:?GITHUB_TOKEN env var is required}"
GEMINI_API_KEY="${GEMINI_API_KEY:?GEMINI_API_KEY env var is required}"
# ─────────────────────────────────────────────────────────────────────────────

echo "🔨  Building and pushing container image..."
gcloud builds submit \
  --tag "${IMAGE}" \
  --project "${PROJECT_ID}" \
  .

echo "🚀  Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE}" \
  --platform managed \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 10 \
  --memory 512Mi \
  --cpu 1 \
  --timeout 60 \
  --set-env-vars "GITHUB_TOKEN=${GITHUB_TOKEN},GEMINI_API_KEY=${GEMINI_API_KEY}"

echo ""
echo "✅  Deployment complete!"
echo "🌐  Public URL:"
gcloud run services describe "${SERVICE_NAME}" \
  --platform managed \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --format "value(status.url)"
