"""Telemetry wiring — the only place that knows which convention we emit.

The agent loop in `agent.py` is deliberately unaware of this module's choices. It
asks for a tracer and writes `gen_ai.*` spans by hand; whether the *model* call is
described in OTel GenAI vocabulary or OpenInference vocabulary is decided here and
nowhere else.

That separation is the point of the demo. Beat 5 of the talk needs two runs whose
only difference is the vocabulary on the chat span, so that the collector's
`gen_ai_normalizer` has exactly one variable to act on. If the two runs also
differed in which spans they produced — as they did when this was two separate
agents — "normalization fixed it" would be unprovable.

    CAPYBARA_INSTRUMENTATION=openlit        (default)  chat spans in gen_ai.*
    CAPYBARA_INSTRUMENTATION=openinference             chat spans in llm.* / openinference.*
    CAPYBARA_INSTRUMENTATION=none                      no auto-instrumentation at all
"""
from __future__ import annotations

import os

from opentelemetry import trace

OPENLIT = "openlit"
OPENINFERENCE = "openinference"
NONE = "none"
CHOICES = (OPENLIT, OPENINFERENCE, NONE)

TRACER_NAME = "your-agent-did-what.capybara-agent"


def selected() -> str:
    """Which instrumentation this run uses, from CAPYBARA_INSTRUMENTATION."""
    value = os.environ.get("CAPYBARA_INSTRUMENTATION", OPENLIT).strip().lower()
    if value not in CHOICES:
        raise SystemExit(
            f"CAPYBARA_INSTRUMENTATION={value!r} is not one of {', '.join(CHOICES)}"
        )
    return value


def endpoint() -> str:
    """The OTLP/HTTP collector endpoint."""
    return os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")


def configure(agent_name: str) -> trace.Tracer:
    """Install the selected instrumentation and return the tracer for hand-written spans."""
    choice = selected()
    if choice == OPENLIT:
        _configure_openlit(agent_name)
    elif choice == OPENINFERENCE:
        _configure_openinference(agent_name)
    else:
        _configure_plain(agent_name)
    return trace.get_tracer(TRACER_NAME)


def _configure_openlit(agent_name: str) -> None:
    """OpenLIT auto-instruments the Anthropic SDK and emits OTel GenAI semconv.

    It also owns provider setup, so we do not build one ourselves here.
    """
    import openlit

    openlit.init(otlp_endpoint=endpoint(), application_name=agent_name, environment="demo")


def _configure_openinference(agent_name: str) -> None:
    """OpenInference instruments the same SDK but emits llm.* / openinference.* instead.

    Unlike OpenLIT it does not configure a provider, so we set one up first.
    """
    from openinference.instrumentation.anthropic import AnthropicInstrumentor

    provider = _provider(agent_name)
    AnthropicInstrumentor().instrument(tracer_provider=provider)


def _configure_plain(agent_name: str) -> None:
    """No auto-instrumentation: only the spans the agent writes by hand.

    Useful for seeing what the framework contributes versus what we do, and for
    running the loop without either library installed.
    """
    _provider(agent_name)


def _provider(agent_name: str):
    """A tracer provider exporting OTLP/HTTP, registered globally."""
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: agent_name}))
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint()}/v1/traces"))
    )
    trace.set_tracer_provider(provider)
    return provider


def shutdown() -> None:
    """Flush pending spans. Batch processors drop them otherwise on a short CLI run."""
    provider = trace.get_tracer_provider()
    if hasattr(provider, "shutdown"):
        provider.shutdown()
