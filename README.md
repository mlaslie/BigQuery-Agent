# BigQuery Analytics Agent

A multi-agent system built with Google ADK that answers natural language questions against a BigQuery dataset and generates high-quality charts on request. Deployed on Vertex AI Agent Engine and fronted by Gemini Enterprise.

## Architecture

- **Root orchestrator** (`agent.py`) — translates natural language to BigQuery SQL, runs queries as the authenticated end user via Gemini Enterprise OAuth, and decides when to offer a chart
- **Chart sub-agent** (`sub_agents/chart_agent.py`) — receives a fully-specified chart request from the orchestrator, generates and executes Plotly/Matplotlib code via Vertex AI Code Interpreter, and saves the chart as a session artifact
- **BigQuery toolset** — built-in ADK toolset, read-only, scoped to a single project/dataset
- **Artifact service** — charts are saved to GCS and rendered inline in Gemini Enterprise

## Prerequisites

- Gemini Enterprise configured with an OAuth authorization resource
- A GCS bucket for chart artifact storage
- A Vertex AI Code Interpreter Extension (see setup below)

### Create the Code Interpreter Extension

Run once — the resource name goes in your `.env` as `CODE_INTERPRETER_EXTENSION_NAME`:

```bash
python3 -c "
import vertexai
from vertexai.preview.extensions import Extension
vertexai.init(project='YOUR_PROJECT_ID', location='global')
ext = Extension.from_hub('code_interpreter')
print(ext.gca_resource.name)
"
```

### GCS Bucket Permissions

Grant the Agent Engine service account write access to your artifact bucket:

```bash
gsutil iam ch \
  serviceAccount:service-PROJECT_NUMBER@gcp-sa-discoveryengine.iam.gserviceaccount.com:roles/storage.objectAdmin \
  gs://your-artifact-bucket-name
```

## Setup

```bash
git clone https://github.com/mlaslie/BigQuery-Agent.git
cd BigQuery-Agent/root_agent
cp .env.example .env
# Fill in all values in .env
```

## Run Locally

```bash
pip install -r requirements.txt
adk run root_agent
```

Or with the ADK dev UI:

```bash
adk web
```

## Deploy to Agent Engine

```bash
chmod +x deploy.sh
./deploy.sh
```

After deploying, register the agent in Gemini Enterprise:

1. Go to **Gemini Enterprise → Agents → Add agent → Custom agent via Agent Engine**
2. Paste the Agent Engine resource ID from the deploy output
3. Under **Authorizations**, add:
   - Authorization name: value of `GE_AUTH_ID` in your `.env`
4. Add test users under agent permissions

To update an existing deployment:

```bash
adk deploy agent_engine \
  --project="YOUR_PROJECT_ID" \
  --region="us-central1" \
  --resource_id="YOUR_AGENT_ENGINE_RESOURCE_ID" \
  --requirements_file="./requirements.txt" \
  .
```

## Project Structure

```
BigQuery-Agent/
├── root_agent/
│   ├── __init__.py
│   ├── agent.py              # root orchestrator
│   ├── deploy.sh             # deployment script
│   ├── requirements.txt
│   ├── .env.example
│   └── sub_agents/
│       ├── __init__.py
│       └── chart_agent.py    # chart sub-agent
└── .gitignore
```
