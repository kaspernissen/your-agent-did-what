"""The agent loop: ask the model, run the tools it asks for, repeat until it stops.

Two responsibilities and no more — drive the conversation, and describe what happened in
spans. It does not install instrumentation (see `telemetry.py`) and it does not know what
the tools do (see `tools.py`).

The agent and tool spans come from OpenInference's own tracing helpers, because nothing
auto-instruments a loop somebody wrote themselves — a library can patch `messages.create`,
but it cannot see a `for` loop in a file nobody shipped. What it can do is hand you an API
for describing the loop yourself, and this uses it rather than setting attribute strings
by hand: `openinference_span_kind` and the set_input / set_output / set_tool helpers, which
is the documented manual-instrumentation path.

That is worth more than saving keystrokes. The library owns the attribute names, so a
rename upstream cannot leave this file emitting keys the collector's gen_ai_normalizer no
longer matches — and set_tool records the description and JSON schema the model was shown,
which no amount of hand-writing was going to bother with.

Everything still arrives in OpenInference's vocabulary, so gen_ai_normalizer is what
produces OTel semantics. Writing gen_ai.* here by hand would prove nothing about the
collector, which is the point of having this agent at all.

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
from openinference.semconv.trace import ToolCallAttributes
from opentelemetry.trace import Status, StatusCode

import tools

DEFAULT_MODEL = "claude-sonnet-5"
DEFAULT_AGENT_NAME = "db-ops-agent"
MAX_TURNS = 6

# Span names stay framework-flavoured, which is what these libraries actually do — the
# operation is an attribute (openinference.span.kind), not the span name.


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
        """Run one incident to completion and return the agent's final text."""
        messages = [{"role": "user", "content": prompt}]
        self._tool_calls = []
        with self._tracer.start_as_current_span(
            self._name, openinference_span_kind="agent"
        ) as span:
            span.set_input(prompt)
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
                    answer = self._text_of(response)
                    span.set_output(answer)
                    span.set_status(Status(StatusCode.OK))
                    return answer
                messages.append(
                    {"role": "user", "content": [self._execute(b) for b in requested]}
                )
            span.set_output("(max turns reached)")
            span.set_status(Status(StatusCode.OK))
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
        schema = tools.schema_for(name)
        with self._tracer.start_as_current_span(
            name, openinference_span_kind="tool"
        ) as span:
            # The description and parameters the model was actually shown, not a guess from
            # the Python signature. set_tool writes tool.name, tool.description and
            # tool.parameters; the library owns those keys, so we cannot misspell them.
            span.set_tool(
                name=name,
                description=schema["description"],
                parameters=schema["input_schema"],
            )
            span.set_input(arguments)
            # Not something set_tool covers: the id ties this span to the specific request
            # the model made, and it only exists at runtime. The constant is upstream's.
            span.set_attribute(ToolCallAttributes.TOOL_CALL_ID, block.id)
            span.set_attribute(
                ToolCallAttributes.TOOL_CALL_FUNCTION_ARGUMENTS_JSON, json.dumps(arguments)
            )
            result = tools.dispatch(name)(**arguments)
            result_json = json.dumps(result)
            span.set_output(result)
            span.set_status(Status(StatusCode.OK))
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
