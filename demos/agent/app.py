"""Minimal tool-calling Claude agent, instrumented with OpenTelemetry GenAI semconv.

- OpenLIT auto-instruments the Anthropic SDK -> emits `chat` spans (OTel GenAI semconv).
- We hand-write `execute_tool` spans for each tool call, per the GenAI agent spans spec.
  The forensic content (gen_ai.tool.call.arguments / .result) is OPT-IN / off by default
  in the spec; we deliberately enable it here — that is the whole point of the demo.

Run via run.sh after the collector is up. Reads ANTHROPIC_API_KEY from the env.
"""

import json
import os
import sys

import anthropic
import openlit
from opentelemetry import trace
from opentelemetry.trace import SpanKind

import tools

MODEL = os.environ.get("DEMO_MODEL", "claude-sonnet-4-20250514")
OTLP_ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
AGENT_NAME = "db-ops-agent"

# One line of auto-instrumentation: wraps anthropic.messages.create with GenAI semconv spans.
openlit.init(otlp_endpoint=OTLP_ENDPOINT, application_name=AGENT_NAME, environment="demo")

tracer = trace.get_tracer("your-agent-did-what.demo-agent")
client = anthropic.Anthropic()


def _run_tool(block):
    """Execute one tool_use block inside a manual execute_tool span; return a tool_result block."""
    name = block.name
    args = dict(block.input or {})
    with tracer.start_as_current_span(f"execute_tool {name}", kind=SpanKind.INTERNAL) as span:
        span.set_attribute("gen_ai.operation.name", "execute_tool")
        span.set_attribute("gen_ai.tool.name", name)
        span.set_attribute("gen_ai.tool.call.id", block.id)
        span.set_attribute("gen_ai.tool.type", "function")
        # OPT-IN forensic content (off by default in the spec):
        span.set_attribute("gen_ai.tool.call.arguments", json.dumps(args))
        result = tools.dispatch(name)(**args)
        span.set_attribute("gen_ai.tool.call.result", json.dumps(result))
    return {"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result)}


def run_agent(prompt, max_turns=6):
    """Run the agent on a single prompt until it stops calling tools."""
    messages = [{"role": "user", "content": prompt}]
    with tracer.start_as_current_span(f"invoke_agent {AGENT_NAME}", kind=SpanKind.INTERNAL) as span:
        span.set_attribute("gen_ai.operation.name", "invoke_agent")
        span.set_attribute("gen_ai.agent.name", AGENT_NAME)
        for _ in range(max_turns):
            resp = client.messages.create(
                model=MODEL,
                max_tokens=1024,
                tools=tools.TOOL_SCHEMAS,
                messages=messages,
            )
            messages.append({"role": "assistant", "content": resp.content})
            tool_uses = [b for b in resp.content if getattr(b, "type", None) == "tool_use"]
            if not tool_uses:
                texts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
                return "\n".join(texts)
            messages.append({"role": "user", "content": [_run_tool(b) for b in tool_uses]})
        return "(max turns reached)"


if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:]) or "List all the records in the database."
    print(f"\n>>> {prompt}\n")
    print(run_agent(prompt))
