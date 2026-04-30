#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy.sh — Deploy the BigQuery Analytics Agent to Vertex AI Agent Engine
#
# Prerequisites:
#   1. gcloud CLI installed and authenticated:
#        gcloud auth login
#        gcloud auth application-default login
#        gcloud config set project $GCP_PROJECT_ID
#
#   2. Required APIs enabled:
#        gcloud services enable \
#          aiplatform.googleapis.com \
#          bigquery.googleapis.com \
#          storage.googleapis.com \
#          discoveryengine.googleapis.com
#
#   3. GCS artifact bucket created:
#        gcloud storage buckets create gs://$ARTIFACT_BUCKET \
#          --project=$GCP_PROJECT_ID \
#          --location=$BQ_LOCATION
#
#   4. .env file populated (copy from .env.example)
#
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh
#
# To update an existing deployment, set AGENT_ENGINE_ID in .env and re-run.
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# Resolve the directory this script lives in — needed for absolute paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load environment variables from .env
if [ -f "$SCRIPT_DIR/.env" ]; then
  export $(grep -v '^#' "$SCRIPT_DIR/.env" | grep -v '^$' | xargs)
else
  echo "ERROR: .env file not found. Copy .env.example to .env and fill in values."
  exit 1
fi

# Validate required variables
: "${GCP_PROJECT_ID:?GCP_PROJECT_ID must be set in .env}"
: "${GCP_LOCATION:?GCP_LOCATION must be set in .env}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Deploying BigQuery Analytics Agent"
echo "  Project  : $GCP_PROJECT_ID"
echo "  Location : $GCP_LOCATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Deploy to Vertex AI Agent Engine ─────────────────────────────────────────
# Notes:
#   - requirements_file uses an absolute path because adk deploy changes the
#     working directory during staging, breaking relative paths.
#   - staging_bucket is intentionally omitted (deprecated in current ADK).
adk deploy agent_engine \
  --project="$GCP_PROJECT_ID" \
  --region="$GCP_LOCATION" \
  --display_name="BigQuery Analytics Agent" \
  --description="Natural language BigQuery analytics with charting. Runs queries as the authenticated end user via Gemini Enterprise OAuth." \
  --requirements_file="$SCRIPT_DIR/requirements.txt" \
  "$SCRIPT_DIR"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Deployment complete."
echo ""
echo "  Next steps:"
echo "  1. Copy the Agent Engine resource ID from the output above."
echo "  2. Set AGENT_ENGINE_ID in your .env file."
echo "  3. Register the agent in Gemini Enterprise:"
echo "       - Go to Gemini Enterprise > Agents > + Add agent"
echo "       - Select 'Custom agent via Agent Engine'"
echo "       - Paste the Agent Engine resource ID"
echo "       - Under Authorizations, click Add authorization:"
echo "           Authorization name : \$GE_AUTH_ID  (e.g. ge-bq-agent-auth-id)"
echo "           Client ID          : <your OAuth client ID>"
echo "           Client Secret      : <your OAuth client secret>"
echo "           Token URI          : https://oauth2.googleapis.com/token"
echo "           Auth URI           : https://accounts.google.com/o/oauth2/auth"
echo "  4. Add test users under agent permissions."
echo "  5. Open Gemini Enterprise > Agents > Preview to test."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
