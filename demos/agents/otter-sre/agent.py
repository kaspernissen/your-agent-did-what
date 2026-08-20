"""The agent loop: ask the model, run the tools it asks for, repeat until it stops.

Two responsibilities and no more — drive the conversation, and describe what happened in
spans. It does not install instrumentation (see `telemetry.py`) and it does not know what
the tools do (see `tools.py`).

The agent and tool spans come from OpenLLMetry's own @agent and @tool decorators, because
nothing auto-instruments a loop somebody wrote themselves — a library can patch
`messages.create`, but it cannot see a `for` loop in a file nobody shipped. Traceloop's
answer is a set of decorators, and this uses them rather than setting attribute strings by
hand.

They are applied at dispatch rather than at definition, because `tools.py` is shared
byte-identical with ../beaver-sre and has to stay free of either library. It is the same
decorator, applied where the tool's name is known.

WORTH KNOWING, and the reason this agent is now the interesting one: the decorators do NOT
record the call's content under the convention. The tool's name arrives as gen_ai.tool.name,
but its arguments and result go to traceloop.entity.input and traceloop.entity.output — a
vendor namespace, from the library that has already converged on gen_ai.* for the model
call. Nothing here emits gen_ai.tool.call.arguments or .result at all.

../beaver-sre is this same loop with OpenInference instead, writing llm.* /
openinference.* and relying on the collector to translate. The two directories are
deliberately separate copies: each one is meant to be readable end to end as an example
of instrumenting an agent under one convention.
"""
from __future__ import annotations

import json
import os

import anthropic
from opentelemetry import trace
from traceloop.sdk.decorators import agent as agent_span
from traceloop.sdk.decorators import tool as tool_span

import tools

DEFAULT_MODEL = "claude-sonnet-5"
DEFAULT_AGENT_NAME = "db-ops-agent"
MAX_TURNS = 6

# Span names are the decorators' own: "<name>.agent" and "<name>.tool". Traceloop builds
# them, so they are not ours to choose — which is part of what using the library as
# documented, rather than approximating it, actually means.


class SreAgent:
    """A tool-calling Claude agent over the customer database."""

    def __init__(self, tracer, *, model: str | None = None, name: str | None = None):
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
        """Run one incident to completion and return the agent's final text.

        The @agent decorator is applied here rather than above the method, because its name
        is this agent's own and is only known once the object exists. Same decorator, same
        span; Traceloop records the arguments and the return value as the entity's input
        and output.
        """
        return agent_span(name=self._name)(self._run)(prompt, max_turns)

    def _run(self, prompt: str, max_turns: int) -> str:
        messages = [{"role": "user", "content": prompt}]
        self._tool_calls = []
        self._trace_id = format(
            trace.get_current_span().get_span_context().trace_id, "032x"
        )
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
        """Run one tool_use block inside a Traceloop tool span; return its tool_result.

        The span is named "<tool>.tool" by the decorator, and carries gen_ai.tool.name plus
        the arguments and result under traceloop.entity.input / .output. Note what is not
        there: gen_ai.tool.call.arguments and .result. The library records the content, in
        its own namespace rather than the convention's.
        """
        name = block.name
        arguments = dict(block.input or {})
        result = tool_span(name=name)(tools.dispatch(name))(**arguments)
        result_json = json.dumps(result)
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
