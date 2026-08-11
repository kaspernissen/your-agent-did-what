# Demos Harness — Design Spec

> **Historical.** A spec or plan from an earlier stage of this project, kept as a record of
> what was decided and why. It describes structures that no longer exist — the demo-1 /
> demo-2 split, the multi-backend fan-out, the Arconia and Spring AI demos, the over-quota
> scenario. For how the repo works today see [`AGENTS.md`](../../../AGENTS.md) and
> [`demos/README.md`](../../../demos/README.md).

**Date:** 2026-06-07
**Topic:** A docker-compose "test harness" for the *Your Agent Did What?* talk that showcases the GenAI-observability **backend/visualization** landscape — one instrumented tool-calling agent fanned out to multiple OSS viewers + a vendor.
**Location:** `/Users/kaspernissen/kaspernissen/your-agent-did-what/demos`

---

## 1. Purpose

The talk's other content (`abstract.md`, `resources.md`, `research.md`) and the sibling demos (`dash0-examples/{langchain,openllmetry,openlit}`) cover *instrumentation*. This harness answers the next question — **once GenAI traces are flowing, where do you send and view them?** — structured around three questions from the talk:

1. **What does the OpenTelemetry project itself give you to visualize GenAI traces?** → the Collector `debug` exporter (console) + Jaeger (CNCF sibling, generic trace viewer). Honest framing: OTel standardizes the *production* and *transport* of telemetry, not its visualization. It is vendor-neutral by design.
2. **How do you send data to a collector so it reaches a vendor?** → the Collector `otlp/dash0` exporter (reusing the existing dash0-examples pattern), env-gated.
3. **What OSS solutions exist?** → Arize Phoenix, Langfuse, OpenLIT, shown side by side — spanning the *generic-vs-GenAI-native* and *OTel-semconv-vs-OpenInference* axes.

The pedagogical core: **instrument once (OTel GenAI semconv), view everywhere, and watch how differently each backend renders the same trace.** The differences are the lesson.

## 2. Non-goals (YAGNI)

- No multiple per-convention apps and no `genainormalizer` wiring in this harness (single app, single convention — the fragmentation/normalizer story stays in slides + `resources.md`). Noted as a possible future extension.
- No Kubernetes. kagent / HolmesGPT / agentgateway are **reference-only** (README pointers to the existing `dash0-examples` demos), not new infra.
- No production hardening (default/demo credentials, ephemeral storage, no TLS internally).

## 3. Architecture

One agent → one Collector → fan-out. Each backend is a **docker-compose profile** so only the chosen ones start; the collector always runs.

```
agent (local python, run.sh)           OTel Collector (always on)
  Anthropic Claude + tools      OTLP    receivers: otlp 4317/4318 (host-mapped)
  OpenLIT SDK (auto LLM spans)  ───────► processors: batch
  + manual execute_tool spans            exporters (fan-out):
  OTel GenAI semconv                       ├─ debug ───────────► console (always)
                                           ├─ otlp/jaeger ─────► jaeger:4317        [profile: jaeger]
                                           ├─ otlp/phoenix ────► phoenix:4317       [profile: phoenix]
                                           ├─ otlphttp/langfuse► langfuse-web:3000  [profile: langfuse]
                                           ├─ otlp/openlit ────► openlit:4318       [profile: openlit]
                                           └─ otlp/dash0 ──────► Dash0 (OTLP)        [env-gated]
```

**Why one collector fanning out:** it *is* the demo — the same bytes land in every UI, so differences are about the viewer, not the data. It also directly shows question #1 (debug) and #2 (dash0) in the same pipeline.

### Port plan (only UIs map to the host; collector→backend stays on the internal docker network)

| Service | Host port | Internal OTLP target (collector → backend) | Notes |
|---|---|---|---|
| otel-collector | 4317, 4318 | — (receives from local agent) | only OTLP endpoint exposed to host |
| jaeger (v2) | 16686 (UI) | `jaeger:4317` (gRPC) | `jaegertracing/jaeger:2.x` — v1 all-in-one is EOL 2025-12-31 |
| phoenix | 6006 (UI + OTLP/HTTP) | `phoenix:4317` (gRPC) | UI and OTLP/HTTP share 6006; gRPC on 4317 |
| langfuse-web | 3000 (UI) | `http://langfuse-web:3000/api/public/otel` | OTLP **HTTP only**, Basic auth |
| openlit | 3001 → 3000 (UI) | `openlit:4318` (HTTP) | remapped off 3000 to avoid Langfuse clash; bundled collector ingests |

No host-port collisions because only UI ports are published; the collector reaches each backend by docker DNS name on its internal port.

## 4. The agent (`agent/`)

A minimal Python tool-calling loop using the official `anthropic` SDK (Claude), auth via `ANTHROPIC_API_KEY` (`sk-ant-…`) from the environment / `.env` — same model as the existing demos.

**Tools (`tools.py`)** — an in-memory fake "database" so the trace tells the talk's story:
- `list_records()` — returns rows
- `query(filter)` — reads rows
- `delete_records(filter)` — destructive; this is the "your agent deleted a database" beat

**Loop (`app.py`):**
- `openlit.init(otlp_endpoint="http://localhost:4318", ...)` — one line; auto-instruments `anthropic.messages.create`, emitting **OTel GenAI semconv** `chat` spans.
- Wrap the run in a manual `invoke_agent {agent.name}` parent span.
- For each tool the model calls, hand-write a child **`execute_tool {gen_ai.tool.name}`** span (kind INTERNAL) per the GenAI agent-span conventions, setting:
  - `gen_ai.operation.name = "execute_tool"`
  - `gen_ai.tool.name`, `gen_ai.tool.call.id`, `gen_ai.tool.type = "function"`
  - **opt-in / off-by-default (deliberately enabled here):** `gen_ai.tool.call.arguments`, `gen_ai.tool.call.result`
  - A README callout: these two are *opt-in and off by default* in the spec — turning them on is exactly what `research.md` identifies as the difference between a trace that proves a tool *ran* and one that proves *what it did*.
- A small set of scripted prompts (`02_run_agent.sh`), including one that drives the agent to `delete_records`, so a forensic trace is produced on demand.

**Why OpenLIT SDK + manual tool spans:** auto-instrumentation realistically gives you the LLM/chat span (the "one line" magic, on stage); plain `messages.create` with tool-use records tool calls as attributes on the chat span, **not** as child `execute_tool` spans — so the agent layer hand-writes those. This is both realistic and the pedagogically important part (it's where forensic opt-in lives).

## 5. Backends — concrete setup (verified 2026-06-07)

### Jaeger (profile: `jaeger`) — generic baseline
- Image `jaegertracing/jaeger:2.x` (pin a concrete tag). OTLP enabled by default. UI 16686.
- Lesson: a GenAI trace in a viewer with **zero GenAI awareness** — spans show as `chat …`, `execute_tool …`, raw attributes. The "164 spans named POST" point, live.

### Arize Phoenix (profile: `phoenix`) — GenAI-native, OpenInference-native
- Image `arizephoenix/phoenix:version-17.2.0` (or pin current). UI + OTLP/HTTP on 6006; OTLP gRPC on 4317. Auth off by default (do **not** set `PHOENIX_ENABLE_AUTH`). Ephemeral storage fine for demo.
- Lesson / honest gotcha: Phoenix keys its rich LLM UI off **OpenInference** attributes. Our `gen_ai.*` spans land and are queryable but render as **plain spans** (no LLM span-kind, no message/token panels). This is the fragmentation made visible and ties to the genainormalizer half of the talk. README states this explicitly so it reads as a *teaching point*, not a bug.

### Langfuse (profile: `langfuse`) — OSS LLM platform (the heavy one)
- v3 self-host: `langfuse/langfuse:3` (web) + `langfuse/langfuse-worker:3` + Postgres 17 + ClickHouse + Redis 7 + MinIO. UI 3000.
- OTLP ingest: **HTTP only** at `/api/public/otel` (collector appends `/v1/traces`), **Basic auth** = `base64(public_key:secret_key)`.
- Headless bootstrap via `LANGFUSE_INIT_*` env (org/project/user/keys) so it works on first boot with known demo keys; the collector's `Authorization: Basic …` header is built from those keys.
- `SALT` + `ENCRYPTION_KEY` (64 hex chars) must match across web and worker.
- Maps `gen_ai.*` natively into its observation model (input/output/model/usage/cost) → renders our semconv data well.
- README flags the resource cost and that you can omit this profile for a lighter demo.

### OpenLIT (profile: `openlit`) — OTel-native GenAI dashboard
- `ghcr.io/openlit/openlit:latest` (UI + bundled collector on 4317/4318) + `clickhouse/clickhouse-server:24.4.1`. UI remapped to host **3001**. Default login `user@openlit.io` / `openlituser`.
- Collector exports to `openlit:4318`; OpenLIT's embedded pipeline writes to its ClickHouse; UI reads it.
- Renders our OTel-semconv data natively (GenAI-aware dashboards, token/cost).
- Note: OpenLIT is used here **only as a backend**. Its SDK is used in the agent for auto-instrumentation — flag this dual role in the README so it's not confusing.

### Dash0 (env-gated, not a service) — the vendor path (question #2)
- Collector `otlp/dash0` exporter using `DASH0_AUTH_TOKEN`, `DASH0_DATASET`, `DASH0_ENDPOINT_OTLP_GRPC_HOSTNAME/PORT` from `.env`, matching the existing dash0-examples config.
- If the token is unset, expect harmless export errors in collector logs (documented), or comment the exporter out.

## 6. Collector config (`collector/otel-collector-config.yaml`)

- `receivers: otlp` (grpc 4317 / http 4318).
- `processors: batch`.
- `exporters`: `debug` (detailed), `otlp/jaeger`, `otlp/phoenix` (gRPC, `tls.insecure: true`), `otlphttp/langfuse` (with Basic auth header), `otlp/openlit`, `otlp/dash0`.
- Single `traces` pipeline referencing all exporters. Inactive-profile backends → harmless connection errors (documented). `retry_on_failure` + bounded `sending_queue` so one down backend never blocks others.
- Pin collector image `otel/opentelemetry-collector-contrib:<tag>` (contrib, for the broader exporter set).

## 7. File layout (mirrors dash0-examples conventions)

```
demos/
  README.md                          # narrative for the 3 questions + per-UI "what to look at" + reference section
  .env.template                      # ANTHROPIC_API_KEY; LANGFUSE init keys; optional DASH0_*
  docker-compose.yml                 # collector (always) + backends behind profiles + their deps
  collector/
    otel-collector-config.yaml
  agent/
    app.py                           # agent loop, OpenLIT init, manual execute_tool spans
    tools.py                         # in-memory database tool (list/query/delete)
    requirements.txt                 # anthropic, openlit, opentelemetry-* (api/sdk)
    run.sh                           # local run against collector on localhost:4318
  scripts/
    01_up.sh                         # docker compose --profile ... up -d, wait for health
    02_run_agent.sh                  # fire scripted prompts incl. the delete one
    03_open_uis.sh                   # print/open backend URLs for whatever profiles are up
  00_run.sh                          # end-to-end: up + run agent + print URLs
  01_cleanup.sh                      # docker compose down -v
```

Default `00_run.sh` brings up **all** profiles; the README shows how to start a subset (e.g. `docker compose --profile jaeger --profile phoenix up -d`) for a lighter or more focused live demo.

## 8. README narrative (the deliverable that ties it together)

1. **Project-native** — run with only `debug` (+ Jaeger): this is what OTel itself hands you. OTel standardizes telemetry, not dashboards.
2. **To a vendor** — set `DASH0_*`, the same trace appears in Dash0. One exporter line.
3. **OSS landscape** — bring up Phoenix / Langfuse / OpenLIT; open each UI; compare the *same* trace. Call out: generic (Jaeger) vs GenAI-native (the rest); and OTel-semconv-native (OpenLIT, Dash0, Langfuse-maps-it) vs OpenInference-native (Phoenix renders ours as plain spans).
4. **Forensics callout** — point at the `execute_tool` span with `gen_ai.tool.call.arguments/result`; explain these are opt-in/off-by-default per spec (link `research.md`); show the `delete_records` trace as "what your telemetry tells you after the agent deleted the database."
5. **Reference-only** — where kagent / agentgateway (existing `dash0-examples` demos) and HolmesGPT fit.

## 9. Success criteria

- `00_run.sh` (with `ANTHROPIC_API_KEY` set) brings up the stack, runs the agent, and the **same** trace is viewable in every started backend's UI.
- The `delete_records` run produces a trace with a child `execute_tool delete_records` span carrying `gen_ai.tool.call.arguments` and `gen_ai.tool.call.result`.
- Jaeger shows it as generic spans; OpenLIT/Langfuse show GenAI-aware rendering; Phoenix shows it as plain spans (documented expectation).
- `01_cleanup.sh` removes everything (`down -v`).
- README lets a reader reproduce each of the three questions independently.

## 10. Open items to confirm during implementation

- Exact current pinned tags for Phoenix / Langfuse / OpenLIT / Jaeger / collector-contrib at build time.
- Whether to base the Langfuse services on the upstream `docker-compose.yml` (recommended) vs. hand-rolling, and trimming it to the minimal env set.
- Confirm OpenLIT bundled-collector ingest on `openlit:4318` works when fed by an *external* collector (vs. direct from SDK).
- Confirm the manual `execute_tool` spans share OpenLIT's tracer/provider so they land in the same trace as the auto LLM spans.

---

## 11. Scope expansion (2026-06-07): Demos 2 & 3, OpenSearch, run-and-analyze

The harness grows from one demo to a small program of three, plus an opt-in backend and a verification/analysis phase. **Demo 1 stays flat at `demos/`** (the flagship); Demos 2 and 3 are sibling subdirectories; an umbrella `demos/README.md` ties them together.

```
demos/
  README.md            # umbrella: what each demo shows + how they relate
  <Demo 1 files...>    # backends fan-out harness (Tasks 1-11)
  normalizer/          # Demo 2: gen_ai_normalizer processor
  arconia/             # Demo 3: Arconia convention-switching (Java/Spring AI)
  ANALYSIS.md          # produced after running everything (Task 16)
```

### Demo 2 — `gen_ai_normalizer` processor (`demos/normalizer/`)

**Shows:** the *collector-side* answer to fragmentation. An app instrumented with a **non-OTel** convention (OpenInference and/or OpenLLMetry) sends OTLP to a collector running `gen_ai_normalizer`, which rewrites the attributes to OTel GenAI semconv; an OTel-native backend then renders it. Pair a "raw" path (no normalizer) and a "normalized" path so the before/after attribute diff is the demo.

- **App:** reuse the same fake-database tool-calling agent shape as Demo 1, but instrument with **OpenInference** (`openinference-instrumentation-anthropic`) and/or **OpenLLMetry/Traceloop** so it emits `llm.*` / `openinference.*` attributes. (Two small apps, or one switchable by env, emitting the two source conventions.)
- **Collector:** `gen_ai_normalizer` with `sources: [{name: openinference, remove_originals: true}, {name: openllmetry, remove_originals: true}]`, placed in the traces pipeline before exporters. Export to `debug` (to show the rewritten attributes) + an OTel-native backend (reuse OpenLIT or Jaeger).
- **Image constraint (verified):** the processor is **not** in `otel/opentelemetry-collector-contrib:0.153.0`. Options, in preference order: (a) use the contrib image `0.154.0`+ once it includes it; (b) build a custom collector with `ocb` (manifest with the `genainormalizerprocessor` gomod). The plan implements the **ocb** path (works today, version-independent) and notes the image alternative.
- **Payoff:** `debug` exporter output shows `llm.model_name` etc. *before* and `gen_ai.request.model` etc. *after*; the OTel-native backend lights up only on the normalized path. Directly demonstrates the "instrument with anything, normalize centrally" platform pitch and the contrib donation (issue #46069).

### Demo 3 — Arconia convention-switching (`demos/arconia/`)

**Shows:** the *SDK-side* answer. One Spring AI (Java) app calling Anthropic; flipping a single property re-emits the same spans under a different convention's attribute names — no code change.

- **Base:** fork/trim from `salaboy/observing-ai` (`java/spring-ai-with-arconia/...`) rather than hand-writing a Spring app. Strip the React frontend to a minimal `ChatController` + `ChatClient`.
- **Stack (pinned):** Java 21, Spring Boot 4.0.5, Spring AI 2.0.0-M5, Arconia 0.27.1. Deps: `spring-ai-starter-model-anthropic`, `arconia-opentelemetry-spring-boot-starter`, `arconia-opentelemetry-semantic-conventions` (swap to `arconia-openinference-ai-semantic-conventions` for the OpenInference variant — verify exact artifactId against the pinned BOM).
- **Run:** `ANTHROPIC_API_KEY=… ./mvnw spring-boot:run`, OTLP to a local collector at `:4318` (reuse Demo 1's collector or a standalone one exporting to `debug`).
- **The flip:** `arconia.observations.conventions.opentelemetry.ai.flavor = opentelemetry | openlit | openllmetry | langsmith`. Capture the emitted attribute names per flavor (via the collector `debug` exporter) and diff them — that diff is the demo.
- **Note:** requires a JDK + Maven; documented as the one demo that isn't pure docker-compose. Acceptable since it's a fundamentally different (JVM) stack and that's part of the point.

### OpenSearch Agent Traces — opt-in backend (Demo 1)

Add as an **opt-in heavyweight profile** (`opensearch`) in Demo 1's compose, clearly caveated:
- Path: collector `otlp` → **Data Prepper** (`otel_trace_source` 21890 → `otel_trace_raw` → opensearch sink, `trace_analytics_raw: true`) → OpenSearch (`otel-v1-apm-span-*`) → Dashboards UI. OpenSearch does **not** accept OTLP directly.
- Services: `opensearchproject/opensearch` (9200), `opensearchproject/opensearch-dashboards` (5601), `opensearchproject/data-prepper` (21890/2021). Security disabled for the demo (`DISABLE_SECURITY_PLUGIN=true`, `discovery.type=single-node`); ~4 GB RAM.
- **Caveat in README:** the dedicated **Agent Traces UI is RFC-stage in OSS OpenSearch** (live on AWS); on stable OSS you get spans in the trace-analytics index but possibly not the dedicated agent UI. It *is* pure `gen_ai.*` semconv (no SDK lock-in), so the same Demo 1 instrumentation feeds it unchanged — only the collector exporter + Data Prepper are added.

### Run-and-analyze phase → `demos/ANALYSIS.md`

After all demos build, **run them with a real `ANTHROPIC_API_KEY`**, drive the agent, and capture:
1. The exact GenAI attributes/spans the agent emits per demo (from the collector `debug` exporter and each backend).
2. How `gen_ai_normalizer` transforms OpenInference/OpenLLMetry input → OTel output (before/after attribute tables).
3. How Arconia's `flavor` changes the emitted attribute names (per-flavor attribute table).
4. How each backend renders the *same* trace (what shows, what's missing — especially Phoenix on `gen_ai.*`).

Store as `demos/ANALYSIS.md`: attribute tables, per-backend rendering notes, normalizer before/after, Arconia flavor diffs, and a synthesis of the space. This is the durable artifact the user wants "for later." **Gated on:** a working `ANTHROPIC_API_KEY` (real API calls) and local Docker resources (Langfuse + OpenSearch are heavy); confirm before running.

### Open items added by this expansion

- Confirm whether `otel/opentelemetry-collector-contrib:0.154.0` is released at build time (use it) or fall back to `ocb`.
- Confirm OpenInference/OpenLLMetry Anthropic instrumentation packages and the attribute names they actually emit (to validate the normalizer mappings end-to-end).
- Confirm the exact Arconia semantic-conventions artifactId against `arconia-bom:0.27.1` (Maven demo vs. Gradle-post naming differ).
- Decide whether Demo 3 reuses Demo 1's collector or ships its own minimal one (default: its own, to keep the JVM demo self-contained).
