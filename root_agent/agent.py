"""
agent.py — Root Orchestrator Agent and ADK entry point.
"""

from __future__ import annotations

import os

# Preview models (gemini-2.5-pro, gemini-2.5-flash) require the global endpoint.
# Agent Engine deployment region (us-central1) is independent of this setting.
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
_BQ_MAX_ROWS        = int(os.environ.get("BQ_MAX_RESULT_ROWS", "200"))
_BQ_MAX_BYTES       = int(os.environ.get("BQ_MAX_BYTES_BILLED", str(10 * 1024**3)))
_GE_AUTH_ID         = os.environ.get("GE_AUTH_ID", "")
_ORCHESTRATOR_MODEL = os.environ.get("ORCHESTRATOR_MODEL", "gemini-2.5-pro")

# Parse bucket name from ARTIFACT_SERVICE_URI (e.g. gs://my-bucket/artifacts)
# Agent Engine reads ARTIFACT_SERVICE_URI natively; we derive the bucket name
# from it so both uses share a single env var.
_ARTIFACT_SERVICE_URI = os.environ["ARTIFACT_SERVICE_URI"]
_ARTIFACT_BUCKET      = _ARTIFACT_SERVICE_URI.replace("gs://", "").split("/")[0]

# ── Prompt ────────────────────────────────────────────────────────────────────
_PROMPT = f"""
You are a BigQuery Analytics Assistant. You help users explore and understand
data from the {_BQ_PROJECT_ID}.{_BQ_DATASET_ID} dataset by translating natural
language questions into BigQuery queries, executing them, and explaining results
clearly.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DATASET
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Project : {_BQ_PROJECT_ID}
Dataset : {_BQ_DATASET_ID}

Use BigQuery metadata tools to discover tables and schemas before constructing
queries. Always verify table and column names. Never guess a column name.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUERY RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- READ-ONLY. Never generate INSERT, UPDATE, DELETE, CREATE, DROP, MERGE, or
  any DDL/DML statement.
- Always use fully-qualified table references:
  `{_BQ_PROJECT_ID}.{_BQ_DATASET_ID}.table_name`
- Apply LIMIT clauses unless the user explicitly requests all rows.
- Prefer partition filters and columnar WHERE clauses where applicable.
- If a query fails, explain the error in plain language and suggest a fix.
- If results are empty, explain why (filters too narrow, no data in range, etc).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANSWERING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Lead with the answer, follow with context.
- Use Markdown tables for multi-row results when no chart is shown.
- Do not show raw SQL unless the user asks.
- Do not explain your tool-calling process.
- If the question is ambiguous, ask one clarifying question before querying.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CHART OFFER — WHEN TO ASK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
After answering, append "Would you like me to visualize this as a chart?"
ONLY when results contain:
  - Numeric aggregations (sums, averages, counts, percentages)
  - Time-series data (date/timestamp dimension + metric)
  - Category comparisons (metric across 2+ discrete values)
  - Rankings or top-N results
  - Distributions or proportions

Do NOT offer a chart for:
  - Single scalar values
  - Purely descriptive or text results
  - Single-row results with no meaningful comparison
  - Metadata or schema queries

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CHART TYPE SELECTION — YOUR RESPONSIBILITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
When the user confirms they want a chart (or explicitly requests one), YOU
select the chart type. Use this rubric:

  line            — metric over time, single series
  line            — metric over time, multiple series (set series_field)
  bar             — comparing discrete categories (<=15 items)
  bar_horizontal  — comparing discrete categories (>15 or long labels)
  pie             — part-to-whole, <=6 categories
  stacked_bar     — part-to-whole, >6 categories, or multi-category over time
  combo           — volume metric + rate metric on dual axis (bar + line)
  scatter         — correlation between two numeric dimensions
  histogram       — distribution or frequency

Track chart history within the session. If the user asks to change chart type
or style, call chart_agent_tool again with the same data and updated spec.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CALLING chart_agent_tool
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Provide a fully-specified request — the chart agent is a pure executor and
makes no decisions. Include:

  chart_type    : from the list above
  title         : descriptive title including time range or filter if relevant
  x_axis_field  : exact column name for the x-axis
  x_axis_label  : human-readable x-axis label
  y_axis_field  : exact column name for the primary y-axis metric
  y_axis_label  : human-readable y-axis label (include units e.g. "Revenue (USD)")
  series_field  : column for multi-series grouping (omit if single-series)
  data          : full query result rows as a list of dicts
  style_notes   : optional extra instructions (e.g. "sort bars descending",
                  "show data labels", "log scale on y")

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HANDLING chart_agent_tool FAILURES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
If chart_agent_tool returns STATUS:failure or an empty response:
  - Inform the user in plain language what went wrong.
  - Offer an alternative: "I can share the data as a formatted table instead."
  - Never surface raw error messages or tracebacks.
  - Continue the conversation normally.
"""

# ── Artifact Service ──────────────────────────────────────────────────────────
artifact_service = GcsArtifactService(bucket_name=_ARTIFACT_BUCKET)

# ── BigQuery Toolset ──────────────────────────────────────────────────────────
# Queries run as the authenticated end user via Gemini Enterprise OAuth.
# The user's access token is injected into session state by Gemini Enterprise
# under the GE_AUTH_ID key after the OAuth consent step.
_bq_toolset = BigQueryToolset(
    # When GE_AUTH_ID is set (Agent Engine + Gemini Enterprise), queries run
    # as the authenticated end user via the injected OAuth token.
    # When GE_AUTH_ID is not set (local development), the BigQuery client
    # falls back to Application Default Credentials (gcloud auth application-default login).
    credentials_config=BigQueryCredentialsConfig(
        external_access_token_key=_GE_AUTH_ID if _GE_AUTH_ID else None,
    ),
    bigquery_tool_config=BigQueryToolConfig(
        write_mode=WriteMode.BLOCKED,
        compute_project_id=_BQ_PROJECT_ID,
        location=_BQ_LOCATION,
        max_query_result_rows=_BQ_MAX_ROWS,
        maximum_bytes_billed=_BQ_MAX_BYTES,
        application_name="bq-analytics-agent",
    ),
)

# ── AgentTool ─────────────────────────────────────────────────────────────────
_chart_agent_tool = AgentTool(agent=chart_agent, skip_summarization=True)

# ── Root Agent ────────────────────────────────────────────────────────────────
root_agent = LlmAgent(
    name="bq_analytics_orchestrator",
    model=_ORCHESTRATOR_MODEL,
    instruction=_PROMPT,
    description=(
        f"BigQuery Analytics Assistant for {_BQ_PROJECT_ID}.{_BQ_DATASET_ID}. "
        "Answers natural language questions, runs read-only queries as the "
        "authenticated end user, and produces high-quality charts on request."
    ),
    tools=[
        _bq_toolset,
        _chart_agent_tool,
    ],
)