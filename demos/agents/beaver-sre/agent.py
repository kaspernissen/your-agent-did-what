"""The agent loop: ask the model, run the tools it asks for, repeat until it stops.

Two responsibilities and no more — drive the conversation, and describe what happened in
spans. It does not install instrumentation (see `telemetry.py`) and it does not know what
the tools do (see `tools.py`).

The agent and tool spans are written by hand, because nothing auto-instruments a loop
somebody wrote themselves. The names they are written in are OpenInference's, so the whole trace leaves here in one
vocabulary and the collector's gen_ai_normalizer is what produces OTel semantics. Writing
gen_ai.* here by hand would prove nothing about the collector, which is the point of
having this agent at all.

The tool call's arguments and its result are both recorded. The conventions define them as
opt-in — the spec says instrumentation SHOULD NOT capture them by default, for privacy and
payload size — so nothing emits them unless somebody decides to. Deciding to is the
difference between a trace that proves a tool ran and one that proves what it did.

../otter-sre is this same loop with OpenLLMetry instead, writing gen_ai.* directly.
The two directories are deliberately separate copies: each one is meant to be readable
end to end as an example of instrumenting an agent under one convention.
"""
from __future__ import annotations

import json
import os

import anthropic
from opentelemetry.trace import SpanKind, Tracer

import tools

DEFAULT_MODEL = "claude-sonnet-5"
DEFAULT_AGENT_NAME = "db-ops-agent"
MAX_TURNS = 6

# OpenInference keys, exactly as upstream spells them: the collector's
# gen_ai_normalizer matches on these literal strings and silently ignores a near-miss.
# Span names stay framework-flavoured, which is what these libraries actually do — the
# operation is an attribute, not the span name.


class SreAgent:
    """A tool-calling Claude agent over the customer database."""

    def __init__(self, tracer: Tracer, *, model: str | None = None, name: str | None = None):
        self._tracer = tracer
        self._model = model or os.environ.get("DEMO_MODEL", DEFAULT_MODEL)
        self._name = name or DEFAULT_AGENT_NAME
        self._client = anthropic.Anthropic()
        # What the run just executed, for callers that want to show it. One agent per
        # run, so this needs no locking — the HTTP service builds a fresh one per
        # request rather than sharing one across concurrent calls.
        self._trace_id: str | None = None
        self._tool_calls: list[dict] = []

    @property
    def model(self) -> str:
        return self._model

    @property
    def name(self) -> str:
        return self._name

    @property
    def trace_id(self) -> str | None:
        """The trace this run belongs to, hex, for deep-linking into a trace viewer."""
        return self._trace_id

    @property
    def tool_calls(self) -> list[dict]:
        """Every tool call of the run, with its arguments and result."""
        return list(self._tool_calls)

    def run(self, prompt: str, max_turns: int = MAX_TURNS) -> str:
        """Run one incident to completion and return the agent's final text."""
        messages = [{"role": "user", "content": prompt}]
        self._tool_calls = []
        with self._tracer.start_as_current_span(
            self._name, kind=SpanKind.INTERNAL
        ) as span:
            span.set_attribute("openinference.span.kind", "AGENT")
            span.set_attribute("agent.name", self._name)
            self._trace_id = format(span.get_span_context().trace_id, "032x")
            for _ in range(max_turns):
                response = self._client.messages.create(
                    model=self._model,
                    max_tokens=1024,
                    tools=tools.TOOL_SCHEMAS,
                    messages=messages,
                )
                messages.append({"role": "assistant", "content": response.content})
                requested = [b for b in response.content if getattr(b, "type", None) == "tool_use"]
                if not requested:
                    return self._text_of(response)
                messages.append(
                    {"role": "user", "content": [self._execute(b) for b in requested]}
                )
            return "(max turns reached)"

    def _execute(self, block) -> dict:
        """Run one tool_use block inside a hand-written tool span; return its tool_result.

        The span is named for the tool, not "execute_tool <tool>": under OpenInference the
        operation is an attribute, not the span name. Worth knowing while reading a trace,
        because there IS an `execute_tool` span a few rows below this one -- it belongs to
        sre-agents-mcp, which is a different service in a different process.
        """
        name = block.name
        arguments = dict(block.input or {})
        arguments_json = json.dumps(arguments)
        with self._tracer.start_as_current_span(
            name, kind=SpanKind.INTERNAL
        ) as span:
            span.set_attribute("openinference.span.kind", "TOOL")
            span.set_attribute("tool.name", name)
            span.set_attribute("tool_call.id", block.id)
            span.set_attribute("tool_call.function.arguments", arguments_json)
            span.set_attribute("input.value", arguments_json)
            result = tools.dispatch(name)(**arguments)
            result_json = json.dumps(result)
            span.set_attribute("output.value", result_json)
            self._tool_calls.append({"name": name, "args": arguments, "result": result})
        return {
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": result_json,
        }

    @staticmethod
    def _text_of(response) -> str:
        """The assistant's text blocks, joined."""
        return "\n".join(
            b.text for b in response.content if getattr(b, "type", None) == "text"
        )
