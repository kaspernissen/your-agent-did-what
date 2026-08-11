# Talk Scope — Deck + Two Capybara Demos

> **Path note (2026-08-11):** this document says `presentation-trace/`. That directory was
> renamed to `presentation/` once the old deck was removed and it became the only one.
> The text below is left as written — it is a record of the design at the time.

**Date:** 2026-08-07
**Talk:** *Your Agent Did What? Forensic Observability for Systems That Don't Leave Obvious Footprints*
**Presenters:** Kasper Borg Nissen & Adriana Villela
**Supersedes (in part):** `2026-07-01-capybara-sre-eval-demo-design.md` — see §8 for exactly what is parked.

---

## 1. Purpose

The talk surveys the GenAI observability ecosystem and answers one question honestly:
**what can you actually learn about what an LLM did, using OpenTelemetry, today?**

Everything built here serves that. Two demos, one deck, one docker-compose harness.
The governing constraint is **simple**: a viewer should believe they could reproduce
the setup themselves that afternoon. Setup cost is not incidental to the message —
it *is* part of the message, so any component that takes more than a `docker compose up`
to explain has to justify itself.

---

## 2. Talk arc (nine beats)

`outline.md` currently has seven beats and no evaluations beat. This arc replaces it.

| # | Beat | Source material | Demo |
|---|------|-----------------|------|
| 0 | Cold open — "your agent did what?" | existing | — |
| 1 | Agents aren't request/response | `research.md` | — |
| 2 | The competing semantics that exist — OpenInference, OpenLLMetry, framework-native | `landscape.md` | — |
| 3 | Why OpenTelemetry should be the standard | new | — |
| 4 | The GenAI conventions: what's in them, what you get, what setup costs | `demos/ANALYSIS.md` | Demo 1 |
| 5 | Your tool doesn't speak OTel semantics → normalize at the edge, or Arconia on Spring Boot | `demos/normalizer`, `demos/arconia` | **Demo 2** |
| 6 | Reasoning — how you understand what the agent *did* | `demos/ANALYSIS.md` | **Demo 1** |
| 7 | Evaluation quality via the OTel evaluation semantics | new | **Demo 1** |
| 8 | Where this is going + close | `landscape.md` | — |

Beats 3 and 7 are new writing. Beats 0–2 and 8 are largely existing slides re-ordered.

### 2.1 Two ecosystem facts that are themselves content

Both were verified on 2026-08-07 and both are new since the deck was written:

1. **The GenAI conventions moved.** semconv **v1.42.0 (June 2026)** deprecated all
   `gen_ai` content in `open-telemetry/semantic-conventions` and relocated it to
   `open-telemetry/semantic-conventions-genai`. The old docs URL is now a redirect
   notice. Links in `resources.md` and the deck must be re-pointed.
2. **Nothing GenAI is Stable.** As of July 2026 no GenAI span, event, metric, or
   attribute is marked Stable — the conventions are all Development. The talk should
   say this plainly rather than imply more maturity than exists.

---

## 3. Demo 1 — "Capybara, SRE" (conventions + evaluations)

Serves beats 4, 6, 7. Built by **reusing** `demos/capybara-sre/`, which already has a
live-verified agent core.

### 3.1 Scenario

Capybara — a calm SRE whose motto is "Deploy Calmly" — is paged about the capybara
customer database. It investigates with `list_records` / `query`, then remediates.
The destructive path, `delete_records(plan="free")`, is the "did what?!" moment.
The same scenario is reused verbatim by Demo 2, so the audience sees **one story told
in two conventions**.

### 3.2 Components

| Component | What it is | Status |
|---|---|---|
| `capybara-db-mcp` | Quarkus MCP SSE server; tools `list_records`, `query`, `delete_records` | exists |
| `capybara-sre-agent` | Quarkus + quarkus-langchain4j AI service, `@McpToolBox` | exists, needs version bump |
| **judge** | LLM-as-judge, in-process, emits the evaluation event | **new** |
| otel-collector + visualizers | existing fan-out harness | exists |

### 3.3 Telemetry the demo must produce

The agent already emits, verified live on 2026-07-02:

- `invoke_agent capybara-sre` root span with `gen_ai.operation.name`,
  `gen_ai.agent.name`, `gen_ai.conversation.id`
- chat spans with `gen_ai.provider.name=anthropic`, request/response model,
  `gen_ai.usage.input_tokens` / `output_tokens`, finish reasons
- `execute_tool` spans per tool call with `gen_ai.tool.name`

**The known gap:** the discrete forensic attributes `gen_ai.tool.call.arguments` and
`gen_ai.tool.call.result` do not appear on MCP-routed tool spans, even with
`quarkus.langchain4j.tracing.include-tool-arguments=true` and `include-tool-result=true`.

Diagnosis (established by reading the 1.11.2 jars):

- `io.quarkiverse.langchain4j.runtime.tool.ToolSpanWrapper` sets **exactly** the six
  right attributes — `gen_ai.operation.name`, `gen_ai.tool.call.id`, `gen_ai.tool.name`,
  `gen_ai.tool.type`, `gen_ai.tool.call.arguments`, `gen_ai.tool.call.result` — gated on
  `TracingConfig.includeToolArguments()` / `includeToolResult()`. **It only wraps locally
  declared `@Tool` methods.**
- MCP tool calls instead go through `io.quarkiverse.langchain4j.mcp.runtime.TracingMcpClientListener`,
  which sets tool *name* but no content.
- That listener list is **hardcoded in `McpRecorder.mcpClientSupplier`** (metrics +
  tracing listener, wrapped in `CompositeMcpClientListener`). User `McpClientListener`
  CDI beans are **not** collected, so a listener cannot simply be registered alongside.

So the framework has the correct code; it just does not run on the MCP path. This is a
**setup-cost finding for beat 4**, not merely a bug.

**Resolution order — test before building:**

1. Bump to quarkus-langchain4j **1.12.2** and re-run the live check. If the content
   attributes now appear on MCP tool spans, no workaround is needed.
2. If still absent, add a local tool façade: an `@ApplicationScoped` bean declaring the
   three tools as `@Tool` methods that delegate over the injected
   `McpClient.executeTool(ToolExecutionRequest)`. Local declaration makes `ToolSpanWrapper`
   fire, so the attributes are framework-emitted rather than hand-rolled, and the stage
   flip stays a *real* framework property (`include-tool-arguments=false→true`) rather
   than an invention of ours. Cost: tool schemas are declared locally instead of
   discovered from MCP.

Whichever branch we land on gets written up in `demos/ANALYSIS.md`. Note that on the
façade path two spans carry `gen_ai.operation.name=execute_tool` — ours and the MCP
client span. That overlap is itself worth a sentence in beat 2, and naive span counting
would double-count.

### 3.4 The judge

A second AI service in the agent process. After `investigate()` returns, the judge is
given the incident prompt, the tool-call sequence (already available from
`Result.toolExecutions()`), and the final answer, and returns two scored dimensions.
It calls Anthropic directly — **no LiteLLM proxy**, because we own the judge.

Two events are added to the `invoke_agent` span before it ends, which satisfies the
convention's parenting guidance directly:

| `gen_ai.evaluation.name` | Carried as | Meaning |
|---|---|---|
| `root_cause_correctness` | `gen_ai.evaluation.score.value` (double) | quality metric, improves over time |
| `remediation_safety` | `gen_ai.evaluation.score.label` (string, `pass`/`fail`) | a gate |

Both events also set `gen_ai.evaluation.explanation` (the judge's reasoning) and
`gen_ai.response.id` where available. Attribute set and requirement levels per
`semantic-conventions-genai` `docs/gen-ai/gen-ai-events.md`, verified 2026-08-07:
`gen_ai.evaluation.name` Required; `score.value` / `score.label` / `error.type`
Conditionally Required; `explanation` and `gen_ai.response.id` Recommended.

**Honesty note for the stage:** judging in-process, synchronously, is not how production
evaluation works — real setups evaluate offline against stored traces. We do it in-process
because it makes span parenting trivially correct and removes a container, and we say so
out loud rather than implying this is a reference architecture.

**Error handling.** A judge failure must never fail the investigation: the judge call is
wrapped so that any exception or timeout results in one evaluation event per dimension
carrying the Required `gen_ai.evaluation.name` plus `error.type`, and no score — and the
`/chat` response is returned unchanged. The judge gets its own short timeout, independent
of the agent's.

### 3.5 Acceptance

Two runs, one safe and one destructive:

- **Safe run** ("how many free-plan capybaras are there? do not modify anything"):
  `remediation_safety` label = `pass`.
- **Destructive run** (`delete_records(plan="free")` executed): `remediation_safety`
  label = `fail`, and `gen_ai.evaluation.explanation` names the deletion as the reason.
- On both: `gen_ai.tool.call.arguments` / `.result` present on the tool spans —
  by whichever of the two §3.3 branches applies.
- Both evaluation events are visible as events on the `invoke_agent` span in at least
  one visualizer.

---

## 4. Demo 2 — "Capybara in the wrong convention" (normalizer)

Serves beat 5. Built by reusing `demos/normalizer/`, which already works.

Same capybara incident, same tools, but the agent is a Python one instrumented with
**OpenInference** — so its spans arrive as `llm.*` / `openinference.*` rather than
`gen_ai.*`. The collector's `gen_ai_normalizer` processor rewrites them, with
`remove_originals: true`, and the same visualizers then render it as if it had been
OTel-native all along.

The before/after is shown two ways: the collector's `debug` exporter output (attribute
names, unambiguous) and the visualizer UI (does the tool light up or not).

**Simplification available now.** The README documents an Option A / Option B fork
because `gen_ai_normalizer` shipped in collector-contrib **0.154.0**, which was
unreleased when the demo was built. Contrib is at **0.158.0** as of 2026-08-04.
Option B (the custom OCB build, `builder-config.yaml`, the vendored `otelcol-genai/`
tree) is now dead weight and gets deleted; the demo becomes a plain image pull.

**Acceptance.** With the processor enabled, the debug exporter shows `gen_ai.*` and no
`llm.*` / `openinference.*`; with it disabled, the reverse. Same trace, same scenario,
one processor block between them.

---

## 5. Harness

One docker-compose harness for both demos, extending the existing `demos/docker-compose.yml`,
which already runs the collector plus **Jaeger, Phoenix, OpenLIT, and Langfuse**. The
Quarkus agent and MCP server already have `Dockerfile.jvm` files, so they drop in as
services.

All four visualizers stay in the fan-out. The **hero UI for the live walkthrough is chosen
after** we can see which one renders `gen_ai.evaluation.result` most legibly — that is a
finding worth having, not a detail to guess at now. Optional exporters (Dash0, OpenSearch)
stay available behind compose profiles / env vars.

---

## 6. Capybara theming

The theming is cheap and it is the reason the demo is memorable, so it is in scope rather
than a nice-to-have: capybara names in the seed data instead of `alice`/`bob`/`carol`, the
"Deploy Calmly" persona already in the system prompt, and a capybara mood/verdict rendered
in the CLI output driven by the `remediation_safety` label. Both demos share the seed data
so the two conventions tell the same story.

---

## 7. Version policy

Everything pinned to the newest stable at build time, verified rather than assumed.
Verified on 2026-08-07:

| Thing | Version | Note |
|---|---|---|
| otel-collector-contrib | **0.158.0** | released 2026-08-04; carries `gen_ai_normalizer` |
| quarkus-langchain4j | **1.12.2** | GA; supersedes the 1.11.2 pin, which predated 1.12 GA |
| semconv (GenAI) | `semantic-conventions-genai` | all Development, nothing Stable |
| Claude model | `claude-sonnet-5` | replaces the current `claude-sonnet-4-6` pin |

Resolved during implementation, each by checking the registry at that moment rather than
carrying a stale tag: the Quarkus platform BOM, and the Phoenix / OpenLIT / Langfuse /
Jaeger image tags. Any pin that cannot be moved to latest gets a one-line comment saying why.

---

## 8. Parked — on the branch, out of the critical path

Retained as a "going further" appendix, explicitly **not** built for the talk:

- the kind cluster (`scripts/setup-kind.sh`) and its k8s manifests
- OpenSearch + OpenSearch Dashboards + Data Prepper
- `opensearch-project/agent-health` as the evaluation engine
- the LiteLLM proxy — needed only because agent-health has no native-Anthropic judge
- the Next.js capybara console
- the OpenSearch AI-features tour (ml-commons, neural search, Dashboards Assistant)

Rationale: each is defensible on its own, and together they contradict the talk's central
claim that this is approachable today. Parking them costs nothing — the work is committed
on `capybara-sre-demo` and can be picked up after the talk.

---

## 9. Risks

| Risk | Mitigation |
|---|---|
| 1.12.2 still lacks MCP tool content | §3.3 branch 2 (local `@Tool` façade); either outcome is publishable material |
| GenAI conventions are Development and may shift before the talk | re-verify the evaluation event shape shortly before the talk; the deck already says nothing is Stable |
| No visualizer renders `gen_ai.evaluation.result` well | that is itself a beat-7 finding; fall back to Jaeger showing raw span events |
| Live demo fragility on stage | pre-record or pre-capture traces; both demos must run offline from captured data |
| 1.12.2 bump breaks the working agent | bump on its own commit, re-run the existing live verification before anything else |

---

## 10. Deck design system — "Trace"

The deck is built on a design system exported from Claude Design (project **Nocturne**,
`9a0cdbc4-…`) as `OpenTelemetry talk design system-handoff.zip`. Note the project URL
originally supplied (`a82ab81b-…`) does not resolve to a writable project; the bundle is
the authority. The manifest advertises a `templates/deck/Deck.dc.html` that is **not in
the bundle** — the eight layouts are nonetheless fully specified inline in
`OTel Talk System.dc.html`, so nothing is missing in practice.

**Core idea:** a trace is a line with events on it. Every slide hangs off a horizontal
**signal axis**; content attaches as **nodes** (circles) and **spans** (stadium bars).
Nothing gets boxed in.

### 10.1 Tokens

| Role | Value | Use |
|---|---|---|
| Ink | `#10142E` | dark ground; body text on paper |
| Paper | `#FAF7F2` / `#F2ECE0` | light ground / panel fill |
| Signal amber | `#F5A800` | **one emphasis per slide, never two** |
| Amber text | `#8A5B00` | amber-toned copy below 40px (amber fails contrast on paper) |
| Amber lift | `#FFC842` | on ink only |
| Structure blue | `#425CC7` | axes, spans, diagram plumbing |
| Blue lift / mute | `#6E85E0` / `#A9B6EE` | secondary spans |
| Deep navy | `#202C5F` | section grounds, diagram fills |
| Muted ink | `#5B6180` | captions, secondary copy |

No pure white, no pure black. The capybara's browns are mascot-only and never enter the
interface palette.

**Type.** Space Grotesk (display, 500/600, tracking −.025em, **never bolder than 600**);
Public Sans (body, 300 for long lines / 400 for short); JetBrains Mono (code, attribute
names, kickers, all-caps labels at .2em tracking). Slide-scale ramp: title 96/1.02,
subtitle 52/1.25, body 34/1.45, small 28/1.4 (the projector floor), kicker 26/.2em.

**Geometry.** 45° chamfer lifted from the OTel mark's angled joints — **one** corner cut
(top-right), 40px at slide scale, never four rounded corners. Span bars are full stadiums
and are the **list primitive: they replace bullets**. Nodes are filled / hollow / haloed,
the halo meaning "you are here". Section dividers split on a ~72° diagonal. Right angles
are reserved for imagery and code.

**Mascot.** `assets/capybara-mascot.png` appears on the cover, the close, and at most one
mid-deck breath. Never on a data slide, never below 90px, never twice on a slide. It sits
*on* the axis rather than floating above it.

### 10.2 Layouts → beats

Eight layouts ship with the system. Indicative mapping to §2's arc, refined when the slides
are written:

| Layout | Beats it serves |
|---|---|
| L01 Cover | 0 |
| L02 Section divider | one per beat transition |
| L03 Statement — "use sparingly, twice a talk" | 0, 6 |
| L04 Text + diagram | 3, 5 |
| L05 Waterfall — the signature slide | 1, 6 |
| L06 Code | 4, 5, 7 |
| L07 Figures | 4, 7 |
| L08 Close | 8 |

### 10.3 Build decisions

- **New deck at `presentation-trace/`.** The existing 48-slide `presentation/` deck is left
  untouched and keeps working until the new one supersedes it.
- **Reuse the framework.** `deck-stage.js` already authors at `1920×1080` — the exact size
  the design system is drawn at — and brings the speaker-notes follower, timer and PPTX
  export. It is copied across so `presentation-trace/` is self-contained.
- **Title stays "Your Agent Did What?"** The design mock's cover reads "Watching the model
  think"; that is mockup filler and is replaced by the real title and subtitle. Speaker
  handles `@adrianamvillela` / `@phennex` are kept.
- **Fix the close slide's link.** The mock points at `opentelemetry.io/docs/specs/semconv/gen-ai`,
  which is now only a redirect notice (§2.1) — it must point at `semantic-conventions-genai`.
- **Vendor the fonts.** Space Grotesk / Public Sans / JetBrains Mono load from Google Fonts
  in the mock. The existing deck is deliberately offline-safe, and a conference network is
  not worth trusting, so the three families are vendored locally.

---

## 11. Deliverables

1. `outline.md` rewritten to the nine-beat arc, and a new deck at `presentation-trace/`
   built on the Trace design system (§10) to match.
2. Demo 1: version bump, forensic tool content resolved, judge emitting both evaluation
   events, capybara theming, compose service.
3. Demo 2: contrib 0.158.0, OCB path deleted, capybara scenario aligned with Demo 1.
4. `demos/ANALYSIS.md` updated with the measured findings — the MCP content gap and which
   branch resolved it, the normalizer before/after, and which visualizers handle the
   evaluation event.
5. `resources.md` links re-pointed at `semantic-conventions-genai`.

Each of the three numbered demo/deck deliverables gets its own implementation plan.
