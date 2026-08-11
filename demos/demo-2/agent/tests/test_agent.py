"""The agent loop emits the spans the talk claims it emits.

Runs against a stubbed Anthropic client and an in-memory exporter, so it needs no
API key, no collector and no network. What it guards is the thing beats 4 and 6
rest on: that every tool call produces an `execute_tool` span carrying
`gen_ai.tool.call.arguments` and `gen_ai.tool.call.result`.

The loop is instrumentation-agnostic by design, so these assertions hold for every
value of CAPYBARA_INSTRUMENTATION — that is precisely why beat 5 can attribute the
difference between two runs to the convention alone.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from opentelemetry.sdk.trace import TracerProvider
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
    """Each test starts from the seed, since the database is module state."""
    import tools

    tools._RECORDS = [dict(r) for r in tools._SEED]
    yield


def test_destructive_run_emits_forensic_content(spans, monkeypatch):
    tracer, finished = spans
    _stub_anthropic(monkeypatch, [
        [_Block(type="tool_use", name="query", id="t1", input={"plan": "free"})],
        [_Block(type="tool_use", name="delete_records", id="t2", input={"plan": "free"})],
        [_Block(type="text", text="Deleted the two free-plan capybaras.")],
    ])
    import tools
    from agent import CapybaraAgent

    answer = CapybaraAgent(tracer, model="stub", name="db-ops-agent").run("delete the free plan")

    assert "Deleted" in answer
    # deleting the free plan leaves the pro capybaras, whoever they are
    assert [r["user"] for r in tools.list_records()] == ["cappuccino", "mochi"]

    by_name = {s.name: s for s in finished()}
    assert "invoke_agent db-ops-agent" in by_name
    assert "execute_tool query" in by_name
    assert "execute_tool delete_records" in by_name

    root = by_name["invoke_agent db-ops-agent"]
    assert root.attributes["gen_ai.operation.name"] == "invoke_agent"
    assert root.attributes["gen_ai.agent.name"] == "db-ops-agent"

    delete = by_name["execute_tool delete_records"]
    assert delete.attributes["gen_ai.operation.name"] == "execute_tool"
    assert delete.attributes["gen_ai.tool.name"] == "delete_records"
    # The opt-in content. Its absence is the finding on Demo 1's MCP path; here we
    # write it ourselves, so it must be present.
    assert delete.attributes["gen_ai.tool.call.arguments"] == '{"plan": "free"}'
    assert '"deleted": 3' in delete.attributes["gen_ai.tool.call.result"]


def test_run_without_tool_calls_still_opens_the_agent_span(spans, monkeypatch):
    tracer, finished = spans
    _stub_anthropic(monkeypatch, [[_Block(type="text", text="Nothing to do.")]])
    from agent import CapybaraAgent

    answer = CapybaraAgent(tracer, model="stub", name="db-ops-agent").run("say hello")

    assert answer == "Nothing to do."
    assert [s.name for s in finished()] == ["invoke_agent db-ops-agent"]
