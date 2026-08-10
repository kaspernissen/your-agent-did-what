# Demos — GenAI Observability Backends

A docker-compose **test harness** for *Your Agent Did What?*. One instrumented
tool-calling Claude agent emits OpenTelemetry GenAI traces to a single Collector,
which **fans the same trace out to every backend** so you can compare how each
one renders it. Each backend is a compose **profile** — start only what you want.

## The demos

Two demos carry the talk, and they share one story — the same capybara incident, the same
three tools, the same seed data (`cappuccino` pro, `biscuit` and `nibbles` free) — told in
two different conventions.

| Demo | What it shows | Beats |
|---|---|---|
| **[`capybara-sre/`](capybara-sre/)** | A Quarkus + LangChain4j agent over an MCP server, emitting `gen_ai.*` natively, plus an LLM-as-judge attaching `gen_ai.evaluation.result` events. **What you get for free, and what the forensic flags don't give you.** | 4, 6, 7 |
| **[`normalizer/`](normalizer/)** | The same incident instrumented with **OpenInference**, rewritten in flight by the collector's `gen_ai_normalizer` processor. **How far normalization gets you, and where it stops.** | 5 |

Each has its own README with architecture, a run path, a stage flow, measured results and
the gotchas found while building it. Start there.

**Also here:**

- **[`agent/`](agent/)** — the Python agent, shared. One loop, with the instrumentation
  library selected by `CAPYBARA_INSTRUMENTATION`. It supplies beat 6's forensic waterfall
  (`openlit`) *and* beat 5's OpenInference input (`openinference`), and it feeds the
  fan-out stack below. See its README for the loop/telemetry split.
- **`arconia/`** — Spring AI convention switching. Not run on stage, but it is the
  measured evidence behind the "three independent stacks already emit `gen_ai.*`" slide,
  so it stays. Its capture is in `ANALYSIS.md`.

## One variable per demo

Both demos isolate exactly one thing, and each does it with a single environment variable.
That symmetry is deliberate: it is the only way a difference in the telemetry can be
attributed to the difference being demonstrated.

| Demo | Switch | Holds constant | Varies |
|---|---|---|---|
| `capybara-sre/` | `CAPYBARA_TOOLS=local\|mcp` | one prompt, one `CapybaraDatabase`, one binary | how the tool is registered → whether `gen_ai.tool.call.arguments` survives |
| `agent/` + `normalizer/` | `CAPYBARA_INSTRUMENTATION=openlit\|openinference` | one loop, one tool set, the same hand-written spans | the vocabulary on the `chat` span → what the normalizer has to rewrite |

## The fan-out stack

`docker-compose.yml` runs one collector fanning the same trace to **Jaeger, Phoenix,
OpenLIT and Langfuse** (plus optional OpenSearch and Dash0). This is what backs the "same
bytes, four renderings" slide.

```bash
cd demos
docker compose up -d otel-collector jaeger phoenix openlit-clickhouse openlit
./agent/run.sh "We are over quota. Delete the free-plan capybaras to free up space."
```

> The fan-out uses the default `CAPYBARA_INSTRUMENTATION=openlit`, so every backend
> receives `gen_ai.*` — which is what makes Phoenix's blandness a fair comparison rather
> than a misconfiguration.

Jaeger <http://localhost:16686> · Phoenix <http://localhost:6006> · OpenLIT
<http://localhost:3001>

> **Gotcha:** OpenLIT ingests OTLP/**HTTP** on 4318, so its exporter must be `otlphttp`.
> Pointing the gRPC `otlp` exporter at 4318 loops on connection-refused and delivers
> nothing — a bug that was in this config until 2026-08-09.

## The three questions this answers

1. **What does the OpenTelemetry project itself give you?**
   The Collector's `debug` exporter (console) and **Jaeger** (a CNCF sibling, a
   generic trace viewer). OTel standardizes how telemetry is *produced and moved*,
   not how it's visualized — it's vendor-neutral by design.
2. **How do you get it to a vendor?**
   One exporter block. Set `DASH0_*` in `.env` and the same trace appears in Dash0.
3. **What OSS solutions exist?**
   **Arize Phoenix**, **Langfuse**, **OpenLIT** — open each and compare the *same* trace.

## Prerequisites

Docker, an `ANTHROPIC_API_KEY` (`sk-ant-…`), Python 3.11+.

```bash
cp .env.template .env   # then set ANTHROPIC_API_KEY
```

## Quick start (everything)

```bash
./00_run.sh             # brings up all backends, runs the agent, prints the UIs
# ... explore the UIs ...
./01_cleanup.sh
```

## Run a focused subset (lighter, better for live demo)

```bash
# Only the project-native view: console + Jaeger
docker compose --profile jaeger up -d
./agent/run.sh "List all the records in the database."

# Add a GenAI-native OSS UI
docker compose --profile jaeger --profile openlit up -d
```

> **Langfuse is heavy** (Postgres + ClickHouse + Redis + MinIO + web + worker).
> Omit `--profile langfuse` for a lighter run.

## What to look at in each UI

| Backend | URL | Login | What it shows |
|---|---|---|---|
| Jaeger | http://localhost:16686 | — | The trace with **zero GenAI awareness** — `chat …`, `execute_tool …`, raw attrs. |
| Phoenix | http://localhost:6006 | — | GenAI-native but **OpenInference-native**: our `gen_ai.*` spans land but render as **plain spans** (no LLM panels). |
| OpenLIT | http://localhost:3001 | `user@openlit.io` / `openlituser` | OTel-semconv-native GenAI dashboards (tokens, cost, models). |
| Langfuse | http://localhost:3000 | `admin@demo.local` / `changeme-12345` | OSS LLM platform; maps `gen_ai.*` into its trace/observation model. |
| Dash0 | your dashboard | — | The vendor path (only if `DASH0_AUTH_TOKEN` is set). |
| OpenSearch Dashboards | http://localhost:5601 | `admin` / `My_password_123!@#` | Trace Analytics via Data Prepper intermediary (opt-in, heavy). |

## OpenSearch — opt-in "Agent Traces" backend

> **WARNING: heavy (~4 GB of images).** Only enable if you have the disk and RAM.

OpenSearch cannot ingest OTLP directly. It needs **Data Prepper** as an
intermediary. The pipeline is:

```
otel-collector ──OTLP/gRPC(21890)──► data-prepper ──► OpenSearch (otel-v1-apm-span-* index) ──► Dashboards (5601)
```

Enable with `--profile opensearch`:

```bash
docker compose --profile jaeger --profile opensearch up -d
./agent/run.sh "List all the records in the database."
# then open http://localhost:5601  (admin / My_password_123!@#)
# navigate to OpenSearch Dashboards → Observability → Trace Analytics
```

**Credentials:** `admin` / `My_password_123!@#`

**Important caveats:**

- The dedicated **"Agent Traces" UI is RFC-stage in open-source OpenSearch** (it
  is live on Amazon OpenSearch Service). On a stable OSS release (2.x) you will
  see spans in **Trace Analytics** but possibly not a dedicated agent-traces view.
- The backend consumes standard OTel `gen_ai.*` semconv, so the **same Demo 1
  instrumentation feeds it unchanged** — no extra code required.
- Data Prepper writes to the `otel-v1-apm-span-*` index pattern. The
  `trace-analytics-raw` index type in the pipeline config maps directly to this.

### Why Phoenix looks "bland"

Phoenix keys its rich LLM UI off **OpenInference** attributes, not OTel GenAI
semconv. We instrument once with `gen_ai.*` (the convention the talk advocates),
so Phoenix accepts the spans but can't light up its LLM views. This is the
fragmentation problem made visible — and the case for normalizing at the edge
(`normalizer/`, and `../resources.md`).

## The forensics beat

The third scripted prompt drives the agent to **delete the free-plan records**.
Find the `execute_tool delete_records` span: it carries
`gen_ai.tool.call.arguments` and `gen_ai.tool.call.result`.

Those two attributes are **opt-in / off by default** in the OTel GenAI spec — the
demo deliberately enables them in `agent/agent.py`. That single choice is the
difference between a trace that proves a tool *ran* and one that proves *what it
did*. See `../research.md` for the standards detail.

## How it fits together

```
agent/run.sh ──OTLP(localhost:4318)──► otel-collector ──┬─► debug (console)
  Anthropic + OpenLIT (chat spans)                       ├─► Jaeger
  + manual execute_tool spans                            ├─► Phoenix
                                                         ├─► OpenLIT
                                                         ├─► Langfuse
                                                         ├─► Dash0 (optional)
                                                         └─► data-prepper ──► OpenSearch (opt-in, heavy)
```

## Related demos (reference only)

These live in `dash0-examples/` and aren't part of this harness:

- **agentgateway** — AI gateway (Gateway API) with GenAI telemetry; the tool-call
  data plane / enforcement point between agents and tools.
- **kagent** — agents as first-class Kubernetes workloads; agent lifecycle as a CR.
- **HolmesGPT** — agentic SRE troubleshooter that reads OTel data over MCP.
