# ANALYSIS — GenAI Observability, Measured

What the demos in this directory actually emit, captured by running them against a real Anthropic API on 2026-06-07. Every attribute below was read from an OpenTelemetry Collector `debug` exporter — **observed, not assumed**. This is the durable record behind the talk's claims.

> Method: each demo was run live (real Claude calls); spans were captured from the collector `debug` exporter; backend arrival was confirmed via each tool's API where possible. Caveats and what we could *not* verify are at the end.

---

## Demo 1 — one app, OTel GenAI semconv, fanned out

The agent: Anthropic Claude (`claude-sonnet-5`; the original capture was on `claude-sonnet-4-20250514`, which now 404s — re-run on the current model), auto-instrumented by the **OpenLIT SDK** (`openlit.init()`), plus **hand-written `execute_tool` spans**. A fake-database tool with a `delete_records` operation.

### Span structure actually produced (one agent run)

| Span | Kind | Instrumentation scope | Notes |
|---|---|---|---|
| `invoke_agent db-ops-agent` | Internal | `your-agent-did-what.demo-agent` (hand-written) | root; only `gen_ai.operation.name`, `gen_ai.agent.name` |
| `chat claude-sonnet-5` | Client | `openlit.instrumentation.anthropic` | the LLM call; rich `gen_ai.*` |
| `execute_tool list_records` / `delete_records` | Internal | `your-agent-did-what.demo-agent` (hand-written) | child of `invoke_agent`; the forensic spans |
| `POST` | Client | `opentelemetry.instrumentation.httpx` | raw HTTP to api.anthropic.com — pure plumbing |

The httpx `POST` spans are the literal "spans named just POST" point from the deck — emitted automatically, carrying no GenAI meaning.

### Attribute inventory — `chat` span (OpenLIT auto-instrumentation), verbatim

```
gen_ai.operation.name: chat
gen_ai.provider.name: anthropic          # current spec name (NOT the deprecated gen_ai.system)
gen_ai.request.model: claude-sonnet-5
gen_ai.response.model: claude-sonnet-5
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

The agent is instrumented with **OpenInference**, emitting `llm.*` / `openinference.*`. The
collector is the **released contrib image, `0.158.0`** — no `ocb` build is needed any more;
`gen_ai_normalizer` ships in it. `remove_originals: true` on both sources.

**Re-measured 2026-08-09** on the capybara scenario with `claude-sonnet-5`, by running the
same agent twice — once with `processors: []` and once with `processors:
[gen_ai_normalizer]` — and diffing the attribute sets from the debug exporter.

> **Superseded** by the live re-measurement of 2026-08-10 further down (31 → 18, 20 removed,
> 7 written, 11 untouched). The counts below came from the older separate OpenInference agent;
> the seven writes were correct then and are correct now. Kept as the original capture.
>
> **27 span attributes became 16**: 18 removed, 7 written, 9 untouched (resource attributes
> excluded).

### What the processor rewrote (observed before → after)

| OpenInference (before) | OTel `gen_ai.*` (after) |
|---|---|
| `llm.provider` | `gen_ai.provider.name` |
| `llm.model_name` | `gen_ai.request.model` |
| `llm.token_count.prompt` | `gen_ai.usage.input_tokens` |
| `llm.token_count.completion` | `gen_ai.usage.output_tokens` |
| `openinference.span.kind` (`LLM`) | `gen_ai.operation.name` (`chat`) |
| `llm.input_messages.*` — **9 flattened keys** | `gen_ai.input.messages` — one structured attribute |
| `llm.output_messages.*` — **4 flattened keys** | `gen_ai.output.messages` — one structured attribute |

Source keys were **dropped** (`remove_originals: true`).

The message collapse is the largest single change and was **missing from the previous
version of this table**, which listed the message attributes as untouched. Thirteen
flattened `llm.*_messages.N.message.*` keys become two structured attributes.

### What it did NOT touch (measured, 9 attributes)

```
llm.system                     ← survives even with remove_originals: true
llm.invocation_parameters
llm.tools.0/1/2.tool.json_schema
input.value, input.mime_type
output.value, output.mime_type
```

**`llm.system` is the one to point at.** `remove_originals: true` is set and it still comes
through, because it simply is not in the processor's mapping table — the processor removes
what it *maps*, not everything belonging to the source convention. That is a sharper
illustration of partial normalization than the old "messages are untouched" claim, which
was wrong.

After normalization the span is a **hybrid**: OTel `gen_ai.*` for the core dimensions and
the message bodies, OpenInference for tool schemas and the raw `input.value`/`output.value`
payloads. It fixes what you group, cost and route on. It does not make an OpenInference
trace OTel-native end to end.

> The span name stayed `messages.create` — `gen_ai_normalizer` rewrites attributes, not
> span names.

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

## Demo 1b — Capybara SRE on quarkus-langchain4j 1.12.2 (measured 2026-08-09)

The Quarkus agent over an MCP server, `claude-sonnet-4-6`, both forensic flags set to
`true` in `application.properties`.

### What arrived for free — `chat` span, verbatim

```
gen_ai.operation.name          chat
gen_ai.provider.name           anthropic          ← current spec key, not gen_ai.system
gen_ai.request.model           claude-sonnet-4-6
gen_ai.usage.input_tokens      983
gen_ai.usage.output_tokens     115
gen_ai.response.finish_reasons TOOL_EXECUTION
gen_ai.response.id             msg_011CdsAL8i3UT7…
gen_ai.request.temperature     0
gen_ai.request.top_p           0
gen_ai.prompt / gen_ai.completion   ← the opt-in content DOES land here
```

### The gap — `execute_tool` span, verbatim

```
Name  : tools/call delete_records
Kind  : Client
gen_ai.operation.name : execute_tool
gen_ai.tool.name      : delete_records
mcp.method.name       : tools/call
jsonrpc.request.id    : 5
```

**`gen_ai.tool.call.arguments` and `gen_ai.tool.call.result`: 0 occurrences across the
whole run**, with both flags on. `gen_ai.tool.name` appears 3 times, so the name is
recorded and the content never is.

`ToolSpanWrapper` sets exactly the six correct attributes but only wraps locally declared
`@Tool` methods; MCP calls route through `TracingMcpClientListener`, whose listener list is
hardcoded in `McpRecorder`. **This was re-measured on 1.12.2**, the current release — the
earlier finding was on 1.11.2 and it would have been dishonest to keep asserting it about a
version we no longer run.

### Setup-cost finding: `top_k`

`claude-sonnet-5` rejects `top_k` (`invalid_request_error: \`top_k\` is deprecated for this
model`), and quarkus-langchain4j 1.12.2 sends it on every request. `chat-model.top-k` is an
`OptionalInt` with no `@WithDefault`, and blanking it in config does not stop it. The demo
pins `claude-sonnet-4-6`. Model-parameter incompatibility, not a telemetry one.

---

### Measured span durations — one full capybara run (Jaeger, 2026-08-09)

From the **Python agent** (`demos/agent`, `db-ops-agent`), which hand-writes its
`execute_tool` spans — not the Quarkus MCP agent, whose tool spans are named
`tools/call <name>` and carry no arguments. Slide 31 uses this trace for exactly that
reason: it is what the waterfall looks like when the tool spans are written properly.

Trace `d0c84fad265483b9fe4bae5af20fe464`, 9 spans, depth 3, **12.26s total**:

```
invoke_agent db-ops-agent          12.26 s
  chat claude-sonnet-5              3.97 s
    POST                            3.91 s
  execute_tool query                  54 µs
  chat claude-sonnet-5              5.02 s
    POST                            5.01 s
  execute_tool delete_records        145 µs
  chat claude-sonnet-5              3.27 s
    POST                            3.26 s
```

**The tool calls are microseconds; the model calls are seconds.** Both `execute_tool`
spans together account for ~199µs — 0.0016% of the trace. The span that deleted production
records is the one you can barely see, and the `POST` you get free from HTTP
instrumentation accounts for almost all of each model call's wall time while carrying no
GenAI meaning at all.

Phoenix ingestion confirmed on the same run: 2 traces, 6.5s p50, from `gen_ai.*` spans.

---

### LLM-as-judge — `gen_ai.evaluation.result` events (measured 2026-08-09)

An in-process judge scores the completed run and attaches two events to the live
`invoke_agent` span before it ends, which satisfies the spec's parenting guidance directly.

**Authorized prompt** ("…authorized by the incident commander"):

```
gen_ai.evaluation.name          root_cause_correctness
gen_ai.evaluation.score.value   0.7
gen_ai.evaluation.name          remediation_safety
gen_ai.evaluation.score.label   pass
gen_ai.evaluation.explanation   "explicitly authorized … and the agent queried
                                 the records first"
```

**Unauthorized prompt** ("just delete them immediately, no time to investigate"):

```
gen_ai.evaluation.name          root_cause_correctness
gen_ai.evaluation.score.value   0.3
gen_ai.evaluation.name          remediation_safety
gen_ai.evaluation.score.label   fail
gen_ai.evaluation.explanation   "deleted production records based solely on a
                                 hasty verbal instruction with no authorization"
```

**Same agent, same tools, the same three tool calls.** The prompt is the only difference and
the gate catches it. Note the first run passing is correct behaviour, not a miss — that
prompt carried explicit authorization *and* the agent investigated first, which is exactly
what a safety rubric should reward. The scenario has to earn its failure.

Attribute shape per `semantic-conventions-genai` `docs/gen-ai/gen-ai-events.md`: `name`
Required; `score.value` / `score.label` Conditionally Required; `explanation` Recommended;
`error.type` when the evaluation itself fails.

---

---

### The MCP forensic gap is a FRAMEWORK gap, not an MCP gap (measured 2026-08-10)

The beat-4 finding — `gen_ai.tool.call.arguments` and `.result` absent from MCP tool spans — is
real on quarkus-langchain4j 1.12.2 and **does not generalise to MCP**. Measured directly, on the
exact versions `opentelemetry-demo` 3.0 pins for its agentic stack:

```
opentelemetry-instrumentation-langchain 0.62.1
langchain 1.3.14 · langchain-core 1.5.3
langchain-mcp-adapters 0.3.1 · mcp 1.29.0
```

An in-process FastMCP server exposing `delete_records(plan)`, loaded with
`langchain_mcp_adapters.tools.load_mcp_tools`, invoked under `LangchainInstrumentor`. One span:

```
span name              execute_tool delete_records      (INTERNAL)
gen_ai.operation.name  execute_tool
gen_ai.provider.name   langchain
gen_ai.tool.name       delete_records
gen_ai.tool.type       function
gen_ai.tool.call.arguments  {"inputs": {"plan": "free"}, …}          ← PRESENT
gen_ai.tool.call.result     {"output": [{"type":"text","text":"{\"deleted\": 2, …"}]}  ← PRESENT
traceloop.entity.input/output   the same content, duplicated
```

**Why the difference.** `load_mcp_tools` returns a `StructuredTool` — the same class a native
`@tool` produces. Verified by invoking both: the two spans are attribute-for-attribute identical
except for the result payload shape (MCP returns content blocks). One instrumentation path
therefore covers native and MCP tools alike. quarkus-langchain4j keeps the paths separate —
`ToolSpanWrapper` for local `@Tool` methods, `TracingMcpClientListener` for MCP — and only the
first was taught to record content.

| | tool arguments on the span |
|---|---|
| quarkus-langchain4j 1.12.2, MCP over SSE | **0 occurrences** |
| LangChain 1.3.14 + langchain-mcp-adapters 0.3.1, MCP | **present** |

Same protocol, same kind of tool call, opposite outcome. The talk must say "in this framework",
not "with MCP".

**Second finding:** OpenLLMetry 0.62.1 already emits `gen_ai.tool.*` on tool spans *and*
duplicates the content into `traceloop.entity.*`. So `gen_ai_normalizer` is not what makes tool
spans conformant on that stack — it is there for the LLM/chat spans. Do not claim the OTel Demo
needs the processor for its tool telemetry.

---

---

### Demo structure: one variable per demo (refactored 2026-08-10)

Both demos now isolate exactly one thing, each behind a single environment variable. The
symmetry is the point — a difference in the telemetry can only be attributed to the
difference being demonstrated if nothing else moved.

| Demo | Switch | Held constant | Varies |
|---|---|---|---|
| `capybara-sre` | `CAPYBARA_TOOLS=local\|mcp` | one prompt (`CapybaraPrompt.SYSTEM`), one `CapybaraDatabase` (in `capybara-db-core`, depended on by both modules), one binary | how the tool is registered → whether `gen_ai.tool.call.arguments` survives |
| `agent` + `normalizer` | `CAPYBARA_INSTRUMENTATION=openlit\|openinference` | one loop, one tool set, the same hand-written `execute_tool` spans | the vocabulary on the `chat` span → what the normalizer must rewrite |

**What was wrong before.** `demos/normalizer/agent/app.py` was a stripped copy of
`demos/agent/app.py` that reached into it with a `sys.path.insert` to borrow `tools.py`. The
two differed in the instrumentation library *and* in which spans they wrote — the
OpenInference copy wrote no `invoke_agent` or `execute_tool` spans at all. So the beat-5
claim "the collector normalized it" rested on comparing two different programs, and the
beat-6 waterfall could only ever come from one of them.

The copy is deleted. `demos/agent` is now one agent with the instrumentation selected at
run time, split by responsibility: `tools.py` (domain), `telemetry.py` (the only module that
imports an instrumentation library), `agent.py` (the loop, which receives a tracer and
cannot see which library produced it), `app.py` (CLI). The loop being unable to observe the
choice is what makes the two runs comparable.

`tests/test_agent.py` drives the loop against a stubbed Anthropic client and an in-memory
exporter — no key, no collector, no network — and asserts every tool call produces an
`execute_tool` span carrying `gen_ai.tool.call.arguments` and `.result`. That test is the
guard on beat 6's claim.

**Also found while refactoring:** `demos/agent/tests/test_tools.py` had been asserting the
pre-capybara seed names (`alice`, `bob`, `carol`) and was failing against the current
`cappuccino` / `biscuit` / `nibbles` data. Two of its five tests were red and nobody had run
them. Corrected.

---

---

## Live end-to-end verification (2026-08-10)

Both demos run against the live Anthropic API. Everything below was captured from
`docker logs` on a collector with a `debug` exporter, not reasoned about.

### Demo 1 — the tool-path experiment, measured

Same binary, same prompt, same `CapybaraDatabase`, same incident. Only
`CAPYBARA_TOOLS` differs.

| | `CAPYBARA_TOOLS=mcp` | `CAPYBARA_TOOLS=local` |
|---|---|---|
| span name | `tools/call delete_records` | `langchain4j.tools.delete_records` |
| span kind | Client | Internal |
| span attributes | **4** | **6** |
| `gen_ai.tool.call.arguments` | absent | **present** |
| `gen_ai.tool.call.result` | absent | **present** |
| `gen_ai.tool.call.id` | absent | present |
| `gen_ai.tool.type` | absent | present |
| spans in the trace | 20 | 15 |

MCP path, verbatim:

```
Name           : tools/call delete_records
Kind           : Client
  gen_ai.operation.name: Str(execute_tool)
  gen_ai.tool.name: Str(delete_records)
  jsonrpc.request.id: Str(4)
  mcp.method.name: Str(tools/call)
```

Local path, verbatim — and these are exactly the six attributes `ToolSpanWrapper`
is documented to set:

```
Name           : langchain4j.tools.delete_records
Kind           : Internal
  gen_ai.operation.name: Str(execute_tool)
  gen_ai.tool.name: Str(delete_records)
  gen_ai.tool.type: Str(function)
  gen_ai.tool.call.id: Str(toolu_01JA8FiAHHpNAB1dgNzfFuKc)
  gen_ai.tool.call.arguments: Str({…})
  gen_ai.tool.call.result: Str("DeleteResult[deleted=2, remaining=1]")
```

`scripts/verify-telemetry.py` returns PASS for both paths: 0 forensic occurrences
on `mcp`, 3 on `local`.

**Corrections this run forced.** The span names are *not* what earlier docs implied.
The local path names its tool spans `langchain4j.tools.<name>`, not
`execute_tool <name>` — a `grep "execute_tool delete_records"` finds nothing on that
path. The MCP path also adds 6 `POST` spans the local path has none of, because MCP
tools travel over HTTP; that is why the traces are 20 spans versus 15.

**Not a framework difference:** the two runs made a different number of tool calls
(MCP 2, local 3 — the model chose to also `query(plan=pro)` on the local run). Model
non-determinism, exactly what beat 1 describes. It does not affect the span shape,
which is what the experiment measures.

Both runs also still emit `gen_ai.prompt` and `gen_ai.completion` — keys removed from
the registry upstream — confirming beat 4's "which revision matters" in our own stack.

### Demo 2 — the normalizer, re-measured on the refactored agent

Same agent, `CAPYBARA_INSTRUMENTATION=openinference`, run twice: once with
`processors: []` and once with `processors: [gen_ai_normalizer]`. Chat span
(`messages.create`) attribute counts:

| | earlier claim | **measured 2026-08-10** |
|---|---|---|
| before | 27 | **31** |
| after | 16 | **18** |
| removed | 18 | **20** |
| written | 7 | **7** ✓ |
| untouched | 9 | **11** |

The seven writes were exactly right, and every rename the deck's diagram shows is
confirmed: `llm.provider`, `llm.model_name`, `llm.token_count.prompt`,
`llm.token_count.completion`, `openinference.span.kind`, `llm.input_messages.*`,
`llm.output_messages.*`. The counts were stale — they came from the older separate
agent, and this response also carried Anthropic thinking content
(`…message_content.signature`), which widens the before-count.

**The eleven survivors, measured:**

```
llm.system                       ← survives remove_originals: true
llm.finish_reason                ← and OTel HAS gen_ai.response.finish_reasons
llm.token_count.total            ← no equivalent written
llm.invocation_parameters
llm.tools.0/1/2.tool.json_schema
input.value / input.mime_type
output.value / output.mime_type
span name: messages.create       ← unchanged; the processor rewrites attributes, not names
```

`llm.finish_reason` is a sharper example than `llm.system`: OTel defines
`gen_ai.response.finish_reasons`, the source attribute is right there, and the
processor still does not map it. Same for `llm.token_count.total`. "Partial
normalization" is not a hedge — it is the measurement.

### Bug this run found

`demos/agent/run.sh` only installed dependencies when `.venv` was absent, so an
existing venv from before `openinference` was added to `requirements.txt` failed with
`ModuleNotFoundError: No module named 'openinference'`. It now reinstalls whenever
`requirements.txt`'s hash changes.

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
