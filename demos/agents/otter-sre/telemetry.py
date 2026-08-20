"""Telemetry wiring for otter-sre: one library, no choices.

OpenLLMetry (Traceloop) already emits the current gen_ai.* conventions as of 0.62.3,
including the new message shape, so nothing downstream translates this agent. It is the
branch of the fan-out that has already converged.

The Anthropic instrumentation is used directly rather than traceloop-sdk, because that SDK
installs its own exporter and processors, and only the vocabulary is meant to differ
between these two agents.

For the other side of the comparison see ../beaver-sre, which is this agent with
OpenInference instead.

The agent loop in `agent.py` does not import this module's opinions — it asks for a tracer
and writes its own spans. What this file decides is who instruments the Anthropic SDK.
"""
from __future__ import annotations

import os

from opentelemetry import trace

# Reported by the service and the CLI, and shown in the capybara-sre console. A
# constant now rather than a lookup: this agent has exactly one answer.
CONVENTION = "openllmetry"

TRACER_NAME = "your-agent-did-what.otter-sre"


def endpoint() -> str:
    """The OTLP/HTTP collector endpoint."""
    return os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")


def configure(agent_name: str) -> trace.Tracer:
    """Install OpenLLMetry on the Anthropic SDK, and return the tracer for hand-written spans."""
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    from opentelemetry.instrumentation.anthropic import AnthropicInstrumentor

    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: agent_name}))
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint()}/v1/traces"))
    )
    trace.set_tracer_provider(provider)

    # The SDK's own HTTP calls, which mirrors what the Java agent shows. This does NOT cover
    # the MCP client: mcp 2.x talks httpx2 and ships its own instrumentation. See mcp_db.py.
    HTTPXClientInstrumentor().instrument(tracer_provider=provider)
    AnthropicInstrumentor().instrument(tracer_provider=provider)

    return trace.get_tracer(TRACER_NAME)


def shutdown() -> None:
    """Flush pending spans. Batch processors drop them otherwise on a short CLI run."""
    provider = trace.get_tracer_provider()
    if hasattr(provider, "shutdown"):
        provider.shutdown()
