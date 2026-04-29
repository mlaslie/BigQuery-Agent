#!/usr/bin/env bash
# deploy.sh — Deploy the BigQuery Analytics Agent to Vertex AI Agent Engine

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/.env" ]; then
  export $(grep -v '^#' "$SCRIPT_DIR/.env" | grep -v '^$' | xargs)
else
  echo "ERROR: .env file not found. Copy .env.example to .env and fill in values."
  exit 1
fi

: "${GCP_PROJECT_ID:?GCP_PROJECT_ID must be set in .env}"
: "${GCP_LOCATION:?GCP_LOCATION must be set in .env}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Deploying BigQuery Analytics Agent"
echo "  Project  : $GCP_PROJECT_ID"
echo "  Location : $GCP_LOCATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

adk deploy agent_engine \
  --project="$GCP_PROJECT_ID" \
  --region="$GCP_LOCATION" \
  --display_name="BigQuery Analytics Agent" \
  --description="Natural language BigQuery analytics with charting via Gemini Enterprise." \
  --requirements_file="$SCRIPT_DIR/requirements.txt" \
  "$SCRIPT_DIR"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Deployment complete."
echo ""
echo "  Next steps:"
echo "  1. Copy the Agent Engine resource ID from the output above."
echo "  2. Register in Gemini Enterprise:"
echo "       Agents > Add agent > Custom agent via Agent Engine"
echo "       Under Authorizations, add:"
echo "         Authorization name : \$GE_AUTH_ID"
echo "  3. Add test users under agent permissions."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
