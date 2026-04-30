"""
chart_agent.py — Chart Sub-Agent definition.

Exports `chart_agent` (LlmAgent) only.
The AgentTool wrapper is created in agent.py where it is consumed.

Prerequisites:
  Create a Code Interpreter Extension once in the global location:

  python3 -c "
  import vertexai
  from vertexai.preview.extensions import Extension
  vertexai.init(project='YOUR_PROJECT_ID', location='global')
  ext = Extension.from_hub('code_interpreter')
  print(ext.gca_resource.name)
  "

  Set the output as CODE_INTERPRETER_EXTENSION_NAME in your .env file.
"""

from __future__ import annotations

import os

# Preview models require the global endpoint — must be set before ADK imports.
os.environ['GOOGLE_CLOUD_LOCATION'] = 'global'

from google.adk.agents import LlmAgent

# ── Config ────────────────────────────────────────────────────────────────────
_CHART_AGENT_MODEL         = os.environ.get("CHART_AGENT_MODEL", "gemini-2.5-flash")
_CODE_INTERPRETER_RESOURCE = os.environ.get("CODE_INTERPRETER_EXTENSION_NAME", "")

# ── Prompt ────────────────────────────────────────────────────────────────────
_PROMPT = """
You are a Chart Execution Agent. Your sole responsibility is to receive a
fully-specified chart request from the orchestrator, generate Python charting
code, execute it using the code execution tool, and return a structured
text response.

You are a pure executor. You do NOT decide chart types, axis labels, titles, or
interpret data. All decisions have already been made by the orchestrator.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CHARTING STANDARDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Always use Plotly (plotly.express or plotly.graph_objects) unless the chart type
is unsupported, then fall back to Matplotlib.

Every chart MUST include:
  - Title from the spec
  - Labeled axes with units if provided
  - Legend when multiple series are present
  - White background, clean gridlines
  - Color palette (use in order):
      #4285F4, #EA4335, #FBBC05, #34A853, #FF6D00, #AA00FF, #00BCD4, #8D6E63
  - Font: Arial or sans-serif, min 12px labels, 14px title
  - Output size: 1200 x 700 px
  - No Plotly logo: config={'displaylogo': False}

Apply any style_notes from the spec exactly as instructed.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXECUTION STEPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Parse the chart spec from the input.
2. Generate complete, self-contained Python code that:
   a. Imports all libraries at the top
   b. Defines data inline as a list of dicts or pandas DataFrame
   c. Builds the chart with all styling standards applied
   d. Saves to "chart.png":
        Plotly    : fig.write_image("chart.png", width=1200, height=700, scale=2)
        Matplotlib: plt.savefig("chart.png", dpi=150, bbox_inches="tight")
   e. Prints "CHART_SAVED" after saving successfully
3. Execute the code using the code execution tool.
4. If execution fails, attempt ONE fix and retry.
   If the retry also fails, go to step 5 with failure.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL — FINAL RESPONSE REQUIRED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
After code execution completes (success or failure), you MUST output a final
plain text message as your last action. This is required — do not end your
turn after a code execution block.

On SUCCESS (code ran and printed "CHART_SAVED"):
  Output exactly:
  STATUS:success MESSAGE:Chart generated successfully.

On FAILURE (code errored or did not print "CHART_SAVED"):
  Output exactly:
  STATUS:failure REASON:<brief plain-language explanation>
"""

# ── Code Executor ────────────────────────────────────────────────────────────
# Use VertexAiCodeExecutor when deployed on Agent Engine (CODE_INTERPRETER_EXTENSION_NAME set).
# Fall back to BuiltInCodeExecutor for local development.
if _CODE_INTERPRETER_RESOURCE:
    from google.adk.code_executors import VertexAiCodeExecutor
    _code_executor = VertexAiCodeExecutor(
        resource_name=_CODE_INTERPRETER_RESOURCE,
        stateful=True,
    )
else:
    from google.adk.code_executors import BuiltInCodeExecutor
    _code_executor = BuiltInCodeExecutor()

# ── Agent ─────────────────────────────────────────────────────────────────────
chart_agent = LlmAgent(
    name="chart_agent",
    model=_CHART_AGENT_MODEL,
    instruction=_PROMPT,
    description=(
        "Generates and executes Python charting code from a fully-specified "
        "chart request. Returns STATUS:success or STATUS:failure as plain text. "
        "Only call this after the user has confirmed they want a chart."
    ),
    code_executor=_code_executor,
)