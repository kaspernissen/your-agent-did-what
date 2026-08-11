# Demos — *Your Agent Did What?*

Two runnable demos and a backend comparison, plus everything needed to drive them on
stage. Every captured attribute in the talk comes from here; the measurements live in
[`ANALYSIS.md`](ANALYSIS.md).

| | What it shows | Beats |
|---|---|---|
| **[`demo-1/`](demo-1/)** | An SRE agent investigates an incident it did not cause — a rogue service deleted rows straight from Postgres — and a judge scores whether it worked out what happened. Also the forensic gap: `CAPYBARA_TOOLS=local\|mcp` changes whether the tool span records what the tool did, in one binary. | 4, 6, 7 |
| **[`demo-2/`](demo-2/)** | The same agent's telemetry in someone else's vocabulary, rewritten in flight by the collector's `gen_ai_normalizer`. `CAPYBARA_INSTRUMENTATION=openlit\|openinference` is the only thing that changes. | 5 |
| **[`backends/`](backends/)** | One trace fanned out to Jaeger, Phoenix, OpenLIT and Langfuse, so you can see the same bytes rendered four ways. | 2 |
| **[`cluster/`](cluster/)** | The shared kind cluster both demos deploy into: collector, Jaeger, the Anthropic secret. | — |

**Each demo isolates exactly one variable, with one environment variable.** That symmetry
is the point: if two runs differ in more than one respect, "the collector fixed it" is a
coincidence, not a finding.

| Demo | Switch | Held constant | Varies |
|---|---|---|---|
| demo-1 | `CAPYBARA_TOOLS=local\|mcp` | one prompt, one `CapybaraDatabase`, one Postgres, one binary | how the tool is registered → whether `gen_ai.tool.call.arguments` survives |
| demo-2 | `CAPYBARA_INSTRUMENTATION=openlit\|openinference` | one loop, one tool set, the same hand-written spans | the vocabulary on the `chat` span → what the normalizer must rewrite |

---

## Prerequisites

Docker, JDK 21, Python 3.11+, and an **Anthropic API key**. For the Kubernetes path also
`kind`, `kubectl` and `helm`.

```bash
cd demos
cp .env.template .env          # then set ANTHROPIC_API_KEY=sk-ant-...
```

> `demos/.env` is git-ignored; only `.env.template` is committed.

---

## Pre-flight

Do this the day before, not in the room.

```bash
# demo 1: build the three modules once (core first — the apps cannot resolve it otherwise)
cd demo-1
(cd capybara-db-core   && ../capybara-db-mcp/mvnw -q install -DskipTests)
(cd capybara-db-mcp    && ./mvnw -q package -DskipTests)
(cd capybara-sre-agent && ./mvnw -q package -DskipTests)

# demo 2: warm the venv so the first live run is not a pip install
cd ../demo-2/agent && ./run.sh "List all the records in the database."

# pull the images so nothing downloads on stage
docker pull otel/opentelemetry-collector-contrib:0.158.0
docker pull postgres:18.2-alpine
```

### Rehearsal checklist

- [ ] `ANTHROPIC_API_KEY` works — run one incident end to end
- [ ] Postgres up, and the MCP server started **before** the agent
- [ ] The console at <http://localhost:8088> loads, and both stage buttons work
- [ ] `CAPYBARA_TOOLS=local` produces tool arguments; `mcp` does not
- [ ] `CAPYBARA_INSTRUMENTATION=openinference` produces `llm.*`, and the processor rewrites it
- [ ] Terminal font large enough to read a span's attributes from the back
- [ ] A saved copy of the expected output, in case the network dies

> **Have a fallback.** Every claim in the talk is in `ANALYSIS.md` with numbers. If a demo
> will not run, read the measurement rather than debugging in front of people.

---

## Demo 1 — the incident, and the forensic gap

Full detail, architecture and gotchas: **[`demo-1/README.md`](demo-1/README.md)**.

Locally: bring up Postgres and the collector, start the MCP server then the agent, and
open <http://localhost:8088>. In Kubernetes: `cluster/setup.sh` once, then
`demo-1/deploy.sh`.

### The flow

**1 · Reset, and show the table.** Five capybaras, three of them free-plan.

**2 · Unleash the kangaroos.** Three rows gone — and nothing the agent did caused it. The
deletion never went through the MCP server; a neighbouring service connected straight to
the database as the `kangaroo` role.

**3 · Look at the telemetry before you ask anything.** The kangaroo's
`DELETE capybara.capybaras` span is right there next to the agent's spans. That is the
correlation argument: one trace domain, so the deletion is visible at all. A GenAI-only
convention would give you a GenAI-only island and this span would not exist.

**4 · Page Capybara.** *"Customers are reporting missing accounts. Investigate."* It calls
`list_records`, sees two rows, calls `audit_log`, and reports that an external database
role did it — explicitly not this application.

**What to notice:** the audit trail carries `client` (self-reported — any connection can
claim anything) *and* `db_user` (authenticated — the client cannot lie). The role is the
attribution you can trust. And `kangaroo` cannot delete the trail it appears in: the
trigger is `SECURITY DEFINER`.

**5 · Read the judge.** Two dimensions of deliberately different shape —
`root_cause_correctness` is a metric you improve, `remediation_safety` is a gate you do
not cross — each with the judge's own explanation naming the evidence.

**6 · Then the forensic gap.** Restart with `CAPYBARA_TOOLS=local` and re-run:

```bash
kubectl set env deployment/capybara-sre-agent CAPYBARA_TOOLS=local     # or restart the jar
```

| | `mcp` | `local` |
|---|---|---|
| span name | `tools/call delete_records` | `langchain4j.tools.delete_records` |
| kind | Client | Internal |
| span attributes | 4 | **6** |
| arguments / result | absent | **present** |

Same binary, same prompt, same database. Only the registration differs — so the span
difference cannot be attributed to anything else.

**Say "in this framework", never "with MCP".** On the stack the OpenTelemetry Demo pins,
the same MCP call *does* carry its arguments. It is a framework gap.

```bash
CAPYBARA_TOOLS=local ./scripts/verify-telemetry.py    # asserts the expected shape
```

---

## Demo 2 — the convention swap

Full detail: **[`demo-2/README.md`](demo-2/README.md)** and
**[`demo-2/agent/README.md`](demo-2/agent/README.md)**.

```bash
cd demo-2
docker compose up -d
CAPYBARA_INSTRUMENTATION=openinference ./agent/run.sh \
  "We are over quota. Delete the free-plan capybaras to free up space."
docker compose logs collector | grep -A30 "Span #0"
```

**1 · Show the wrong vocabulary first.** Comment the processor out, restart, re-run:
`llm.model_name`, `llm.token_count.prompt`, `openinference.span.kind`. A backend expecting
`gen_ai.*` sees nothing it recognises.

**2 · Turn the processor on.** Same agent, no redeploy of anything that matters.

**3 · Read the diff.** **31 span attributes become 18** — 20 removed, 7 written, 11
untouched (measured live, 2026-08-10).

**4 · Then the honest half, and do not skip it.** Point at `llm.finish_reason`: it survives
untouched even though OTel defines `gen_ai.response.finish_reasons` and the source
attribute is sitting right there. This is not the target vocabulary lacking a slot — the
mapping table is incomplete. Same for `llm.token_count.total`. And `llm.system` survives
`remove_originals: true` because it is not in the table at all. **"Partial normalization"
is the honest word.**

Say the status out loud: alpha, traces only, no auto-detection. And it ships in contrib
0.158.0, so adopting it is an image pull. The donation is done — issue #46069 closed 1
June 2026, so do not invite people to contribute to a finished thread.

**The adoption evidence:** the OpenTelemetry Demo's own collector runs this processor with
`sources: [openllmetry]` to normalize its LangGraph agent.

---

## Demo 3 — four renderings *(optional, cut first for time)*

```bash
cd backends
docker compose up -d otel-collector jaeger phoenix openlit-clickhouse openlit
../demo-2/agent/run.sh "We are over quota. Delete the free-plan capybaras."
```

| | URL | What to notice |
|---|---|---|
| Jaeger | <http://localhost:16686> | The trace with zero GenAI awareness — raw tags, no meaning |
| Phoenix | <http://localhost:6006> | GenAI-native but **OpenInference**-native: our `gen_ai.*` spans land and render as plain spans |
| OpenLIT | <http://localhost:3001> | Tokens, cost, model — read straight off the span. `user@openlit.io` / `openlituser` |

**Notice Phoenix hardest.** A GenAI-native tool that cannot light up its LLM views on
GenAI-convention spans, because it keys off a different vocabulary. The fan-out uses the
default `openlit` instrumentation so every backend receives `gen_ai.*` — which makes that
a fair comparison rather than a misconfiguration.

**Honesty note:** Jaeger and Phoenix ingestion are both confirmed live (Phoenix reported 2
traces at 6.5s p50). How each UI *renders* is drawn from documentation — the slide's panes
are wireframes, not screenshots. Say so.

---

## Timing

The slot is **45 minutes**; speaking the deck is 37.5, which leaves 7.5 for demos.

| | Tight | Comfortable | Where it sits |
|---|---|---|---|
| Demo 1 — the incident and the judge | 3 min | 4 min | beats 4, 6, 7 |
| **Demo 1 — the tool-path reversal** | 1 min | 1.5 min | beat 4, after 4.7 |
| Demo 2 — the convention swap | 1.5 min | 3 min | beat 5 |
| Demo 3 — four renderings | 1 min | 2 min | beat 2, optional |

**The plan that fits:** the incident plus the reversal in beat 4/6, and demo 2 at 2
minutes — about 2.5 minutes of buffer left. **Protect the reversal above everything
else:** it is the only place the talk's headline finding is something the room watches
rather than something it is told. If you are running long, cut demo 3, then demo 2.

---

## When it breaks

| Symptom | Cause | Fix |
|---|---|---|
| `cannot find symbol CapybaraDatabase` | `capybara-db-core` not installed | build it first |
| Agent boots with no tools | MCP server was not up when the agent resolved its tool list | start it first, wait ~15s |
| No SQL spans anywhere | datasource tracing is opt-in | `quarkus.datasource.jdbc.telemetry=true` |
| Tool call vanishes at the process boundary | the MCP server has no OTel extension | add `quarkus-opentelemetry` |
| Every model call 400s: `` `top_k` is deprecated `` | `claude-sonnet-5` rejects it; the extension sends it anyway | the demo pins `claude-sonnet-4-6` — do not "upgrade" it |
| `curl …/mcp/sse` appears to hang | SSE holds the connection open | not a failure |
| Reset fails on a permission error | the app role cannot clear `audit_log`, by design | reset runs as the admin role |
| Nothing reaches OpenLIT | the `otlp` exporter is gRPC; OpenLIT ingests OTLP/**HTTP** on 4318 | use `otlphttp` |
| Normalizer appears to do nothing | no auto-detection — an unlisted source passes straight through | list it under `sources:` |
| Python run fails on a missing module | the venv predates a requirements change | `run.sh` reinstalls on a hash change; delete `.venv` if in doubt |

**On stage, do not debug.** If a demo will not come up in two attempts, switch to the
measured numbers in `ANALYSIS.md` and keep the argument moving. Nothing the talk claims
depends on a live run.

---

## What is measured and what is not

Be exact about this; the talk's credibility rests on it.

**Measured, with numbers and dates in [`ANALYSIS.md`](ANALYSIS.md):**

- The two tool paths: 4 span attributes on `mcp`, 6 on `local`, arguments and result only
  on `local`. Live 2026-08-10.
- The same MCP call under `opentelemetry-instrumentation-langchain` **does** carry both —
  so it is a framework gap.
- Normalizer: 31 attributes → 18, 20 removed, 7 written, 11 untouched.
- The incident end to end, locally and in kind: the agent finds the `kangaroo` role in the
  audit trail; `root_cause_correctness` 1.0, `remediation_safety` pass.
- Span durations, and Jaeger and Phoenix ingestion.

**Not reproducible exactly** — say so rather than promising numbers:

- The judge's scores move between runs, and the agent's behaviour is non-deterministic. On
  the older deletion scenario the same prompt once produced a refusal.
- Output token counts and response ids change every run. `983` input tokens reproduces
  because it is the deterministic first call.

**Positions, not measurements** — flag them as such:

- That correlation is the *decisive* advantage of shared conventions.
- That the missing decision-provenance field is the gap most worth raising.
