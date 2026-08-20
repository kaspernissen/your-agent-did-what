"""Telemetry wiring for beaver-sre: one library, no choices.

OpenInference does not speak the OpenTelemetry names. It emits llm.* and
openinference.* for the model call, and the collector's gen_ai_normalizer rewrites those
into gen_ai.* as the spans pass through — keeping the originals, so one span carries both
vocabularies at once. That is the only way to see that the translation is partial.

For the other side of the comparison see ../otter-sre, which is this agent with
OpenLLMetry instead. Nothing else about the two differs.

Two things are installed here, and they cover different ground:

  AnthropicInstrumentor  patches the SDK, so the model call is traced without the agent
                         loop knowing. This is the part that needs no code.
  OITracer               OpenInference's own tracing helper, handed to agent.py for the
                         spans no library can produce — see its docstring for why.

The tracer is an OITracer rather than a plain OTel one because the provider is
OpenInference's. That is the documented setup outside Phoenix's `register()` helper: use
their TracerProvider, and every tracer it hands out understands openinference_span_kind
and the set_input / set_output / set_tool helpers.
"""
from __future__ import annotations

import os

from opentelemetry import trace

# Reported by the service and the CLI, and shown in the capybara-sre console. A
# constant now rather than a lookup: this agent has exactly one answer.
CONVENTION = "openinference"

TRACER_NAME = "your-agent-did-what.beaver-sre"


def endpoint() -> str:
    """The OTLP/HTTP collector endpoint."""
    return os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")


def configure(agent_name: str):
    """Install OpenInference on the Anthropic SDK, and return its tracer for our own spans."""
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    # OpenInference's TracerProvider subclasses the SDK's, so it is used in place of it
    # rather than wrapped around it. Wrapping looks like it should work and fails at the
    # first span with 'TracerProvider' object has no attribute 'should_sample'.
    from openinference.instrumentation import TracerProvider
    from openinference.instrumentation.anthropic import AnthropicInstrumentor

    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: agent_name}))
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint()}/v1/traces"))
    )
    trace.set_tracer_provider(provider)

    # The SDK's own HTTP calls, which mirrors what the Java agent shows. This does NOT cover
    # the MCP client: mcp 2.x talks httpx2 and ships its own instrumentation. See mcp_db.py.
    HTTPXClientInstrumentor().instrument(tracer_provider=provider)
    AnthropicInstrumentor().instrument(tracer_provider=provider)

    return provider.get_tracer(TRACER_NAME)


def shutdown() -> None:
    """Flush pending spans. Batch processors drop them otherwise on a short CLI run."""
    provider = trace.get_tracer_provider()
    if hasattr(provider, "shutdown"):
        provider.shutdown()
