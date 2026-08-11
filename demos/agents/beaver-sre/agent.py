"""The agent loop: ask the model, run the tools it asks for, repeat until it stops.

Two responsibilities and no more — drive the conversation, and describe what
happened in OpenTelemetry GenAI spans. It does not choose an instrumentation
library (see `telemetry.py`) and it does not know what the tools do (see
`tools.py`).

The agent and tool spans are hand-written, because nothing auto-instruments a loop
somebody wrote by hand. But this module does not choose their *vocabulary*: it asks a
Vocabulary object from `telemetry.py` to name them. Under OpenInference that means the
whole trace leaves here in OpenInference vocabulary and the collector's
gen_ai_normalizer is what produces OTel semantics — which is the thing the demo is
supposed to show. Writing gen_ai.* here by hand would prove nothing about the
collector.

Either way the tool call's arguments and result are recorded. The conventions define
them as opt-in — the spec says instrumentation SHOULD NOT capture them by default, for
privacy and payload size — so nothing emits them unless somebody decides to. Deciding
to is the difference between a trace that proves a tool ran and one that proves what it
did, which is the argument of beats 4 and 6.
"""
from __future__ import annotations

import json
import os

import anthropic
from opentelemetry.trace import SpanKind, Tracer

import telemetry
import tools

DEFAULT_MODEL = "claude-sonnet-5"
DEFAULT_AGENT_NAME = "db-ops-agent"
MAX_TURNS = 6


class CapybaraAgent:
    """A tool-calling Claude agent over the capybara customer database."""

    def __init__(self, tracer: Tracer, *, model: str | None = None, name: str | None = None,
                 vocabulary=None):
        self._tracer = tracer
        # Defaults to OTel vocabulary so a caller that does not care -- a test, mostly --
        # gets gen_ai.* rather than silently emitting a vocabulary nobody translates.
        self._vocab = vocabulary or telemetry.GenAIVocabulary()
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
            self._vocab.agent_span_name(self._name), kind=SpanKind.INTERNAL
        ) as span:
            self._vocab.annotate_agent(span, self._name)
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
        """Run one tool_use block inside an execute_tool span; return its tool_result."""
        name = block.name
        arguments = dict(block.input or {})
        with self._tracer.start_as_current_span(
            self._vocab.tool_span_name(name), kind=SpanKind.INTERNAL
        ) as span:
            self._vocab.annotate_tool_call(span, name, block.id, json.dumps(arguments))
            result = tools.dispatch(name)(**arguments)
            self._vocab.annotate_tool_result(span, json.dumps(result))
            self._tool_calls.append({"name": name, "args": arguments, "result": result})
        return {
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": json.dumps(result),
        }

    @staticmethod
    def _text_of(response) -> str:
        """The assistant's text blocks, joined."""
        return "\n".join(
            b.text for b in response.content if getattr(b, "type", None) == "text"
        )
