"""
agent.py — Root Orchestrator Agent and ADK entry point.
"""

from __future__ import annotations
import os

os.environ['GOOGLE_CLOUD_LOCATION'] = 'global'

from .sub_agents.chart_agent import chart_agent
from google.adk.agents import LlmAgent
from google.adk.artifacts import GcsArtifactService
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.bigquery import BigQueryCredentialsConfig, BigQueryToolset
from google.adk.tools.bigquery.config import BigQueryToolConfig, WriteMode

# ── Config ────────────────────────────────────────────────────────────────────
_GCP_PROJECT_ID     = os.environ["GCP_PROJECT_ID"]
_BQ_PROJECT_ID      = os.environ.get("BQ_PROJECT_ID", _GCP_PROJECT_ID)
_BQ_DATASET_ID      = os.environ["BQ_DATASET_ID"]
_BQ_LOCATION        = os.environ.get("BQ_LOCATION", "US")
# Derive bucket name from ARTIFACT_SERVICE_URI so both uses share one env var.
# Agent Engine reads ARTIFACT_SERVICE_URI natively; we parse the bucket name from it.
_ARTIFACT_SERVICE_URI = os.environ["ARTIFACT_SERVICE_URI"]
_ARTIFACT_BUCKET      = _ARTIFACT_SERVICE_URI.replace("gs://", "").split("/")[0]
_ORCHESTRATOR_MODEL = os.environ.get("ORCHESTRATOR_MODEL", "gemini-2.5-pro")

# Use .get() so it doesn't crash locally. If None, it uses local gcloud auth.
_GE_AUTH_ID         = os.environ.get("GE_AUTH_ID") 

# ── Artifact Service ──────────────────────────────────────────────────────────
# Defined globally so the ADK runner auto-detects it.
artifact_service = GcsArtifactService(bucket_name=_ARTIFACT_BUCKET)

# ── Prompt ────────────────────────────────────────────────────────────────────
_PROMPT = f"""
You are a BigQuery Analytics Assistant for {_BQ_PROJECT_ID}.{_BQ_DATASET_ID}.
You help users query data and generate charts.
When a user asks a question, answer the question using text first
 - if the answer would be a good candidate for a chart, ask the user if they would like the data charted.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL: TOOL CALLING RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- NO PARALLEL TOOLS: You must NEVER call multiple tools at the same time. Only call ONE tool per turn.
- If you need to query data and then chart it, do it in two separate steps. Wait for the query to finish before calling the chart tool.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CALLING chart_agent_tool
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The chart_agent_tool accepts a SINGLE string parameter called `prompt`.
You CANNOT pass separate JSON fields. You must format your ENTIRE request into one single string.

Example format for the string:
"Create a bar chart titled 'Top Products'. X-axis: Product, Y-axis: Revenue. Data:[{{'Product': 'A', 'Revenue': 100}}, {{'Product': 'B', 'Revenue': 200}}]"

When chart_agent_tool finishes, tell the user: "I have generated the chart for you."
"""

# ── BigQuery Toolset ──────────────────────────────────────────────────────────
# Define base configuration
_bq_toolset_kwargs = {
    "bigquery_tool_config": BigQueryToolConfig(
        write_mode=WriteMode.BLOCKED,
        compute_project_id=_BQ_PROJECT_ID,
        location=_BQ_LOCATION,
    )
}

# Add credentials config ONLY if we are in production with a GE_AUTH_ID.
# If omitted (local testing), BigQuery falls back to Application Default Credentials.
if _GE_AUTH_ID:
    _bq_toolset_kwargs["credentials_config"] = BigQueryCredentialsConfig(
        external_access_token_key=_GE_AUTH_ID
    )

_bq_toolset = BigQueryToolset(**_bq_toolset_kwargs)

# ── AgentTool ─────────────────────────────────────────────────────────────────
_chart_agent_tool = AgentTool(agent=chart_agent)

# ── Root Agent ────────────────────────────────────────────────────────────────
root_agent = LlmAgent(
    name="bq_analytics_orchestrator",
    model=_ORCHESTRATOR_MODEL,
    instruction=_PROMPT,
    description="Analytics Assistant",
    tools=[_bq_toolset, _chart_agent_tool],
)