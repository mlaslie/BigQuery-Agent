"""
chart_agent.py — Chart Sub-Agent definition.
"""

from __future__ import annotations
import os

# Force model calls to the global endpoint
os.environ['GOOGLE_CLOUD_LOCATION'] = 'global'

from google.adk.agents import LlmAgent
from google.adk.code_executors import VertexAiCodeExecutor

# ── Config ────────────────────────────────────────────────────────────────────
_CHART_AGENT_MODEL         = os.environ.get("CHART_AGENT_MODEL", "gemini-2.5-flash")
_CODE_INTERPRETER_RESOURCE = os.environ["CODE_INTERPRETER_EXTENSION_NAME"]

# ── Prompt ────────────────────────────────────────────────────────────────────
# ── Prompt ────────────────────────────────────────────────────────────────────
_PROMPT = """
You are a Chart Execution Agent. You receive a text prompt containing data and chart instructions.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CHARTING STANDARDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- ALWAYS use Matplotlib (`import matplotlib.pyplot as plt`) and Pandas.
- Do NOT use Plotly, it will crash the sandbox.
- Save the chart exactly as: `plt.savefig('chart.png', bbox_inches='tight')`
- CRITICAL: NEVER call `plt.show()`. It will cause duplicate charts to appear in the UI.
- ALWAYS call `plt.close()` after saving to clear the memory buffer.
- The data is provided in your text prompt. Parse it directly into a pandas DataFrame.
- Print "CHART_SAVED" to stdout after saving successfully.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL — TURN TERMINATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Generate the Python code and execute it using your code tool.
2. Wait for the execution to finish.
3. You MUST provide a final text response. Do NOT stop silently.
   Output: "STATUS:success MESSAGE: Chart generated successfully."
"""

# ── Agent ─────────────────────────────────────────────────────────────────────
chart_agent = LlmAgent(
    name="chart_agent",
    model=_CHART_AGENT_MODEL,
    instruction=_PROMPT,
    description=(
        "Generates charts. "
        "IMPORTANT: You must pass a SINGLE STRING containing the chart instructions and data."
    ),
    code_executor=VertexAiCodeExecutor(
        resource_name=_CODE_INTERPRETER_RESOURCE,
        stateful=True,
    ),
)