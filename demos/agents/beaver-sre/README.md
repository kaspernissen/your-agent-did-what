# The capybara Python agent

**One tool-calling Claude agent over the capybara customer database, with the
instrumentation library selectable at run time.**

This agent serves two beats of the talk, and it is one codebase on purpose:

| Beat | What it provides | How |
|---|---|---|
| **6** — forensics | `invoke_agent` / `chat` / `execute_tool` spans with the opt-in forensic content actually populated | `CAPYBARA_INSTRUMENTATION=openlit` (default) |
| **5** — normalization | the same run described in OpenInference vocabulary, for the collector to rewrite | `CAPYBARA_INSTRUMENTATION=openinference` |

There used to be two agents, one per convention. They differed in the
instrumentation library *and* in which spans they wrote — the OpenInference one
wrote no tool spans at all — so "the collector normalized it" could not be
attributed to the collector. Now there is one loop and one variable.

---

## Layout

Four files, one responsibility each.

```
tools.py        the capybara database and the Anthropic tool schemas.
                Domain only — knows nothing about telemetry.

telemetry.py    which convention this run emits. The ONLY module that imports
                an instrumentation library, and the only one that has to change
                if you add a third convention.

agent.py        the loop: ask the model, run the tools it asks for, repeat.
                Writes gen_ai.* spans by hand. Instrumentation-agnostic — it
                receives a tracer and never asks where it came from.

app.py          CLI: read the prompt, wire the two together, print the answer.
```

The boundary that matters is between `agent.py` and `telemetry.py`. Because the
loop cannot see which library is installed, the two runs are provably identical
apart from the vocabulary on the `chat` span — which is exactly the claim beat 5
makes.

---

## Run it

```bash
cd demos/agents/beaver-sre
cp ../../.env.template ../../.env   # then set ANTHROPIC_API_KEY

# OTel GenAI semconv — gen_ai.* on every span
./run.sh "Customers are reporting missing accounts. Investigate what happened."

# OpenInference — llm.* / openinference.* on the chat span
CAPYBARA_INSTRUMENTATION=openinference ./run.sh   # the deployed default
```

`run.sh` creates `.venv` on first use, sources `../.env`, and defaults the
collector endpoint to `http://localhost:4318` (OTLP/**HTTP** — not 4317). Bring a
collector up first: `demos/` for the normalizer pipeline, or
`demos/observability/docker-compose.yml` for the multi-backend fan-out.

| variable | default | meaning |
|---|---|---|
| `CAPYBARA_INSTRUMENTATION` | `openlit` | `openlit` · `openinference` · `none` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4318` | OTLP/HTTP base URL |
| `DEMO_MODEL` | `claude-sonnet-5` | any Anthropic model id |
| `ANTHROPIC_API_KEY` | — | required |

`none` installs no auto-instrumentation, so you see only the spans the agent
writes itself. It is the quickest way to show which parts of a trace come from a
library and which come from a decision somebody made.

---

## What it emits

Regardless of the instrumentation, the agent hand-writes:

```
invoke_agent db-ops-agent          gen_ai.operation.name, gen_ai.agent.name
  execute_tool <name>              gen_ai.operation.name, gen_ai.tool.name,
                                   gen_ai.tool.call.id, gen_ai.tool.type,
                                   gen_ai.tool.call.arguments   ← opt-in
                                   gen_ai.tool.call.result      ← opt-in
```

The two `gen_ai.tool.call.*` attributes are opt-in in the spec — instrumentation
SHOULD NOT capture them by default, for privacy and payload size. The agent sets
them deliberately, in `agent.py`. That single decision is the difference between a
trace proving a tool *ran* and one proving *what it did*.

The `chat` span comes from whichever library is selected, and is the only thing
that changes between runs.

---

## Tests

```bash
./.venv/bin/python -m pytest tests/ -q      # after the first run.sh created .venv
```

`tests/test_tools.py` covers the database. `tests/test_agent.py` drives the loop
against a stubbed Anthropic client and an in-memory span exporter, asserting that
every tool call produces an `execute_tool` span carrying the forensic content — no
API key, no collector, no network. That test is the guard on the claim beat 6
makes, so it should fail loudly if anyone removes those two `set_attribute` calls.

---

## Gotchas

- **OTLP/HTTP, port 4318.** Not 4317. Pointing the HTTP exporter at the gRPC port
  loops on connection-refused and delivers nothing.
- **Batch export needs the flush.** `app.py` calls `telemetry.shutdown()` in a
  `finally`; without it a short CLI run can exit before the batch processor
  exports, and the trace silently never arrives.
- **The database is module state.** One run mutates it; the process exits and it
  resets. Tests reset it explicitly via a fixture rather than relying on reload
  ordering.
- **Both instrumentation libraries are installed**, but only the selected one is
  imported — see the local imports in `telemetry.py`. Installing both keeps
  switching to a single environment variable rather than a reinstall.
