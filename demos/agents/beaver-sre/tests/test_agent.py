"""The agent loop emits the spans it is supposed to emit.

Runs against a stubbed Anthropic client and an in-memory exporter, so it needs no
API key, no collector and no network. What it guards is that every tool call produces
a tool span carrying the call's arguments and its result -- in OpenInference's
names (`tool_call.function.arguments`, `input.value`, `output.value`), because that is
this agent's vocabulary and what the collector is given to normalize.

The loop itself is instrumentation-agnostic: it writes these spans by hand, and the
library only instruments the model call. If the loop changed with the library, a
difference in the telemetry could not be attributed to the vocabulary, and the
comparison with ../otter-sre would prove nothing.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# OpenInference's provider, not the SDK's: it is what hands out an OITracer, and the loop
# now asks that tracer for openinference_span_kind and set_input / set_output / set_tool.
from openinference.instrumentation import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


class _Block:
    """Stands in for an Anthropic content block."""

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def _stub_anthropic(monkeypatch, turns):
    """Install a fake `anthropic` that replays `turns`, one content list per create().

    Also rebinds the reference in `agent`, which imported the real module at import
    time — patching sys.modules alone would leave the previous stub in place and the
    second test would replay the first test's turns.
    """
    remaining = list(turns)

    class _Messages:
        def create(self, **_kwargs):
            return _Block(content=remaining.pop(0))

    class _Anthropic:
        def __init__(self, *_a, **_kw):
            self.messages = _Messages()

    stub = types.SimpleNamespace(Anthropic=_Anthropic)
    monkeypatch.setitem(sys.modules, "anthropic", stub)
    import agent as agent_module

    monkeypatch.setattr(agent_module, "anthropic", stub, raising=False)


@pytest.fixture
def spans(monkeypatch):
    """An in-memory exporter plus a tracer, returned as (tracer, get_finished_spans)."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider.get_tracer("test"), exporter.get_finished_spans


@pytest.fixture(autouse=True)
def fresh_database():
    """Each test starts from the full roster, before anything has been deleted."""
    import db
    import tools

    tools.use(db.InMemoryDatabase(staged=False))
    yield


def test_destructive_run_emits_forensic_content(spans, monkeypatch):
    tracer, finished = spans
    _stub_anthropic(monkeypatch, [
        [_Block(type="tool_use", name="query", id="t1", input={"plan": "free"})],
        [_Block(type="tool_use", name="delete_records", id="t2", input={"plan": "free"})],
        [_Block(type="text", text="Deleted the two free-plan customers.")],
    ])
    import tools
    from agent import SreAgent

    answer = SreAgent(tracer, model="stub", name="db-ops-agent").run("delete the free plan")

    assert "Deleted" in answer
    # deleting the free plan leaves the pro customers, whoever they are
    assert [r["user"] for r in tools.list_records()] == ["cappuccino", "mochi"]

    by_name = {s.name: s for s in finished()}
    # Span names are framework-flavoured under OpenInference: the operation is an attribute.
    assert "db-ops-agent" in by_name
    assert "query" in by_name
    assert "delete_records" in by_name

    root = by_name["db-ops-agent"]
    assert root.attributes["openinference.span.kind"] == "AGENT"
    assert root.attributes["input.value"] == "delete the free plan"
    assert "Deleted" in root.attributes["output.value"]

    delete = by_name["delete_records"]
    assert delete.attributes["openinference.span.kind"] == "TOOL"
    assert delete.attributes["tool.name"] == "delete_records"
    # set_tool carries the schema the model was shown, which the hand-written version never
    # bothered to record.
    assert "Destructive" in delete.attributes["tool.description"]
    assert '"plan"' in delete.attributes["tool.parameters"]
    # The content the conventions make opt-in. This loop records it explicitly, so unlike a
    # framework-instrumented path it must always be present.
    assert delete.attributes["input.value"] == '{"plan": "free"}'
    assert delete.attributes["tool_call.function.arguments"] == '{"plan": "free"}'
    assert '"deleted": 3' in delete.attributes["output.value"]


def test_run_without_tool_calls_still_opens_the_agent_span(spans, monkeypatch):
    tracer, finished = spans
    _stub_anthropic(monkeypatch, [[_Block(type="text", text="Nothing to do.")]])
    from agent import SreAgent

    answer = SreAgent(tracer, model="stub", name="db-ops-agent").run("say hello")

    assert answer == "Nothing to do."
    assert [s.name for s in finished()] == ["db-ops-agent"]


def test_openinference_vocabulary_emits_the_source_convention(spans, monkeypatch):
    """Under OpenInference the loop must emit OpenInference keys, not gen_ai.* ones.

    This is what makes the collector's normalization demonstrable rather than assumed: if
    these spans already arrived in OTel vocabulary, gen_ai_normalizer would have nothing
    to do and the demo would prove nothing.

    The exact strings matter — the processor matches on them, so a near-miss is a span it
    silently ignores.
    """
    from agent import SreAgent

    tracer, finished = spans
    _stub_anthropic(monkeypatch, [
        [_Block(type="tool_use", name="list_records", id="t9", input={})],
        [_Block(type="text", text="Two left.")],
    ])

    SreAgent(tracer, model="stub", name="beaver-sre").run("what happened?")

    by_name = {s.name: s for s in finished()}
    # Span names stay framework-flavoured; the operation is an attribute, not the name.
    assert "beaver-sre" in by_name
    assert "list_records" in by_name

    agent_span = by_name["beaver-sre"]
    assert agent_span.attributes["openinference.span.kind"] == "AGENT"
    assert not any(k.startswith("gen_ai.") for k in agent_span.attributes)

    tool_span = by_name["list_records"]
    assert tool_span.attributes["openinference.span.kind"] == "TOOL"
    assert tool_span.attributes["tool.name"] == "list_records"
    assert tool_span.attributes["tool_call.id"] == "t9"
    assert "tool_call.function.arguments" in tool_span.attributes
    assert "output.value" in tool_span.attributes
    assert not any(k.startswith("gen_ai.") for k in tool_span.attributes)
