# Your Agent Did What? — 30-Minute Presentation Outline

**Full title:** *Your Agent Did What? Forensic Observability for Systems That Don't Leave Obvious Footprints*
**Length:** 30 minutes (≈26 min content + 4 min buffer/Q&A handoff)
**Presenters:** Kasper Borg Nissen + Adriana Villela (duo handoffs marked ⟳ — optional)
**Spine of the talk:** *observing an agent is not like observing a request.* Every section returns to one contrast — what changes when the thing you're tracing reasons, decides, and acts on its own.

> **Visual direction (for when this becomes slides):** keep the **dark background** from Kasper's PlatformCon template, but recolor the red/orange accents to **blue → purple**. **No Dash0 logo.** (The reference repo `platform-engineers-guide-to-observability` is a *book* project, not a slide framework — so the deck needs to be built in a slide tool; see the note at the end.) Source decks to lift visuals from are cited per slide as **[PC]** = PlatformCon 2026, **[KC]** = KubeCon/Dapr "Taming Complexity", **[demo]** = our `demos/ANALYSIS.md`.

---

## Arc at a glance (timing)

| # | Section | Time | The "different from req/response" beat |
|---|---|---|---|
| 0 | Cold open — the 3am page | 1.5 | You can't read a stack trace for a decision |
| 1 | Agents aren't request/response | 4 | The 4 properties; the contrast table |
| 2 | What that does to your traces | 5 | Context breaks; signal is buried; skills break traces |
| 3 | The fragmentation problem | 6 | 5 conventions for one span; measured drift |
| 4 | Bridging the gap (normalize at the edge) | 5 | genai_normalizer + Arconia, live |
| 5 | The forensics payoff | 5.5 | Reconstructing *why* is the new MTTR |
| 6 | Where this is going + close | 3 | OTel is the substrate; call to action |

---

## 0 · Cold open — "Your agent did what?" (1.5 min)

- **Slide:** title over the dark/blue-purple background. **[PC]** title style, recolored.
- **Hook:** "It's 02:47. An agent rolled back a deployment — then deleted rows from a production database. The incident is over. The next morning, someone asks the only question that matters: *why did it do that?* You open your telemetry. What's actually there?"
- Plant the promise: by the end you'll know (a) why agent telemetry is different, (b) why the ecosystem is fragmented and where it's converging, and (c) what your traces must capture to answer "why" — demonstrated with real data.
- ⟳ intro both presenters in one line each.

---

## 1 · Agents aren't request/response (4 min)

The conceptual core. Establish the contrast before any tooling.

- **Slide 1.1 — Evolution of architectures.** Monolith → microservices → event-driven → **agent-based**. Each step solved a problem and added complexity; building got easier, *understanding* got harder. **[KC]** "Evolution of architectures" + **[PC]** cognitive-load curve.
- **Slide 1.2 — Four properties we've never operated against.** **[PC]** "AI workloads aren't like anything we've operated":
  1. **Non-determinism** — same input, different output. Re-running doesn't reproduce the bug.
  2. **Dynamic tool use** — the call graph is *generated at runtime*, not declared. Every tool is a caller that never read your API docs.
  3. **Token economics, not RPS** — a single bad prompt can balloon spend 100×.
  4. **Opaque decisions** — there's no stack trace for *why*; the reasoning happened inside a model you don't own.
- **Slide 1.3 — Every familiar signal has a new equivalent (THE table).** **[PC]** "Every familiar signal has a new equivalent":
  | Request/response world | Agent world |
  |---|---|
  | Stack trace | Reasoning chain |
  | Status code (2xx/5xx) | Quality signal (hallucination, confidence, eval) |
  | RPS & latency | Tokens, cost, blast radius |
  | Static call graph | Dynamic tool invocation (MCP, local/remote) |
  | Replayable request | Non-deterministic run |
  - Land it: "The old practice wasn't wrong. It was right for its time. We just have to build the equivalents for this new class of system."
- **Slide 1.4 — New execution patterns / new boundaries.** **[KC]** "A new landscape": LLM reasoning loops, tool invocation (local vs remote MCP), skill execution (scripts/services), agent-to-agent (A2A). One line each on MCP (Anthropic, Nov '24 — tool registry for models), A2A (Google, Apr '25 — agent discovery/collab), Skills (agentskills.io, Dec '25 — lightweight `SKILL.md` + scripts). **The point:** each is a *new execution boundary* — and every boundary is a place a trace can break.

---

## 2 · What that does to your traces (5 min)

From concept to the actual telemetry. This is the "don't leave obvious footprints" section.

- **Slide 2.1 — Why this is hard to observe.** **[KC]** 5-card slide: traditional tracing assumes linear req/response; context propagation breaks between agents/tools/models; decisions are dynamic & non-deterministic; execution spans many systems (LLMs, APIs, MCP, skills); key context lives *outside* the runtime (prompts, reasoning).
- **Slide 2.2 — A shared pain: context gets lost.** **[KC]** context-propagation diagram (good vs broken) + W3C Trace Context (`traceparent`). Async transports (events, gRPC, sockets) make propagation harder → disconnected traces → "everyone's looking at a different piece of the puzzle."
- **Slide 2.3 — The trace of one pizza order (the demo trace).** **[KC]** screenshot. **~275 spans, ~48s, 10 agents/services** for *one order*. The agent system (Dapr + Diagrid + langchain4j) is real. "A single order becomes a complete story of what happened inside the system."
- **Slide 2.4 — But: more telemetry ≠ better telemetry.** **[KC]** Of 275 spans, many are infra/retries/polling; **164 named just `POST`/`GET`**. The one span you want is buried. **Goal: meaningful spans, not more spans. Extracting the signal is the frontier.**
- **Slide 2.5 — Skills break traces (the concrete boundary).** **[KC]** "What about skills": skills are shell scripts/subprocesses — *not instrumented, don't propagate context.* We had to manually bridge `TRACEPARENT` into bash + `curl` to keep the trace alive. "New execution boundaries create new observability challenges." → This is the bridge into "so what do we actually capture, and can the tools agree on it?"

---

## 3 · The fragmentation problem (6 min)

The first half of the abstract. Now grounded in measured data from our demos.

- **Slide 3.1 — One vocabulary? Not yet.** **[PC]** "Five conventions for the same span": OTel GenAI SemConv, OpenInference (Arize), OpenLLMetry (Traceloop), LangSmith, Langfuse. Same model call = `gen_ai.request.model` in one, `llm.model_name` in another. Credit Salaboy: **legitimate differences, not naming preferences** — each optimizes for something (vendor neutrality / eval workflows / dev ergonomics / framework). Not going away soon.
- **Slide 3.2 — What OTel GenAI semconv actually gives you.** **[PC]** "One vocabulary": `gen_ai.operation.name`, `gen_ai.provider.name`, `gen_ai.request.model`, token usage, finish reasons, tool calls; `execute_tool`/`invoke_agent`/`chat` spans. The shared starting line.
- **Slide 3.3 — Measured drift (NEW — our data).** **[demo]** The honest, original contribution. We ran *one* fake-database agent through multiple stacks and captured the real attributes:
  - OpenLIT Python SDK → `gen_ai.provider.name` (**current** spec) + ~8 non-standard extensions (cost, cache tokens, `time_to_first_token`, `gen_ai.tool.args`).
  - Arconia/Spring AI, `opentelemetry` flavor → `gen_ai.provider.name`; **but `openlit`/`openllmetry` flavor → `gen_ai.system` (deprecated)** + OpenLLMetry adds `traceloop.*`.
  - **Punchline:** two tools, same week, both "OTel GenAI semconv" — one emits the current provider key, the other the deprecated one. *"Conforms to OTel GenAI" is necessary but not sufficient — which revision/flavor matters.*
- **Slide 3.4 — Same trace, different viewers (the backend spectrum).** **[demo]** We fanned one trace out to Jaeger / Phoenix / OpenLIT / Langfuse:
  - **Jaeger** (generic): shows it as plumbing — `chat …`, `execute_tool …`, raw tags. No GenAI awareness.
  - **Phoenix** (GenAI-native, but **OpenInference-native**): accepts our `gen_ai.*` spans but renders them as **plain spans** — fragmentation made visible, on stage.
  - **OpenLIT / Langfuse** (OTel-semconv-aware): light up — tokens, cost, model.
  - "Same bytes. The viewer decides whether it's legible."

---

## 4 · Bridging the gap — normalize at the edge (5 min)

The "realistic path to OTel-native" the abstract promises. Two live answers.

- **Slide 4.1 — The platform answer: normalize at the edge.** **[PC]** Developers instrument with whatever their framework emits; the *platform* canonicalizes centrally. Two tools you can use today.
- **Slide 4.2 — `gen_ai_normalizer` (collector-side) — live before/after.** **[demo]** OpenInference-instrumented app → collector running `gen_ai_normalizer` → OTel `gen_ai.*`. Real captured rewrite:
  - `llm.model_name` → `gen_ai.request.model`; `llm.token_count.prompt` → `gen_ai.usage.input_tokens`; `openinference.span.kind (LLM)` → `gen_ai.operation.name (chat)`.
  - **Honest caveat (our finding):** it normalizes the *scalar* attributes you group/cost/route on, but **leaves message bodies** (`llm.input_messages.*`, `input.value`, tool schemas) untouched → **partial normalization.** Good for dashboards/cost; not a full end-to-end translation.
  - Status: merged, **alpha**, traces-only; **not in the released contrib image yet** (we built it with `ocb`); working toward donation — **contrib issue #46069**. Raise it now, at the right moment.
- **Slide 4.3 — Arconia (SDK-side) — one property.** **[demo]** Spring AI app; flip `arconia.observations.conventions.opentelemetry.ai.flavor` → `opentelemetry` / `openlit` / `openllmetry` / `langsmith` and the same spans re-emit under that convention — verified live. (Lesson we learned the hard way: needs the `arconia-opentelemetry-`**`ai`**`-semantic-conventions` artifact.) Collector fixes it downstream for any language; Arconia fixes it upstream for Spring shops. Both target OTel semconv.
- **Slide 4.4 — Without conventions, correlation fails.** **[PC]** the three-line wall: *Without conventions, correlation fails. Without correlation, AI guesses. With structure and context, AI reasons.* Conventions are what turn raw telemetry into something an LLM (or a human at 3am) can reason over.

---

## 5 · The forensics payoff (5.5 min)

Return to the cold open. The second, "nobody's-talking-about-it" half of the abstract.

- **Slide 5.1 — Reconstructing "why" is the new MTTR.** **[PC]** "You're not debugging anymore. You're interrogating a system you can't replay." The on-call questions: *What telemetry did the agent read? Which tools did it call? What did the model return? Did anything change after?*
- **Slide 5.2 — Agent reasoning, captured as a span.** **[KC]** the real GenAI-semconv span: `gen_ai.request.model`, `gen_ai.prompt = "You are a pizza cooking agent…"`, `gen_ai.completion = "I'll cook one Pepperoni pizza… STEP 1: acquire ingredients"`, token usage. "The trace doesn't just show service calls — it shows the *reasoning step*."
- **Slide 5.3 — The forensic content is a switch you have to throw (NEW — our data + research).** **[demo]** Our `execute_tool delete_records` span carried `gen_ai.tool.call.arguments = {"plan":"free"}` and `gen_ai.tool.call.result = {"deleted":2,"remaining":1}`. **But those two attributes are opt-in / off by default in the OTel spec.** Default instrumentation proves a tool *ran*; only the opt-in proves *what it did*. **That single choice is the difference between a footprint and an empty footprint.**
- **Slide 5.4 — What's still missing (be honest).** From the research: **no schema-level decision-provenance primitive** (only a reasoning-token count) across OTel/LangSmith/Langfuse/Datadog; **you can't faithfully replay** (context window isn't persisted; non-determinism diverges the rerun) → *reasoning must be captured at execution time or it's gone forever.* And don't trust the model's own chain-of-thought as the audit trail. This is the gap the talk names for the SIG.
- **Slide 5.5 — Skills/A2A: the boundaries where "why" leaks out.** Tie back to 2.5 — the places context (and therefore "why") is most likely to be lost are exactly the new agent boundaries. Forensics = keeping the thread alive across them.

---

## 6 · Where this is going + close (3 min)

- **Slide 6.1 — OTel is the substrate (external proof).** Jaeger v2 is **rebuilt on the OpenTelemetry Collector** ("natively understands OTLP end to end, no translation layers"; v1 EOL'd 2025-12-31). Even the 10-year-old tracing project now runs *on* OTel. Its roadmap puts GenAI features (PII redaction, payload tiering) **in the collector pipeline**, and an LLM trace-investigation agent in the UI. **[from `landscape.md`]**
- **Slide 6.2 — A maturity model for OTel GenAI support.** **[KC]** Levels 0–3 (Instrumented → Aligned → Native → Optimized); descriptive, not a score. Community issue **#3247**. Where are *you*?
- **Slide 6.3 — The ecosystem is already building on it.** kagent, HolmesGPT, agentgateway, k8sgpt — agents observing agents, reading OTel data over MCP. **[PC]**
- **Slide 6.4 — Call to action / takeaways.**
  1. **Instrument every layer** (agent runtime, gateway, MCP, inference) — none gets a pass.
  2. **Adopt OTel GenAI semconv now** — and turn on the opt-in forensic content deliberately.
  3. **Normalize at the edge** (genai_normalizer / Arconia) — and contribute to #46069 + the SIG.
  4. **Govern agents like services** — identity, policy, cost, observability.
  - Closing line: *"Your agent will do something you didn't expect. The only question is whether your telemetry can tell you why. Build the footprints before you need them."*
- **Slide 6.5 — Thank you / get in touch.** QR + handles. **[KC]/[PC]** closing style, recolored, no Dash0 logo.

---

## Reusable-assets map (so building the deck is fast)

| Need | Source slide |
|---|---|
| Title / closing / section dividers (dark bg) | **[PC]** — recolor red/orange → blue/purple |
| Evolution of architectures | **[KC]** |
| 4 properties; signal-equivalents table; "correlation fails" wall; 5-conventions; "one vocabulary"; AI-SRE | **[PC]** |
| Why-hard-to-observe; context-loss; W3C trace context; pizza trace; more≠better; skills-break-traces; reasoning span; maturity model | **[KC]** |
| Measured attribute drift; backend-spectrum renderings; normalizer before/after; Arconia flavor diff; forensic opt-in span | **[demo]** `demos/ANALYSIS.md` |
| Jaeger-on-collector quotes; normalization framing | `landscape.md` |

## Open decisions before building slides
1. **Slide tool** — the reference repo is a book, not a deck. Recommend **Marp** (markdown + custom CSS theme; fits this markdown repo, easy dark blue/purple theme, no logo) or **reveal.js**. Which?
2. **Solo vs duo** — keep Adriana handoffs, or collapse to one voice?
3. **Live demo vs recorded** — sections 3–5 can run the actual `demos/` harness live, or use captured screenshots from `ANALYSIS.md`. Live is riskier (heavy stacks); recommend pre-recorded clips + the captured attribute blocks.
