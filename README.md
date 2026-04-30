# BigQuery Analytics Agent

A multi-agent system built with Google ADK that answers natural language questions against a BigQuery dataset and generates high-quality charts on request. Runs locally and deploys to Vertex AI Agent Engine, fronted by Gemini Enterprise.

## Architecture

- **Root orchestrator** (`agent.py`) — translates natural language to BigQuery SQL, runs queries as the authenticated end user via Gemini Enterprise OAuth, and decides when to offer a chart
- **Chart sub-agent** (`sub_agents/chart_agent.py`) — receives chart instructions and data as a single prompt string, generates and executes Matplotlib code via Vertex AI Code Interpreter, and saves the chart as a session artifact
- **BigQuery toolset** — built-in ADK toolset, read-only, scoped to a single project/dataset
- **Artifact service** — charts are persisted to GCS and rendered inline in Gemini Enterprise

## Project Structure

```
BigQuery-Agent/
├── .gitignore
├── README.md
└── root_agent/
    ├── __init__.py
    ├── agent.py                      # root orchestrator
    ├── create_code_interpreter.py    # one-time Code Interpreter extension setup
    ├── deploy.sh                     # Agent Engine deployment script
    ├── requirements.txt
    ├── .env.example
    └── sub_agents/
        ├── __init__.py
        └── chart_agent.py            # chart sub-agent
```

## Prerequisites

- Python 3.11+
- Google Cloud project with billing enabled
- APIs enabled:

```bash
gcloud services enable \
  aiplatform.googleapis.com \
  bigquery.googleapis.com \
  storage.googleapis.com \
  discoveryengine.googleapis.com
```

- A GCS bucket for chart artifact storage
- Gemini Enterprise with an OAuth authorization resource configured (for Agent Engine deployment)

## Setup

### 1. Clone and install

```bash
git clone https://github.com/mlaslie/BigQuery-Agent.git
cd BigQuery-Agent/root_agent
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in all values in .env
```

### 3. Create the Code Interpreter Extension (one-time)

The chart agent requires a Vertex AI Code Interpreter Extension. Create it once and reuse across deployments:

```bash
python3 create_code_interpreter.py
```

The script prompts for your GCP project ID and region, creates the extension, and prints the resource name to add to your `.env` as `CODE_INTERPRETER_EXTENSION_NAME`.

### 4. GCS bucket permissions

Grant the Agent Engine service account write access to your artifact bucket:

```bash
gsutil iam ch \
  serviceAccount:service-PROJECT_NUMBER@gcp-sa-discoveryengine.iam.gserviceaccount.com:roles/storage.objectAdmin \
  gs://your-artifact-bucket-name
```

## Running Locally

For local runs, leave `GE_AUTH_ID` commented out in `.env`. The BigQuery toolset will use Application Default Credentials:

```bash
gcloud auth application-default login
```

Then run:

```bash
adk web
```

> **Note:** Chart generation requires a valid `CODE_INTERPRETER_EXTENSION_NAME` even when running locally — the Code Interpreter runs in Google Cloud regardless of where the agent is invoked.

## Deploy to Agent Engine

```bash
chmod +x deploy.sh
./deploy.sh
```

After deploying:

1. Copy the Agent Engine resource ID from the deploy output
2. Set `AGENT_ENGINE_ID` in your `.env` (used for future updates)
3. Register in Gemini Enterprise:
   - **Gemini Enterprise → Agents → Add agent → Custom agent via Agent Engine**
   - Paste the Agent Engine resource ID
   - Under **Authorizations**, add:
     - Authorization name: must exactly match `GE_AUTH_ID` in your `.env`
     - Token URI: `https://oauth2.googleapis.com/token`
     - Auth URI: `https://accounts.google.com/o/oauth2/auth`
     - Client ID and Client Secret from your OAuth credential
4. Add test users under agent permissions
5. Uncomment & update `GE_AUTH_ID` in `.env` and redeploy

### Update an existing deployment

```bash
adk deploy agent_engine \
  --project="YOUR_PROJECT_ID" \
  --region="us-central1" \
  --agent_engine_id="YOUR_AGENT_ENGINE_RESOURCE_ID" \
  .
```

## How It Works

1. User asks a natural language question in Gemini Enterprise
2. Orchestrator runs a read-only BigQuery query as the authenticated end user
3. Results are returned as a natural language answer
4. If results are chart-worthy, the orchestrator offers to visualize
5. User confirms → orchestrator selects chart type and passes a fully-specified prompt to the chart agent
6. Chart agent generates and executes Matplotlib code via Code Interpreter
7. Chart is saved to GCS and rendered inline in Gemini Enterprise

## Authentication

- **Local:** Uses Application Default Credentials (`gcloud auth application-default login`). Leave `GE_AUTH_ID` commented out in `.env`
- **Agent Engine + Gemini Enterprise:** Gemini Enterprise injects the user's OAuth token into session state after consent. The BigQuery toolset reads it via `GE_AUTH_ID`. Queries run with the end user's IAM permissions
