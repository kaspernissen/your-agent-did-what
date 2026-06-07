# ANALYSIS — GenAI Observability, Measured

What the demos in this directory actually emit, captured by running them against a real Anthropic API on 2026-06-07. Every attribute below was read from an OpenTelemetry Collector `debug` exporter — **observed, not assumed**. This is the durable record behind the talk's claims.

> Method: each demo was run live (real Claude calls); spans were captured from the collector `debug` exporter; backend arrival was confirmed via each tool's API where possible. Caveats and what we could *not* verify are at the end.

---

## Demo 1 — one app, OTel GenAI semconv, fanned out

The agent: Anthropic Claude (`claude-sonnet-4-20250514`), auto-instrumented by the **OpenLIT SDK** (`openlit.init()`), plus **hand-written `execute_tool` spans**. A fake-database tool with a `delete_records` operation.

### Span structure actually produced (one agent run)

| Span | Kind | Instrumentation scope | Notes |
|---|---|---|---|
| `invoke_agent db-ops-agent` | Internal | `your-agent-did-what.demo-agent` (hand-written) | root; only `gen_ai.operation.name`, `gen_ai.agent.name` |
| `chat claude-sonnet-4-20250514` | Client | `openlit.instrumentation.anthropic` | the LLM call; rich `gen_ai.*` |
| `execute_tool list_records` / `delete_records` | Internal | `your-agent-did-what.demo-agent` (hand-written) | child of `invoke_agent`; the forensic spans |
| `POST` | Client | `opentelemetry.instrumentation.httpx` | raw HTTP to api.anthropic.com — pure plumbing |

The httpx `POST` spans are the literal "spans named just POST" point from the deck — emitted automatically, carrying no GenAI meaning.

### Attribute inventory — `chat` span (OpenLIT auto-instrumentation), verbatim

```
gen_ai.operation.name: chat
gen_ai.provider.name: anthropic          # current spec name (NOT the deprecated gen_ai.system)
gen_ai.request.model: claude-sonnet-4-20250514
gen_ai.response.model: claude-sonnet-4-20250514
gen_ai.request.max_tokens: 1024
gen_ai.request.temperature: 1.0
gen_ai.request.top_k / top_p: 1.0
gen_ai.request.stop_sequences: []
gen_ai.request.stream: false
gen_ai.response.id: msg_01K1uy...
gen_ai.response.finish_reasons: ["tool_use"]
gen_ai.output.type: text
gen_ai.usage.input_tokens: 487
gen_ai.usage.output_tokens: 49
gen_ai.input.messages: [ ... full conversation JSON as a string ... ]
gen_ai.output.messages: [ ... assistant response + tool_call JSON ... ]
```

**OpenLIT-specific extensions (NOT in the core OTel GenAI spec):**
```
gen_ai.client.token.usage: 536           # input+output sum
gen_ai.usage.cost: 0                      # 0 for unpriced models
gen_ai.usage.cache_read.input_tokens / cache_creation.input_tokens
gen_ai.server.time_to_first_token: 1.4375   # real latency
gen_ai.server.time_per_output_token: 0
gen_ai.sdk.version: 0.107.0
gen_ai.tool.name / gen_ai.tool.call.id / gen_ai.tool.args   # tool call echoed onto the chat span
telemetry.sdk.name: openlit
```
Note OpenLIT uses **`gen_ai.tool.args`** on the chat span — a *non-standard* name (spec is `gen_ai.tool.call.arguments`).

### Attribute inventory — `execute_tool delete_records` span (hand-written), verbatim

```
gen_ai.operation.name: execute_tool
gen_ai.tool.name: delete_records
gen_ai.tool.call.id: toolu_013N48...
gen_ai.tool.type: function
gen_ai.tool.call.arguments: {"plan": "free"}          # OPT-IN / off by default in the spec
gen_ai.tool.call.result: {"deleted": 2, "remaining": 1}   # OPT-IN / off by default
```

**This is the forensics payoff.** `gen_ai.tool.call.arguments` and `.result` are opt-in/off-by-default per the OTel spec (`research.md`). Enabling them is the difference between a trace that proves the delete tool *ran* and one that proves it ran with `{"plan":"free"}` and removed 2 rows. With default instrumentation, that span exists but is empty.

### Backend rendering matrix (same trace, different viewers)

| Backend | Received? | What it shows |
|---|---|---|
| **debug** (console) | ✅ | everything, raw — the source of truth above |
| **Jaeger** | ✅ confirmed via API (`db-ops-agent` service; spans `invoke_agent`, `chat …`, `execute_tool …`, `POST`) | generic spans, no GenAI awareness — tokens/model/tool args are just string tags you must hunt for |
| **OpenLIT** | needs the startup fix below | OTel-semconv-native GenAI dashboards (tokens, cost, model) |
| **Phoenix** | (not visually captured) | per research: accepts `gen_ai.*` but renders as **plain spans** (OpenInference-native) |
| **Langfuse** | (not captured this run) | per research: maps `gen_ai.*` into its observation model |

> **Harness bug found & fixed:** the OpenLIT container crashed on first run (`/app/client/data/.nextauth_secret: No such file or directory`). Fix (now in `docker-compose.yml`): a named volume `openlit-data:/app/client/data` + `SQLITE_DATABASE_URL=file:/app/client/data/data.db`, matching OpenLIT's official compose. After the fix the UI boots healthy (HTTP 307 to login).

---

## Demo 2 — `gen_ai_normalizer` at the collector (OpenInference → OTel)

The agent is instrumented with **OpenInference** (`openinference.instrumentation.anthropic 1.0.6`), emitting `llm.*` / `openinference.*`. The custom collector (built with `ocb`, modules pinned to `v0.153.0`; builder `v0.153.0` — note `v0.137.0` failed on a missing internal package) runs `gen_ai_normalizer` with `remove_originals: true`.

### What the processor rewrote (observed before → after)

| OpenInference (before) | OTel `gen_ai.*` (after) |
|---|---|
| `llm.provider` | `gen_ai.provider.name` |
| `llm.model_name` | `gen_ai.request.model` |
| `llm.token_count.prompt` | `gen_ai.usage.input_tokens` |
| `llm.token_count.completion` | `gen_ai.usage.output_tokens` |
| `openinference.span.kind` (`LLM`) | `gen_ai.operation.name` (`chat`) |

Source keys were **dropped** (`remove_originals: true`).

### What it did NOT touch (important)

These passed through **unchanged** — the normalizer maps scalar/identity attributes but **not message content or tool schemas**:
```
llm.system, llm.invocation_parameters,
llm.input_messages.*, llm.output_messages.*, llm.tools.*,
input.value, input.mime_type, output.value, output.mime_type
```
So after normalization the span is a **hybrid**: core attributes are OTel `gen_ai.*`, but the prompt/completion bodies remain in OpenInference shape. A backend that needs the messages still has to understand OpenInference for those. **Partial normalization** is the honest takeaway — the processor canonicalizes the dimensions you'd group/cost/route on, not the full payload.

> Also note the span name stayed `messages.create` (OpenInference's name) — `gen_ai_normalizer` rewrites attributes, not span names.

---

## Demo 3 — Arconia convention switching (Spring AI / Java)

Minimal Spring AI app (Spring Boot 4.0.5, Spring AI 2.0.0-M5, Arconia 0.27.1, Java 21), Anthropic via `spring-ai-starter-model-anthropic`. We flipped `arconia.observations.conventions.opentelemetry.ai.flavor` across `opentelemetry`, `openlit`, `openllmetry`.

### Result: the flavor flip WORKS — one property changes the attribute names

> Correction: our first attempt showed "no effect" because we had copied the salaboy *base* module, which depends on `arconia-opentelemetry-`**`semantic-conventions`** (OTel-only, no flavor beans). The flavor switch lives in `arconia-opentelemetry-`**`ai`**`-semantic-conventions` (the artifact the openlit/openllmetry/langsmith salaboy modules use). After swapping that one dependency (and setting `capture-content=SPAN_ATTRIBUTES` — the `-ai-` artifact makes it an enum, not a boolean), flipping the property re-emits the spans under different conventions, no code change. Same versions throughout (0.27.1 / 2.0.0-M5) — it was a dependency bug, not a version gap.

Observed differences on the LLM span (same code, three flavors):

| Concept | `opentelemetry` | `openlit` | `openllmetry` |
|---|---|---|---|
| Provider / system | **`gen_ai.provider.name`** | **`gen_ai.system`** | **`gen_ai.system`** |
| Streaming flag | `gen_ai.request.stream` | `gen_ai.request.is_stream` | (absent on model span) |
| Workflow/advisor spans | `gen_ai.*` only | `gen_ai.*` only | **adds `traceloop.entity.input/output/name`, `traceloop.span.kind`** |
| operation / model / tokens / messages | `gen_ai.operation.name`, `gen_ai.request.model`, `gen_ai.usage.input_tokens/output_tokens`, `gen_ai.input.messages/output.messages` — identical keys across all three |

So the differences are real but **narrow** in this version: the headline is the provider key (`gen_ai.provider.name` vs `gen_ai.system`), the streaming-flag key, and OpenLLMetry's `traceloop.*` additions. The bulk of the attributes stay `gen_ai.*` across flavors. "Five conventions, one property" is genuine — and also a reminder that, today, the conventions overlap heavily and diverge mostly at the edges.

### Span structure (Spring AI, all flavors)
```
POST /api/chat                  (Server)
└─ spring_ai chat_client        (Internal, spring.ai.kind=chat_client; openllmetry adds traceloop.span.kind=workflow)
   └─ call                      (Internal, advisor)
      └─ chat claude-haiku-4-5  (Internal, the LLM span with the flavor-dependent attributes above)
```

---

## Cross-cutting synthesis — the state of the space (measured)

1. **The ecosystem really is converging on `gen_ai.*`.** OpenLIT (Python SDK), Spring AI/Arconia (Java), and the `gen_ai_normalizer` output all land on OpenTelemetry GenAI semconv attribute names. The shared vocabulary is real, not aspirational — for the core dimensions.

2. **But the provider key alone fragments three ways — sometimes by config.**
   - OpenLIT Python SDK → **`gen_ai.provider.name`** (current spec)
   - `gen_ai_normalizer` output → **`gen_ai.provider.name`** (current spec)
   - Arconia → **depends on the flavor**: `opentelemetry`→`gen_ai.provider.name`, but `openlit`/`openllmetry`→**`gen_ai.system`** (the deprecated key, which those conventions still use)
   A backend keying on one misses the other. "Conforms to OTel GenAI" is necessary but not sufficient — *which revision/flavor* matters, and the same tool can emit either depending on one property.

3. **Normalization is partial, not total.** `gen_ai_normalizer` canonicalizes the attributes you group/cost/route on, but leaves message bodies in the source convention. It fixes the dashboards and cost math; it does not make an OpenInference trace fully OTel-native end to end. Good enough for the platform pitch ("normalize centrally"); worth being precise about the boundary.

4. **SDK extensions are everywhere.** OpenLIT adds ~8 non-spec attributes (cost, cache tokens, latency, `gen_ai.tool.args`). Useful, but they're vendor surface area on top of the standard — exactly the kind of drift the SIG is trying to corral.

5. **The forensic content is a switch you have to throw.** `gen_ai.tool.call.arguments/result` only appeared because we set them by hand. Default instrumentation gives you the *shape* of what the agent did, not the *substance*. This is the talk's load-bearing forensics point, demonstrated.

6. **Generic vs GenAI-native is a real cliff.** Jaeger took the exact same bytes and showed plumbing; the GenAI-native tools show tokens/cost/model. Same trace, and the viewer decides whether it's legible.

### What we did NOT verify (be honest on stage)
- Phoenix / Langfuse / OpenSearch **visual rendering** of the trace (Jaeger arrival was API-confirmed; OpenLIT was fixed but not re-captured visually; Langfuse and OpenSearch were not run to completion this round).
- OpenSearch Agent Traces end-to-end (its UI is RFC-stage in OSS; not booted).
- The `langsmith` flavor (we captured `opentelemetry`/`openlit`/`openllmetry`; langsmith is the 4th `-ai-` flavor, not yet run).
- *(Resolved)* The Arconia flavor switch — initially mis-built with the OTel-only dependency; re-run with `arconia-opentelemetry-ai-semantic-conventions` confirms it works (see Demo 3).

### Pointers
- Standards detail behind the opt-in forensic attributes: `../research.md`.
- The broader landscape + Jaeger roadmap: `../landscape.md`.
