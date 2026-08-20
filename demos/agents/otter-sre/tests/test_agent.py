"""The agent loop emits the spans it is supposed to emit.

Runs against a stubbed Anthropic client and an in-memory exporter, so it needs no
API key, no collector and no network. What it guards is that every tool call produces
a tool span carrying the call's arguments and its result -- as
`gen_ai.tool.call.arguments` and `gen_ai.tool.call.result`, the opt-in content this
loop writes deliberately.

The loop itself is instrumentation-agnostic: it writes these spans by hand, and the
library only instruments the model call. If the loop changed with the library, a
difference in the telemetry could not be attributed to the vocabulary, and the
comparison with ../beaver-sre would prove nothing.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from traceloop.sdk import Traceloop
from traceloop.sdk.instruments import Instruments

# One SDK for the module: see the `spans` fixture for why it cannot be per-test.
_EXPORTER = InMemorySpanExporter()
Traceloop.init(
    app_name="test",
    exporter=_EXPORTER,
    disable_batch=True,
    telemetry_enabled=False,
    block_instruments={Instruments.MCP},
)


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
    """An in-memory exporter plus a tracer, returned as (tracer, get_finished_spans).

    Traceloop owns the provider here, because the loop's spans come from its @agent and
    @tool decorators and those resolve the tracer from the global provider rather than
    from anything we hand them. Traceloop.init(exporter=...) is the documented way to
    point it at ours; disable_batch so a span is exported the moment it ends.

    Initialised once for the whole module, and the exporter cleared per test. Traceloop
    keeps one global SDK, so a second init() does not rebind the exporter -- every test
    after the first would assert against spans that went somewhere else, which reads as
    "the loop emitted nothing".
    """
    _EXPORTER.clear()
    from opentelemetry import trace
    return trace.get_tracer("test"), _EXPORTER.get_finished_spans


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
    # Traceloop's decorators name the spans, not us: "<entity>.agent" and "<entity>.tool".
    assert "db-ops-agent.agent" in by_name
    assert "query.tool" in by_name
    assert "delete_records.tool" in by_name

    root = by_name["db-ops-agent.agent"]
    assert root.attributes["traceloop.span.kind"] == "agent"
    assert root.attributes["gen_ai.agent.name"] == "db-ops-agent"

    delete = by_name["delete_records.tool"]
    assert delete.attributes["traceloop.span.kind"] == "tool"
    assert delete.attributes["gen_ai.tool.name"] == "delete_records"
    # The content IS recorded -- in Traceloop's namespace, not the convention's. This is
    # the finding, so it is pinned rather than merely observed: if a release moves it to
    # gen_ai.tool.call.*, this test fails and the talk needs re-measuring.
    assert '"plan": "free"' in delete.attributes["traceloop.entity.input"]
    assert '"deleted": 3' in delete.attributes["traceloop.entity.output"]
    assert "gen_ai.tool.call.arguments" not in delete.attributes
    assert "gen_ai.tool.call.result" not in delete.attributes


def test_run_without_tool_calls_still_opens_the_agent_span(spans, monkeypatch):
    tracer, finished = spans
    _stub_anthropic(monkeypatch, [[_Block(type="text", text="Nothing to do.")]])
    from agent import SreAgent

    answer = SreAgent(tracer, model="stub", name="db-ops-agent").run("say hello")

    assert answer == "Nothing to do."
    assert [s.name for s in finished()] == ["db-ops-agent.agent"]


def test_the_decorators_name_the_tool_but_not_its_content(spans, monkeypatch):
    """OpenLLMetry converged on gen_ai.* for the model call, and not for the loop.

    Its @agent and @tool decorators put the tool's NAME under gen_ai.tool.name and the
    call's arguments and result under traceloop.entity.*. So the one agent in this demo
    that needs no normalizing for its model call still hands the forensic content over in
    a vendor namespace. ../beaver-sre is the counterpart, in OpenInference throughout.
    """
    from agent import SreAgent

    tracer, finished = spans
    _stub_anthropic(monkeypatch, [
        [_Block(type="tool_use", name="list_records", id="t9", input={})],
        [_Block(type="text", text="Two left.")],
    ])

    SreAgent(tracer, model="stub", name="otter-sre").run("what happened?")

    by_name = {s.name: s for s in finished()}
    assert "otter-sre.agent" in by_name
    assert "list_records.tool" in by_name

    agent_span = by_name["otter-sre.agent"]
    assert agent_span.attributes["gen_ai.agent.name"] == "otter-sre"
    assert not any(k.startswith("openinference.") for k in agent_span.attributes)

    tool_span = by_name["list_records.tool"]
    assert tool_span.attributes["gen_ai.tool.name"] == "list_records"
    assert "traceloop.entity.input" in tool_span.attributes
    assert "traceloop.entity.output" in tool_span.attributes
    assert not any(k.startswith("openinference.") for k in tool_span.attributes)
