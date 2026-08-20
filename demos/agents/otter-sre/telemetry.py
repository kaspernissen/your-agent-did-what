"""Telemetry wiring for otter-sre: one library, no choices.

OpenLLMetry (Traceloop) already emits the current gen_ai.* conventions as of 0.62.3,
including the new message shape, so nothing downstream translates this agent's model call.
It is the branch of the fan-out that has already converged.

For the other side of the comparison see ../beaver-sre, which is this agent with
OpenInference instead.

This used to install `opentelemetry-instrumentation-anthropic` directly and avoid
traceloop-sdk, on the grounds that the SDK brings its own exporter and processors. It does
— but `Traceloop.init(exporter=...)` is the documented way to hand it yours instead, and
going through the SDK is what makes the rest of the library available: the @agent and
@tool decorators agent.py uses. Direct instrumentation covers the model call and nothing
else, which left the loop hand-written in a way this agent's counterpart no longer is.

Two things worth knowing about what init() does:

  telemetry_enabled=False  stops the SDK reporting anonymous usage to Traceloop. On by
                           default, and not something a demo should do quietly.
  app_name                 becomes the resource's service.name, which is where the agent's
                           identity lives. The decorators' own names are separate — see
                           agent.py.
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


def configure(agent_name: str):
    """Initialise OpenLLMetry against our collector, and return a tracer for our own spans."""
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from traceloop.sdk import Traceloop
    from traceloop.sdk.instruments import Instruments

    # Our exporter, not Traceloop's. Passing one means the SDK's base URL, API key and
    # header settings are ignored entirely, which is what we want: the spans go to the
    # collector in this cluster and nowhere else.
    #
    # MCP is blocked because Traceloop 0.62.3's MCP instrumentor targets an older client:
    # it looks for mcp.client.streamable_http.streamablehttp_client, and mcp 2.x renamed
    # that to streamable_http_client. Left unblocked it logs
    #   "Error initializing MCP instrumentor … most likely due to a circular import"
    # on every start. Nothing is lost by blocking it — the mcp SDK traces itself, which is
    # where the MCP spans in this agent's traces come from. See mcp_db.py.
    Traceloop.init(
        app_name=agent_name,
        exporter=OTLPSpanExporter(endpoint=f"{endpoint()}/v1/traces"),
        disable_batch=False,
        telemetry_enabled=False,
        block_instruments={Instruments.MCP},
    )

    return trace.get_tracer(TRACER_NAME)


def shutdown() -> None:
    """Flush pending spans. Batch processors drop them otherwise on a short CLI run."""
    provider = trace.get_tracer_provider()
    if hasattr(provider, "shutdown"):
        provider.shutdown()
