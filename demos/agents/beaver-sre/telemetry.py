"""Telemetry wiring — the only place that knows which convention we emit.

The agent loop in `agent.py` is deliberately unaware of this module's choices. It
asks for a tracer and writes `gen_ai.*` spans by hand; whether the *model* call is
described in OTel GenAI vocabulary or OpenInference vocabulary is decided here and
nowhere else.

That separation is what makes two runs comparable: the same loop, the same spans, the
same tool calls, and only the vocabulary differing. Anything else — a second agent, a
different tool path — and a change in the telemetry could no longer be attributed to the
convention.

    CAPYBARA_INSTRUMENTATION=openlit        (default)  chat spans in gen_ai.*
    CAPYBARA_INSTRUMENTATION=openinference             chat spans in llm.* / openinference.*
    CAPYBARA_INSTRUMENTATION=openllmetry               chat spans in OpenLLMetry's names
    CAPYBARA_INSTRUMENTATION=none                      no auto-instrumentation at all

Two of these are sources the collector's gen_ai_normalizer knows about, openinference and
openllmetry, and it keeps the originals rather than deleting them. So a single trace view shows
what the library emitted beside what the collector made of it, which is the only way to see that
the translation is partial.
"""
from __future__ import annotations

import os

from opentelemetry import trace

OPENLIT = "openlit"
OPENINFERENCE = "openinference"
OPENLLMETRY = "openllmetry"
NONE = "none"
CHOICES = (OPENLIT, OPENINFERENCE, OPENLLMETRY, NONE)

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
    elif choice == OPENLLMETRY:
        _configure_openllmetry(agent_name)
    else:
        _configure_plain(agent_name)
    _instrument_http()
    return trace.get_tracer(TRACER_NAME)


def _instrument_http() -> None:
    """Instrument httpx, which is what the Anthropic SDK talks.

    Transport rather than vocabulary, so it runs whichever instrumentation was selected. It
    gives the model call an HTTP child span, the same shape the Java agent shows. It does not
    cover the MCP client: mcp 2.x uses httpx2, and mcp_db.py carries trace context itself
    through MCP's _meta. Missing package is not an error.
    """
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    except ImportError:
        return
    HTTPXClientInstrumentor().instrument()


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


def _configure_openllmetry(agent_name: str) -> None:
    """OpenLLMetry (Traceloop) instruments the same SDK again, with a third set of names.

    Using the Anthropic instrumentation directly rather than traceloop-sdk, because the SDK
    installs its own exporter and processors, and the point here is that only the vocabulary
    changes between runs: same loop, same spans, same provider, same collector.
    """
    from opentelemetry.instrumentation.anthropic import AnthropicInstrumentor

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


class OpenInferenceVocabulary:
    """Describe the agent loop the way an OpenInference-instrumented framework would.

    This is the point of the demo, and hand-writing gen_ai.* here defeated it: if our own
    spans already arrive in OTel vocabulary, the collector has nothing to prove. A
    framework that does not speak OTel GenAI emits *this* — openinference.span.kind,
    tool.name, tool_call.function.arguments — and gen_ai_normalizer is what turns it into
    OTel semantics on the other side.

    Keys are the upstream constants, taken from Arize-ai/openinference's Go semantic
    conventions, because the processor matches on exact strings: a near-miss produces a
    span it silently ignores.

    Span names stay framework-flavoured (the agent's name, the tool's name) rather than
    "invoke_agent x". That is what these libraries actually do, and it makes a point the
    talk already wants to make: the operation name is an attribute, not the span name.
    """

    name = OPENINFERENCE

    def agent_span_name(self, agent: str) -> str:
        return agent

    def tool_span_name(self, tool: str) -> str:
        return tool

    def annotate_agent(self, span, agent_name: str, conversation_id: str | None = None) -> None:
        span.set_attribute("openinference.span.kind", "AGENT")
        span.set_attribute("agent.name", agent_name)
        if conversation_id:
            span.set_attribute("session.id", conversation_id)

    def annotate_tool_call(self, span, tool_name: str, call_id: str, arguments: str) -> None:
        span.set_attribute("openinference.span.kind", "TOOL")
        span.set_attribute("tool.name", tool_name)
        span.set_attribute("tool_call.id", call_id)
        span.set_attribute("tool_call.function.arguments", arguments)
        span.set_attribute("input.value", arguments)

    def annotate_tool_result(self, span, result: str) -> None:
        span.set_attribute("output.value", result)


class GenAIVocabulary:
    """Describe the loop in OTel GenAI vocabulary directly.

    For the runs where nothing else will: with no instrumentation at all, or with a
    library that already emits gen_ai.*. Writing OpenInference keys there would produce a
    trace in a vocabulary nobody in the pipeline is translating.
    """

    name = "otel"

    def agent_span_name(self, agent: str) -> str:
        return f"invoke_agent {agent}"

    def tool_span_name(self, tool: str) -> str:
        return f"execute_tool {tool}"

    def annotate_agent(self, span, agent_name: str, conversation_id: str | None = None) -> None:
        span.set_attribute("gen_ai.operation.name", "invoke_agent")
        span.set_attribute("gen_ai.agent.name", agent_name)
        if conversation_id:
            span.set_attribute("gen_ai.conversation.id", conversation_id)

    def annotate_tool_call(self, span, tool_name: str, call_id: str, arguments: str) -> None:
        span.set_attribute("gen_ai.operation.name", "execute_tool")
        span.set_attribute("gen_ai.tool.name", tool_name)
        span.set_attribute("gen_ai.tool.call.id", call_id)
        span.set_attribute("gen_ai.tool.type", "function")
        # Opt-in forensic content, deliberately enabled. This is the switch.
        span.set_attribute("gen_ai.tool.call.arguments", arguments)

    def annotate_tool_result(self, span, result: str) -> None:
        span.set_attribute("gen_ai.tool.call.result", result)


def vocabulary():
    """The vocabulary the hand-written spans should use, given the library in play.

    It follows the library on purpose. Under OpenInference the whole trace arrives in
    OpenInference vocabulary and the collector normalizes all of it; otherwise there is
    nothing downstream translating, so gen_ai.* is what to write.
    """
    # OpenInference is the one whose agent and tool spans the normalizer also rewrites, so it is
    # the only choice where writing the source vocabulary by hand demonstrates anything.
    # OpenLLMetry's mapping covers the model call, so the hand-written spans stay in gen_ai.*.
    return OpenInferenceVocabulary() if selected() == OPENINFERENCE else GenAIVocabulary()


def shutdown() -> None:
    """Flush pending spans. Batch processors drop them otherwise on a short CLI run."""
    provider = trace.get_tracer_provider()
    if hasattr(provider, "shutdown"):
        provider.shutdown()
