# Your Agent Did What? — 30-Minute Presentation Outline

**Full title:** *Your Agent Did What? Forensic Observability for Systems That Don't Leave Obvious Footprints*
**Length:** **30–35 minutes** (the speakers' working range, confirmed 2026-08-09), nine beats, **49 slides**.
**Presenters:** Kasper Borg Nissen (`@phennex`) + Adriana Villela (`@adrianamvillela`)
**Question the talk answers:** *what can you actually learn about what an LLM did, using OpenTelemetry, today — and how hard is it to set up?* (spec §1)
**Spine:** one capybara incident, told twice in two conventions, with every claim measured rather than asserted.

> **Deck:** built at `presentation-trace/` on the **Trace** design system (spec §10). A trace is a line with events on it: every slide hangs off a horizontal signal axis, content attaches as nodes and span bars, span bars replace bullets, nothing gets boxed in. **One amber emphasis per slide — named below for every slide.** The mascot appears at full size three times (cover, one mid-deck breath, close) and as a persistent 96px footer presence on every non-divider slide — see `presentation-trace/LAYOUTS.md`.
>
> Source tags used per slide: **[PC]** = the previous deck, removed 2026-08-10 (see below), **[KC]** = KubeCon/Dapr "Taming Complexity" deck, **[D1]** = Demo 1 "Capybara, SRE", **[D2]** = Demo 2 "Capybara in the wrong convention", **[ANALYSIS]** = `demos/ANALYSIS.md`, **[R-F]** = `research.md` (forensics), **[R-E]** = `research-evaluations.md`, **[LS]** = `landscape.md`, **[SPEC]** = the talk-scope spec.
>
> **The two external tags are not equally available, and the difference matters when building slides.**
> - **[PC] is no longer in this repo.** The previous 48-slide deck at `presentation/` was the source for the material lifted into beats 0–3 — "Opaque decisions", "Five conventions for the same span" with its five provider/attribute pairs, and the "Without conventions, correlation fails" wall. That lift is complete and the deck has since diverged well beyond it, so `presentation/` was removed on 2026-08-10; recover it from git history if you ever need the original wording. The `[PC]` tags below record where a slide came from, not a file to go and read.
> - **[KC] is not in this repo.** "Taming Complexity", "Evolution of architectures" and the cognitive-load curve could not be located anywhere in the repository. Those slides are **external speaker material Kasper must supply**, or they get redrawn from scratch.

---

## Arc at a glance (timing)

| # | Beat | Time | Leads | The one thing it must land |
|---|---|---|---|---|
| 0 | Cold open + who we are | 4 | Kasper | The incident is over; the only question left is *why* |
| 1 | Agents aren't request/response | 5.5 | Adriana | An agent is a loop; the call graph is generated at runtime and the decision is not in it |
| 2 | The competing semantics that exist | 4 | Adriana | Five conventions, one span — and we measured how far apart they are |
| 3 | Why OpenTelemetry should be the standard | 3 | Kasper | Everyone is already normalizing *toward* `gen_ai.*` |
| 4 | The conventions: what you get, what setup costs | 5.5 | Kasper | Real vocabulary, moved repo, nothing Stable, and setup bites |
| 5 | Your tool doesn't speak OTel? Normalize at the edge | 4 | Adriana | Two places to fix it, and exactly how far each gets you |
| 6 | Reasoning — what did the agent actually do? | 4 | Kasper | Default instrumentation proves a tool ran, not what it did |
| 7 | Evaluation quality via the OTel evaluation semantics | 4 | Adriana | OTel already carries "was it good?" — as an event, at Development |
| 8 | Where this is going + close | 3 | Both | Even the ten-year-old tracer now runs on the Collector |
| | **Total** | **~37 — over the 30–35 target; expanding first by agreement, cut list parked below** | | |

**Cut list — parked, not actioned.** The deck is deliberately in an *expand first, cut later*
phase: material is being added while the argument is still settling, and trimming waits until
the full picture is on the table. Beat 1 grew from 4 to 5.5 min when 1.3 (the vocabulary) and
1.4 (the telemetry path) were added, which puts the total at the top of the range. When it is
time to cut, these are the candidates in order — recorded now, while the reasoning is fresh:

1. **2.4 — "Both of these claim to be OTel GenAI"** (the Arconia `flavor` slide). It is the only
   slide where Arconia carries an argument rather than getting a mention, which is more prominence
   than intended, and it argues drift *within* one convention while its beat is about fragmentation
   *across* conventions. Its insight — a tool can claim conformance and still emit deprecated keys —
   survives as a spoken line on 4.3 ("Stable: zero"). Saves ~45s.
2. **1.2 — the architecture run-up** (monolith → microservices → event-driven → agent-based). Now
   that 1.3 defines an agent directly, the run-up is the more cuttable of the two. Saves ~45s.

Cutting either brings the total back under 35. Neither is cut today.

Since that list was written the deck has gained 1.3, 1.4, 4.2, 6.4 and 7.2 — all orientation
or setup material — and lost the Arconia flavor slide, putting it at ~36. That is over target
and deliberate: the argument is still settling, and it is easier to cut from a complete deck
than to discover a hole on stage. Trim before the first rehearsal, not before then.

Handoffs happen on the section dividers, which is why every beat except the close opens with one.

---

## 0 · Cold open — "your agent did what?" (4 min) — **Kasper**

**Message:** An agent deleted rows in production, the incident is already over, and the only question anyone actually cares about the next morning is *why did it do that?*

### 0.1 — Cover
- **Layout:** L01 Cover
- **Headline:** Your Agent Did What?
- **Sub:** Forensic Observability for Systems That Don't Leave Obvious Footprints · `@phennex` · `@adrianamvillela`
- **Amber emphasis:** the words **"Did What?"** in the title
- **Mascot:** yes — sitting *on* the axis, not floating
- **Source:** existing [PC] title slide, retitled per [SPEC] §10.3 (the mock's "Watching the model think" is filler and is replaced)

### 0.2 — Who?
- **Layout:** L07 Figures (navy ground, deep cards)
- **Headline:** Who?
- **Content:** both speakers on `--ink` cards over a `--navy` ground — circular portrait, then name / title / employer mark beside it, credentials below. Adriana: Principal Developer Advocate at Dynatrace, CNCF + AAIF Ambassador, OpenTelemetry Community Manager, End User SIG maintainer, Geeking Out podcast. Kasper: Director of Developer Relations at Dash0, CNCF + AAIF Ambassador, Golden Kubestronaut, author *OpenTelemetry for Dummies*, former KubeCon+CloudNativeCon EU & NA Co-Chair, Cloud Native Nordics.
- **Amber emphasis:** the **lead speaker's portrait ring** — mirrors the cover, where the first speaker is the amber node
- **Source:** speakers. **Say the capybara line out loud** (it is in the speaker note, not on the slide): Adriana loves capybaras, which is why one is asleep on the last slide and why the demo agent is called Capybara.

### 0.3 — Agents are becoming the front door to your platform
- **Layout:** L07 Figures (three cards)
- **Headline:** Agents are becoming the **front door** to your platform
- **Content:** where this is already happening, before any incident lands — **in the portal** (platform teams ship an agent beside the service catalogue; developers ask about their own systems in plain language instead of learning another dashboard) · **in the incident channel** (summarise the trace, correlate the deploy, propose the rollback, on live systems during the incident) · **in CI and the terminal** (coding agents with repository access and a shell, already running against real infrastructure).
- **Amber emphasis:** **"front door"** in the headline
- **Source:** new writing — the platform-engineering framing the room lives in
- **Land it:** "None of these are demos. They hold credentials, they read production data, and increasingly they act on it. Platform teams are shipping these as products; the observability problem arrives with them whether anyone planned for it or not."
- **Careful:** no vendors or product names here — kagent, HolmesGPT and the coding agents have their own slides in beat 8, and naming them now spends that payoff early.
- **Why it exists:** the deck went from "who we are" straight to "your agent deleted a database", which asks the room to care about a problem before establishing that the thing causing it is already in their stack. This is the slow start that earns the incident.

### 0.4 — Two ways you meet an agent
- **Layout:** L04 Text + diagram (two chamfered cards)
- **Headline:** You either build one, or you run someone else's
- **Content:** *You build it* — LangChain, LangGraph, Spring AI, LangChain4j; you choose the framework, so you choose what it emits; your problem is which convention and what it leaves out. *You run someone else's* — kagent, HolmesGPT, k8sgpt, Copilots in your tooling; you did not choose the instrumentation. **Two problems, not one:** it *reads* your telemetry, so it is only as good as what it reads — and it *acts* on your systems, so you need its telemetry too.
- **Amber emphasis:** **"you need its telemetry too"**
- **Source:** new, 2026-08-09. This slide exists because the instrumentation ecosystem the talk surveys is developer-facing while the demo is an SRE incident; without it the room cannot tell which of them the talk is for. Pays off at 8.3.

### 0.5 — The morning after
- **Layout:** L03 Statement
- **Headline:** "It deleted the rows. The incident is over. Now prove **why**."
- **Amber emphasis:** the single word **"why"**
- **Source:** the cold-open hook in the previous outline (§0) + `abstract.md` ¶3 ("your agent just deleted a database. What does your telemetry actually tell you?")
- **Note:** this is one of only two statement slides in the deck — the layout is documented as "use sparingly, twice a talk" ([SPEC] §10.2). The other is 6.4.

---

## 1 · Agents aren't request/response (5.5 min) — **Adriana**

**Message:** An agent's execution is a call graph generated at runtime by a non-deterministic process, and the artifact you most need — the decision — is not a thing your request/response instincts know how to capture.

### 1.1 — Divider
- **Layout:** L02 Section divider
- **Headline:** Agents aren't request/response
- **Amber emphasis:** the beat kicker `01 / 08`
- **Source:** design system; speaker handoff point (Kasper → Adriana)

### 1.2 — We keep changing what we have to understand
- **Layout:** L04 Text + diagram
- **Headline:** Monolith → microservices → event-driven → **agent-based**
- **Amber emphasis:** the final **agent-based** node on the axis
- **Source:** [KC] "Evolution of architectures" (salvageable as-is, recolored) — **[KC] specifically is external speaker material with no copy in this repo; Kasper must supply it or the slide gets redrawn from scratch.** (This is a [KC] problem, not a general one — [PC] slides *are* in the previous deck; see the source-tag note at the top.) Each step solved a problem and added complexity: building got easier, *understanding* got harder.

### 1.3 — An agent is a loop around a model that can call your tools
- **Layout:** L07 Figures (four cards in a row, arrows between)
- **Headline:** An agent is a **loop around a model** that can call your tools
- **Content:** the vocabulary defined once, on the demo's own parts — **agent** (the loop; keeps calling the model until it decides it is done) · **model** (picks the next step; billed per token in and out) · **MCP server** (how an agent is handed tools it did not ship with) · **tools** (the functions it can actually run against your systems). A dashed bracket under model→MCP→tools carries "↺ the agent decides how many times round".
- **Amber emphasis:** **"loop around a model"** in the headline
- **Source:** [D1] — the parts are Capybara's real ones, so beat 4's "Meet Capybara, SRE" is this diagram made concrete
- **Land it:** "Only two of these are yours: the prompt, and the list of tools you handed it. How many model calls, which tools, in what order — decided at runtime. Which means you cannot read the path off the code. You have to observe it."
- **Why it exists:** the deck showed *spans* (1.6) before it ever showed the room the loop those spans describe, and an SRE audience running someone else's agent may never have had *agent* / *MCP server* / *token* defined out loud.

### 1.4 — Nothing in this path is GenAI-specific
- **Layout:** L07 Figures (three panels, arrows between)
- **Headline:** Nothing in this path is **GenAI-specific**
- **Content:** the path the spans actually take, on the demo stack — **in your process** (`quarkus-langchain4j` auto instrumentation · `InvestigationResource` hand-written spans · MCP client tool-call spans) → **OTLP**, gRPC 4317 / HTTP 4318 → **collector** (receivers `otlp` · processors `gen_ai_normalizer` · exporters `otlp` + `debug`) → **backends** (Jaeger, OpenLIT, your vendor).
- **Amber emphasis:** **"GenAI-specific"** in the headline
- **Source:** [D1] + [D2] — this is literally both demos' pipeline
- **Land it:** "One wire format the whole way, and your agent does not know what is downstream — which is why the middle can rewrite its attributes without touching a line of application code. Same collector, same pipeline, same backends you already run for everything else."
- **Why it exists:** 1.6's waterfall used to appear with no account of how those spans got out of the process; this also plants the collector-as-control-point that beat 3 argues and beat 5 demonstrates.

### 1.5 — Four properties we've never operated against
- **Layout:** L04 Text + diagram
- **Headline:** Four properties we've never operated against
- **Content:** non-determinism (re-running doesn't reproduce the bug) · the call graph is *generated at runtime*, not declared · token economics, not RPS · **opaque decisions — there is no stack trace for *why***
- **Amber emphasis:** **"opaque decisions"**
- **Source:** [PC] "AI workloads aren't like anything we've operated"; property 4 is the one [R-F] turns into a concrete schema gap in beat 6

### 1.6 — Every familiar signal has a new equivalent
- **Layout:** L07 Figures
- **Headline:** Every familiar signal has a new equivalent
- **Content (paired figures):** stack trace → reasoning chain · status code → quality signal · RPS & latency → tokens, cost, blast radius · static call graph → dynamic tool invocation · replayable request → non-deterministic run
- **Amber emphasis:** **"reasoning chain"** (the pair the rest of the talk chases)
- **Source:** [PC] "Every familiar signal has a new equivalent" table — salvageable, re-laid-out as figure pairs rather than a table (the system has no table primitive)
- **Land it:** "The old practice wasn't wrong. It was right for its time. We have to build the equivalents."

### 1.7 — What one agent run actually looks like
- **Layout:** L05 Waterfall
- **Headline:** One run, four kinds of span
- **Content:** `invoke_agent` (Internal, root) → `chat <model>` (Client) → `execute_tool` (Internal) → `POST` (Client, pure plumbing to the model API)
- **Amber emphasis:** the **`POST`** row — emitted automatically, carrying no GenAI meaning
- **Source:** [ANALYSIS] Demo 1 "Span structure actually produced". The signature layout of the system; it returns in beat 6 carrying the incident.

---

## 2 · The competing semantics that exist (4 min) — **Adriana**

**Message:** OpenInference, OpenLLMetry and the framework-native conventions describe the same span with different names for legitimate reasons — and we measured how far apart they actually are, which is both further and nearer than people assume.

### 2.1 — Divider
- **Layout:** L02 Section divider
- **Headline:** Five conventions, one span
- **Amber emphasis:** the beat kicker `02 / 08`
- **Source:** design system

### 2.2 — Same model call, five vocabularies
- **Layout:** L04 Text + diagram
- **Headline:** One model call. Five names for the model.
- **Content:** OTel GenAI semconv · OpenInference (Arize) · OpenLLMetry (Traceloop) · LangSmith · Langfuse. `gen_ai.request.model` in one, `llm.model_name` in another.
- **Amber emphasis:** the attribute chip **`llm.model_name`**
- **Source:** [LS] §2 opening; [PC] "Five conventions for the same span" — salvageable

### 2.3 — These are legitimate differences, not naming preferences
- **Layout:** L07 Figures
- **Headline:** Legitimate differences, not naming preferences
- **Content:** each one optimizes for something — OTel GenAI **vendor-neutral** · OpenInference **eval workflows** · OpenLLMetry **dev ergonomics** · LangSmith **LangChain-native** · Langfuse **maps the others in**. Credit Salaboy. They are not going away soon.
- **Amber emphasis:** **"legitimate differences"** in the headline
- **Source:** [LS] §2 (Salaboy's framing, stated verbatim there) for "legitimate differences, not naming preferences". The per-tool attribution is **[PC]** the previous deck, where each of the five cards already carries its optimization label verbatim alongside its provider attribute — lift the pairs from there rather than restating them.

### 2.4 — Measured: the provider key alone fragments three ways
- **Layout:** L06 Code
- **Headline:** Both of these claim to be OTel GenAI
- **Content:** OpenLIT Python SDK → `gen_ai.provider.name` (current spec). Arconia/Spring AI with `flavor=opentelemetry` → `gen_ai.provider.name`; with `flavor=openlit` or `openllmetry` → **`gen_ai.system`** (deprecated). Same code, one property apart.
- **Amber emphasis:** **`gen_ai.system`** — the deprecated key
- **Source:** [ANALYSIS] cross-cutting finding #2, observed from a collector `debug` exporter. Punchline: *"conforms to OTel GenAI" is necessary but not sufficient — which revision matters.*

### 2.5 — Same bytes. The viewer decides whether it's legible.
- **Layout:** L04 Text + diagram
- **Headline:** Same bytes, four renderings
- **Content:** Jaeger (generic) shows plumbing — raw tags · Phoenix is GenAI-native but **OpenInference-native**: it accepts `gen_ai.*` spans and renders them as **plain spans** · OpenLIT and Langfuse light up with tokens, cost, model.
- **Amber emphasis:** Phoenix's **"plain spans"** — the fragmentation tax, visible on stage
- **Source:** [LS] §1 (backend spectrum, Phoenix "Translating Conventions" docs) + [ANALYSIS] backend rendering matrix. **Honesty:** Jaeger arrival was API-confirmed; Phoenix/Langfuse renderings are from documentation, not captured screenshots ([ANALYSIS] "What we did NOT verify") — say so, or capture them before the talk.

---

## 3 · Why OpenTelemetry should be the standard (3 min) — **Kasper**

**Message:** OTel is the only one of the five you can converge on without also picking a vendor — and the measured evidence is that three independent stacks already emit its vocabulary.

*This beat is new writing ([SPEC] §2). Its factual spine is [ANALYSIS] cross-cutting #1 and [LS] §2; the argumentative parts are flagged below.*

### 3.1 — Divider
- **Layout:** L02 Section divider
- **Headline:** Why OpenTelemetry should be the standard
- **Amber emphasis:** the beat kicker `03 / 08`
- **Source:** design system; handoff Adriana → Kasper

### 3.2 — Three independent stacks, one vocabulary
- **Layout:** L07 Figures
- **Headline:** They already agree more than they admit
- **Content:** OpenLIT (Python SDK) → `gen_ai.*` · Spring AI + Arconia (Java) → `gen_ai.*` · `gen_ai_normalizer` output → `gen_ai.*`. The shared vocabulary is real, not aspirational — for the core dimensions.
- **Amber emphasis:** the shared target **`gen_ai.*`**
- **Source:** [ANALYSIS] cross-cutting finding #1, measured across all three demos

### 3.3 — An agent incident is also a database incident
- **Layout:** L04 Text + diagram
- **Headline:** Agent telemetry is not a separate telemetry system
- **Content:** the capybara incident is a *database* incident with an LLM in front of it. A GenAI-only convention gives you a GenAI-only island; the span you need next is the SQL span, the pod restart, the deploy. **One correlation domain, not two.**
- **Amber emphasis:** **"one correlation domain"** — the closing line of the content
- **Source:** [PC] "Without conventions, correlation fails / Without correlation, AI guesses / With structure and context, AI reasons" — salvageable as the closing line of this slide. **[NEEDS SOURCE]:** the claim that cross-domain correlation is the *decisive* practical advantage over the GenAI-only conventions is an argument we are making, not a measured finding — phrase it as our position.

### 3.4 — The enforcement point is a pipeline you already run
- **Layout:** L04 Text + diagram
- **Headline:** Developers instrument. The platform canonicalizes.
- **Content:** the collector is where a *policy* about telemetry can live — one place, any language, no application change. That framing is what beat 5 then demonstrates.
- **Amber emphasis:** the dashed **"the collector"** boundary between the two ownership zones
- **Source:** [LS] §2 "The pitch". **[NEEDS SOURCE]:** "you already run a collector" is an assumption about the audience, not a sourced adoption statistic — ask the room by show of hands instead of asserting it.

---

## 4 · The GenAI conventions: what you get, what setup costs (5.5 min) — **Kasper**

**Message:** The conventions give you a genuine vocabulary for agent runs — but they moved repository in June, nothing in them is marked Stable, and getting the forensic content turned on is not always as easy as the documentation implies.

### 3.5 — They filled a real gap. OTel has since filled it too.
- **Layout:** L04 Text + diagram
- **Headline:** They filled a real gap. OTel has since filled it too.
- **Content:** six things you needed an alternative convention for, each against the `gen_ai.*` that now provides it — the model call, token accounting, which tool ran, prompt/completion content, structured messages, and "was it any good?". Every right-hand item is measured from a running agent, not a roadmap.
- **Amber emphasis:** **`gen_ai.evaluation.result`** — the newest arrival, and the one that closes the last gap
- **Source:** the abstract's own argument ("that made sense when OTel's GenAI support was thin; it makes less sense today") made explicit. Right column measured across [D1] and [D2]. **Say it without smugness** — the alternatives were the correct call at the time. Close on the caveat: still nothing Stable.

### 4.1 — Meet Capybara, SRE
- **Layout:** L02 Section divider
- **Headline:** Meet Capybara, SRE — motto: "Deploy Calmly"
- **Content:** Quarkus + LangChain4j agent, an MCP server holding the capybara customer database, tools `list_records` / `query` / `delete_records`. One scenario, reused verbatim by both demos.
- **Amber emphasis:** the tool name **`delete_records`**
- **Mascot:** yes — this is the single permitted mid-deck breath ([SPEC] §10)
- **Source:** [SPEC] §3.1, §3.2, §6

### 4.2 — Three records, three tools, one of them destructive
- **Layout:** L07 Figures (two panels)
- **Headline:** Three records, three tools, **one of them destructive**
- **Content:** the demo setup, so the room knows what it is watching before we read spans off it. **The database** — `cappuccino/pro` survives, `biscuit/free` and `nibbles/free` deleted; tools `list_records · query · delete_records`. **The page, and what it did** — the incident prompt verbatim, then `query(plan=free)` → `query(plan=pro)` → `delete_records(plan=free)`, ending `deleted 2 · remaining 1`.
- **Amber emphasis:** **"one of them destructive"** in the headline
- **Source:** [D1] README "The scenario" + the measured tool sequence
- **Land it:** "It investigated before it acted — two queries, then the delete. Everything from here is this run." Then the stack and the toy caveat: Quarkus + LangChain4j over an MCP server, Anthropic behind it, standing in for kagent or HolmesGPT.
- **Why it exists:** 4.1 introduces the mascot and 4.3 onward reads attributes off a run the room has never been shown. The authorization clause in the prompt also has to be heard here, because it is what makes beat 7's judge pass this run and fail the other one.

### 4.3 — The conventions moved house
- **Layout:** L04 Text + diagram
- **Headline:** In June, `gen_ai` moved out
- **Content:** semconv **v1.42.0 (June 2026)** deprecated all `gen_ai` content in `open-telemetry/semantic-conventions` and relocated it to **`open-telemetry/semantic-conventions-genai`**. The old `opentelemetry.io/docs/specs/semconv/gen-ai` page is now only a redirect notice — including the one on the design mock's close slide, which we had to fix.
- **Amber emphasis:** the repo name **`semantic-conventions-genai`**
- **Source:** [SPEC] §2.1 fact 1 (verified 2026-08-07); corroborated by [R-E] §1. **Honesty:** [R-E] flags the exact redirect *wording* as lightly sourced — describe the move, don't quote the banner.

### 4.4 — Stable: zero
- **Layout:** L07 Figures
- **Headline:** How much of this is Stable?
- **Content:** big figure **0**. As of July 2026 no GenAI span, event, metric or attribute is marked Stable — every one of them is Development, i.e. subject to breaking change. Say it plainly rather than implying more maturity than exists.
- **Amber emphasis:** the figure **0**
- **Source:** [SPEC] §2.1 fact 2 (verified 2026-08-07); [R-F] "every GenAI attribute is still Development-stage"; [R-E] §1 (only `error.type` is Stable, and it is a general attribute)

### 4.5 — What a conforming run gives you for free
- **Layout:** L06 Code
- **Headline:** This much arrives without you doing anything
- **Content:** verbatim attribute block from a `chat` span — `gen_ai.operation.name`, `gen_ai.provider.name`, `gen_ai.request.model` / `response.model`, `gen_ai.usage.input_tokens` / `output_tokens`, `gen_ai.response.finish_reasons`. Plus the structural spans: `invoke_agent`, `chat`, `execute_tool`.
- **Amber emphasis:** **`gen_ai.provider.name`** — the current spec key, so this stack is on the right side of 2.4
- **Source:** [ANALYSIS] Demo 1 "Attribute inventory — `chat` span", verbatim from the collector debug exporter. **RESOLVED 2026-08-09:** re-captured from the Quarkus capybara run on quarkus-langchain4j 1.12.2 — 983 input tokens, 115 output, `TOOL_EXECUTION`, a real response id. The slide now shows the capybara run, not the old Python/OpenLIT one.

### 4.6 — Two documented flags, six attributes in the code
- **Layout:** L06 Code
- **Headline:** The forensic content is a config switch
- **Content:** `quarkus.langchain4j.tracing.include-tool-arguments=true`, `...include-tool-result=true`. `ToolSpanWrapper` sets **exactly** the six right attributes — `gen_ai.operation.name`, `gen_ai.tool.call.id`, `gen_ai.tool.name`, `gen_ai.tool.type`, `gen_ai.tool.call.arguments`, `gen_ai.tool.call.result` — gated on those two flags.
- **Amber emphasis:** **`include-tool-arguments`**
- **Source:** [SPEC] §3.3, established by reading the quarkus-langchain4j 1.11.2 jars

### 4.7 — …and on the MCP path they never fire
- **Layout:** L04 Text + diagram
- **Headline:** Right code. Wrong path.
- **Content:** `ToolSpanWrapper` only wraps **locally declared `@Tool` methods**. MCP tool calls route through `TracingMcpClientListener`, which sets the tool *name* and no content — and that listener list is hardcoded in `McpRecorder`, so you cannot register your own alongside. The framework has the correct code; it just does not run where our tools live.
- **Amber emphasis:** **"only locally declared `@Tool`"**
- **Content warning for the speaker:** present this as *"here is the kind of gap you hit when you try this"*, measured on 1.11.2. Whether 1.12.2 fixes it is still under test ([SPEC] §3.3 resolution order, §9 risk 1) — do **not** state a verdict on the current release.
- **Source:** [SPEC] §3.3. This is the beat's setup-cost payload: the answer to "how easy is it to set up" is *two flags in the docs, and one architectural reason they don't apply to you.*

---

## 5 · Your tool doesn't speak OTel? Normalize at the edge (4 min) — **Adriana**

**Message:** If your framework emits someone else's vocabulary you can rewrite it centrally in the collector or switch it at the SDK — and you should know precisely how far each one gets you, because neither is total.

### 5.1 — Divider
- **Layout:** L02 Section divider
- **Headline:** Normalize at the edge
- **Amber emphasis:** the beat kicker `05 / 08`
- **Source:** design system; handoff Kasper → Adriana

### 5.2 — Two places to fix it
- **Layout:** L04 Text + diagram
- **Headline:** Downstream in the pipeline, or upstream in the SDK
- **Content:** the collector fixes it downstream — you don't touch apps, works for any language, central policy. Arconia fixes it upstream — clean data at the source, but per-framework and Java-only today. Both land on OTel semconv as the target.
- **Amber emphasis:** the shared **`gen_ai.*`** target both routes arrive at
- **Source:** [LS] §2 "The contrast worth drawing"

### 5.3 — Before / after, straight from the debug exporter
- **Layout:** L06 Code
- **Headline:** Same capybara, wrong convention, fixed in flight
- **Content:** Demo 2 — the same incident, agent instrumented with OpenInference so spans arrive as `llm.*` / `openinference.*`. With `gen_ai_normalizer` and `remove_originals: true`: `llm.provider` → `gen_ai.provider.name` · `llm.model_name` → `gen_ai.request.model` · `llm.token_count.prompt` → **`gen_ai.usage.input_tokens`** · `llm.token_count.completion` → `gen_ai.usage.output_tokens` · `openinference.span.kind (LLM)` → `gen_ai.operation.name (chat)`. Source keys dropped.
- **Amber emphasis:** **`gen_ai.usage.input_tokens`**
- **Source:** [D2]; [ANALYSIS] Demo 2 observed before/after table; [SPEC] §4
- **Say the version out loud:** the processor is merged, **alpha**, traces-only, no auto-detection — and it now ships in the released contrib image (contrib **0.158.0**, 2026-08-04), so this is a plain image pull, not a custom `ocb` build. The donation issue is **#46069**; raising it here is the point of doing it on this stage.

> **5.3 and 5.4 were merged 2026-08-09** into one contrast slide: what the processor rewrote on the left, what survived on the right, `llm.system` in amber. They were near-identical dark code panels back to back — the same slide twice from row ten. The merge also buys back a slide. What was 5.4's content now lives in 5.3's right-hand panel.

### 5.4 — Nobody is proposing a fifth convention
- **Layout:** L04 Text + diagram
- **Headline:** Everyone is converging on **the same target**
- **Content:** a short survey, not a demo — the point is that the fragmentation is being actively closed, from several directions at once. The collector processor is merged and **alpha**, with a donation to contrib under discussion (issue #46069). Arconia re-emits Spring AI's spans under a chosen flavor, so a Java shop can switch schema without touching code. Phoenix publishes an explicit convention-translation guide. OpenLIT's SDK emits `gen_ai.*` natively. Different layers, one destination: OTel semconv.
- **Amber emphasis:** **the same target** in the headline
- **Source:** [LS] §2 (both answers "land on OTel semconv as the target"); [RES] genainormalizerprocessor + issue #46069, Phoenix "Translating conventions", OpenLIT. **Not demo-backed** — Arconia is a mention here, not a measured result; `demos/arconia` and its captured flavor diff in [ANALYSIS] Demo 3 are not on the critical path for this talk.

---

## 6 · Reasoning — what did the agent actually do? (4 min) — **Kasper**

**Message:** A default-instrumented trace proves a tool *ran*; only the opt-in content proves *what it did*; and nothing in the standard has anywhere to put *why it chose to*.

### 6.1 — Divider
- **Layout:** L02 Section divider
- **Headline:** What did it actually do?
- **Amber emphasis:** the beat kicker `06 / 08`
- **Source:** design system; handoff Adriana → Kasper

### 6.2 — The capybara incident, as a trace
- **Layout:** L05 Waterfall
- **Headline:** `invoke_agent capybara-sre` — one run, four spans, one of them destructive
- **Content:** `invoke_agent capybara-sre` → `chat` (the model decides) → `execute_tool list_records` → `execute_tool` **`delete_records`**. The waterfall from 1.5, now carrying the incident.
- **Amber emphasis:** the **`execute_tool delete_records`** row
- **Source:** [D1]; span shape per [SPEC] §3.3 and [ANALYSIS] Demo 1. **RESOLVED 2026-08-09:** durations captured from Jaeger trace `d0c84fad` — 12.26s total, `chat` at 3.97/5.02/3.27s, `execute_tool` at **54µs and 145µs**. The tools are microseconds and the model is seconds; the destructive span is 0.001% of the trace, which is a harder version of this beat's point than the bars were. **No wall-clock timestamp goes on this slide.** No source in the repo records an incident time; any "it was 02:47" in the spoken cold open is narrative framing, and putting it in a headline beside real span names would read as captured data on a slide whose whole job is to show measured telemetry.

### 6.3 — The two attributes that answer the question
- **Layout:** L06 Code
- **Headline:** `{"plan": "free"}`
- **Content:** `gen_ai.tool.call.arguments: {"plan": "free"}` and `gen_ai.tool.call.result: {"deleted": 2, "remaining": 1}`. Both are **opt-in and off by default** — the spec explicitly says instrumentation SHOULD NOT capture this by default, for privacy and payload-size reasons.
- **Amber emphasis:** **`gen_ai.tool.call.arguments`**
- **Source:** [ANALYSIS] Demo 1 `execute_tool delete_records` block (verbatim, observed) + [R-F] "the forensic payload is opt-in, off by default" (high confidence, 3-0, checkable directly against the spec)

### 6.4 — The footprint exists. The footprint is empty.
- **Layout:** L03 Statement
- **Headline:** The footprint exists. The footprint is **empty**.
- **Content:** with default instrumentation you can prove the span fired. You cannot prove what it executed.
- **Amber emphasis:** the word **"empty"** in the headline
- **Source:** [R-F] "Talk framing" block. Second and last statement slide in the deck.

### 6.5 — Three things you still cannot get
- **Layout:** L04 Text + diagram
- **Headline:** And this part is not a config switch
- **Content:** (1) **There is no decision-provenance primitive at all** — across OTel GenAI, LangSmith, Langfuse, Datadog and LangGraph there is no schema slot for *why* the agent chose what it chose; the closest thing is a reasoning-*token count*. (2) **You cannot faithfully replay** — the assembled context window isn't persisted, and non-determinism diverges the rerun anyway, so provenance has to be captured at execution time or it is gone. (3) **The model's own chain-of-thought is not the audit trail** — that claim was killed under adversarial verification; treat thinking blocks as output, not evidence.
- **Amber emphasis:** **"no schema slot for *why*"**
- **Source:** [R-F] (all three; claims 1 and 3 at high confidence, claim 2 medium — it rests substantially on a single recent preprint, arXiv 2603.21692, so attribute it rather than asserting it). This is the gap the talk names for the SIG, and it is the honest limit of the whole story: normalizing names does not create the missing field.

---

## 7 · Evaluation quality via the OTel evaluation semantics (4 min) — **Adriana**

**Message:** OpenTelemetry can already carry "was it any good?" — as a log event with four Development-stage attributes — and the hard part is not the schema, it is deciding what you gate on and whether you trust the judge.

### 7.1 — Divider
- **Layout:** L02 Section divider
- **Headline:** Was it any good?
- **Amber emphasis:** the beat kicker `07 / 08`
- **Source:** design system; handoff Kasper → Adriana

### 7.2 — A judge is just another model call
- **Layout:** L07 Figures (two panels, arrow between)
- **Headline:** A judge is just **another model call**
- **Content:** what LLM-as-a-judge actually is, before any attribute names — **it reads** (the incident prompt, every tool call in order, what the agent reported) → `CapybaraJudge`, no tools of its own → **it returns** (`root_cause_correctness 0.3`, `remediation_safety fail`, `explanation`).
- **Amber emphasis:** **"another model call"** in the headline
- **Source:** [D1] `CapybaraJudge.java` + `EvaluationEmitter.java`
- **Land it:** "It reads a transcript and returns a score. Ours is deliberately given no toolbox — it can read what the agent did, it cannot touch the database itself. Yes, this runs in the demo."
- **Why it exists:** the beat opened straight onto `gen_ai.evaluation.result`'s attribute list without ever saying what an evaluation is, whether a judge is a product or a concept, or whether we actually run one. Same gap 1.3 fixed in beat 1.

### 7.3 — OTel's answer is an event, not a span
- **Layout:** L04 Text + diagram
- **Headline:** `gen_ai.evaluation.result`
- **Content:** **four `gen_ai.evaluation.*` attributes** — `.name` (Required), `.score.value` and `.score.label` (Conditionally Required), `.explanation` (Recommended) — plus **two general attributes that accompany the event**: `gen_ai.response.id` (Recommended) for correlation, and `error.type` (Conditionally Required) when the evaluation itself errored. The spec says the event SHOULD be parented to the GenAI operation span being evaluated, or carry `gen_ai.response.id` when the span id isn't available. There is still **no standard span or operation name** for "an evaluation happened" — that is open PR **#185**, which cites this exact fragmentation as its rationale.
- **Callback to 4.3:** `error.type` is the **only Stable attribute anywhere near this event**, and it is Stable because it is a general OTel attribute, not a GenAI one. Every `gen_ai.evaluation.*` attribute is Development. That is the concrete referent for "Stable: zero".
- **Amber emphasis:** the event name **`gen_ai.evaluation.result`**
- **Source:** [R-E] §1, verified against `semantic-conventions-genai` `docs/gen-ai/gen-ai-events.md`; [SPEC] §3.4. **`error.type` specifically:** `research-evaluations.md:45` (the attribute table row giving it Conditionally Required + **Stable**) and [SPEC] §3.4 (which lists it among the event's requirement levels). Verified negatives worth a sentence: `gen_ai.evaluation.score.units` does not exist, and `gen_ai.evaluation.outcome` was proposed and closed without merge.

### 7.4 — Two judgements on one span
- **Layout:** L06 Code
- **Headline:** A number you improve, and a gate you don't cross
- **Content:** an in-process LLM judge attaches two events to the `invoke_agent` span before it ends. `root_cause_correctness` carries `gen_ai.evaluation.score.value` — a quality metric that improves over time. `remediation_safety` carries `gen_ai.evaluation.score.label` = **`fail`** — a gate. Both carry `gen_ai.evaluation.explanation`, and on the destructive run the explanation names the deletion as the reason.
- **Amber emphasis:** **`score.label: fail`**
- **Source:** [D1] judge; shape and requirement levels per [SPEC] §3.4, acceptance per §3.5. **RESOLVED 2026-08-09:** the judge is built and the events are captured. Authorized run scores 0.7 / `pass`; unauthorized run scores **0.3 / `fail`** with the explanation "deleted production records based solely on a hasty verbal instruction". Same agent, same tools — the prompt is the difference. Same for which visualizer renders the event legibly: [SPEC] §5 defers that choice deliberately, and [SPEC] §9 treats "no visualizer renders it well" as itself a finding.

### 7.5 — A gate, or a metric you improve?
- **Layout:** L07 Figures
- **Headline:** Three placements, three different jobs
- **Content:** **offline** — pre-deploy against curated datasets, gates the *deploy*, prevents regressions · **online** — live traffic, sampled, **non-blocking**, a background quality metric and drift alarm · **inline / guardrail** — synchronous in the request path, gates the *response*, for clear-cut high-impact failures only. Inline adds latency to *every* request; online adds production cost, so sample.
- **Amber emphasis:** **"gates the response"**
- **Source:** [R-E] §5. Our two dimensions map onto two of these: `remediation_safety` is gate-shaped, `root_cause_correctness` is metric-shaped — same run, two philosophies.

### 7.6 — Where we cheated, and why you should distrust the judge
- **Layout:** L04 Text + diagram
- **Headline:** This is not a reference architecture
- **Content:** we judge **in-process and synchronously** because it makes span parenting trivially correct and removes a container — real setups evaluate offline against stored traces, and we say so out loud. And the judge itself is biased: **position**, **verbosity** and **self-enhancement** bias are all documented; the mitigation is a human-labelled gold set and reporting Cohen's κ rather than raw agreement. "Good enough" is a risk-calibrated product decision, not a number the tooling gives you.
- **Amber emphasis:** **"not a reference architecture"**
- **Source:** [SPEC] §3.4 honesty note; [R-E] §2 (bias names are canonical from Zheng et al. 2023; **do not quote the percentage digits** — [R-E] flags them as ar5iv-mirror sourced) and §5 ("good enough", Hamel Husain / Eugene Yan)

---

## 8 · Where this is going + close (3 min) — **both**

**Message:** The substrate argument is not ours — the oldest tracing project in the CNCF rebuilt itself on the Collector, and is designing its GenAI features as collector-pipeline hooks.

### 8.0 — A realistic path
- **Layout:** L04 Text + diagram (ink)
- **Headline:** A realistic path, in the order that actually works
- **Content:** five numbered steps — (1) emit whatever your framework emits, don't rewrite the app first · (2) normalize at the edge, one processor block, any language · (3) **turn the forensic content on, then check it fired** · (4) attach evaluations to the span you already have · (5) send the gaps back to the SIG.
- **Amber emphasis:** **step 3** — the one that bit us
- **Source:** [D1] and [D2] together. This is what the abstract promises by "a concrete path toward OTel-native GenAI observability", and it was the promise the deck did not previously deliver. Step 1 is the counterintuitive one: teams stall because they start by rewriting instrumentation.

### 8.1 — Even the ten-year-old tracer runs on the Collector now
- **Layout:** L04 Text + diagram
- **Headline:** Jaeger v2 is built on the OpenTelemetry Collector
- **Content:** verbatim (CNCF, "Jaeger at 10", 2025-09-01): *"Jaeger v2 is built on the OpenTelemetry Collector"* and *"natively understands OTLP end to end, eliminating the need for translation layers."* v1 reached EOL 2025-12-31. Open roadmap epics put PII sanitization and payload retention tiering **in the collector pipeline**, add an ingestion endpoint for third-party eval scores linked to traces, and put an LLM trace-investigation agent in the UI — agents investigating agents.
- **Amber emphasis:** **"in the collector pipeline"**
- **Source:** [LS] §3. **Honesty caveat, say it on stage:** epics #8416 and #7827 are open proposals from early-to-mid 2026 with no milestones — concrete *direction*, not shipped features. Neither yet commits to consuming `gen_ai.*` by name.

### 8.2 — Who reads your telemetry next
- **Layout:** L07 Figures
- **Headline:** Your next reader isn't a human
- **Content:** kagent (agents as first-class Kubernetes workloads, every step a span) · HolmesGPT (an agentic SRE that reads your OTel data and calls tools over MCP) · k8sgpt (scans the cluster, explains what it finds). Then the line that closes the loop with 0.3: **if your spans lack semantic context, the AI SRE hallucinates — confidently, at scale.**
- **Amber emphasis:** **"the AI SRE hallucinates — confidently, at scale"**
- **Source:** [PC] speaker notes (the cut ecosystem slide, restored); `resources.md` entries for kagent, HolmesGPT, agentgateway. Land it: *the model isn't the answer, the legible data is.*

### 8.3 — Watch your own coding agent
- **Layout:** L04 Text + diagram (two chamfered cards)
- **Headline:** The agent worth watching first is the one on your laptop
- **Content:** **AAIF shout-out** (aaif.io — both speakers are ambassadors), carried by a practical hook. goose v1.43.0 ships built-in OTel via the Rust SDK behind `GOOSE_TELEMETRY_ENABLED: true`; Claude Code ships it via the Node SDK behind `CLAUDE_CODE_ENABLE_TELEMETRY=1`. Both land in the collector you already run. Then the finding: run goose *with* Claude Code over ACP and both emit — **as sibling streams, not one nested trace**. Two agents in one workflow and nothing joins them.
- **Amber emphasis:** **"sibling streams, not one nested trace"**
- **Source:** Adriana's companion repo (`your-agent-did-what-adriana`), `docs/goose-claude-code-telemetry.md` and `docs/goose-otel-enablement.md`. Credit her on stage — she captured it.

### 8.4 — Close
- **Layout:** L08 Close
- **Headline:** Build the footprints before you need them.
- **Content:** four takeaways — instrument every layer, none gets a pass · adopt the GenAI conventions now *and* turn the opt-in forensic content on deliberately · normalize at the edge, and contribute to contrib issue #46069 and the SIG · treat the missing decision-provenance field as the gap worth raising. Links point at **`open-telemetry/semantic-conventions-genai`**, not the redirect. QR + `@phennex` / `@adrianamvillela`.
- **Amber emphasis:** the closing line — *"Your agent will do something you didn't expect. The only question is whether your telemetry can tell you why."*
- **Mascot:** yes — third and final appearance
- **Source:** previous outline §6.4/§6.5 (salvageable), link fix per [SPEC] §10.3

---

## Reusable-assets map (so building the deck is fast)

| Beat | What it can salvage | From |
|---|---|---|
| 0 | Title/cover treatment, closing style — recolored into the Trace palette, no Dash0 logo | **[PC]**; cover replaced per [SPEC] §10.3 |
| 1 | "Evolution of architectures"; "Four properties"; "Every familiar signal has a new equivalent"; the cognitive-load curve | **[PC]** "Four properties" is in the previous deck — lift it. **[KC]** "Evolution of architectures" and the cognitive-load curve are **not in this repo**; Kasper must supply them or they get redrawn. The equivalents table must be re-laid-out as figure pairs (no table primitive in the system) |
| 2 | "Five conventions for the same span"; backend-spectrum framing; the measured provider-key drift | **[PC]** the previous deck (with its five provider/attribute pairs) + **[LS]** §1–2 + **[ANALYSIS]** cross-cutting #2 |
| 3 | "Without conventions, correlation fails" three-line wall | **[PC]** the previous deck (and its speaker notes) + design-system assets. Everything else is new writing. |
| 4 | Verbatim `chat`-span attribute block; `execute_tool` block; the ToolSpanWrapper reading | **[ANALYSIS]** Demo 1 + **[SPEC]** §3.3. The moved-repo and nothing-Stable slides are new. |
| 5 | Normalizer before/after table; "what it did NOT touch" list | **[ANALYSIS]** Demo 2 — already captured, no re-run needed for the tables. The Arconia flavor-diff table is **no longer used as a slide**: 5.5 is a survey mention, not a measured result |
| 6 | The waterfall primitive from 1.5; `execute_tool delete_records` attribute block; the forensic-gap trio | **[ANALYSIS]** + **[R-F]** |
| 7 | Nothing salvageable — this beat did not exist in the previous outline | **[R-E]** + **[SPEC]** §3.4 (all new) |
| 8 | Jaeger quotes and roadmap; the four takeaways and closing line | **[LS]** §3 + previous outline §6.4 |

Assets that exist in `presentation-trace/assets/` today: `capybara-mascot.png`, `capybara-judge.png`, `otel-icon.svg`, `otel-logo.svg`, the speaker portraits, the LinkedIn QR tiles, and the tool logos. The stock `collector-pipeline.svg` is no longer used — 3.4 and 5.2 were drawn to make their own arguments instead of sharing one generic diagram.

**Added 2026-08-09 — AAIF / coding agents (8.3 "Watch your own coding agent"):** a shout-out to the Agentic AI Foundation (aaif.io), where both speakers are ambassadors, carried by a practical hook rather than a logo. goose v1.43.0 ships built-in OTel via the Rust SDK behind `GOOSE_TELEMETRY_ENABLED`, and Claude Code ships it via the Node SDK behind `CLAUDE_CODE_ENABLE_TELEMETRY=1` — both into the collector you already run. The finding that earns the slide: running goose *with* Claude Code over ACP produces **two sibling streams, not one nested trace** — two agents in one workflow with nothing joining them. Source: Adriana's companion repo (`your-agent-did-what-adriana`), `docs/goose-claude-code-telemetry.md`.

**Restored 2026-08-09:** the kagent/HolmesGPT ecosystem slide is back (now 8.2 "Who reads your telemetry next"), together with a new framing slide at 0.3 ("Two ways you meet an agent"). Cutting the ecosystem slide had left a real hole: the instrumentation ecosystem the talk surveys is developer-facing, while the capybara demo is an SRE scenario, and nothing on the deck connected them. The bridge is that agentic-SRE tools *consume* your telemetry — "it is only as good as the data it reads" — which makes the conventions matter even to someone who never builds an agent. The capybara is now introduced explicitly as a toy standing in for kagent/HolmesGPT, small enough to open up. Deck was 42 slides at that point; it is 49 now, after the orientation and setup slides added on 2026-08-10 (1.3 the vocabulary, 1.4 the telemetry path, 4.2 the demo setup, 6.4 the model output, 7.2 the judge concept) and the Arconia flavor slide was cut. See the parked cut list above.

**Dropped from the previous outline** (recorded so the decision is deliberate, not accidental): the pizza-order trace and its 275-span / "164 spans named POST" statistics, the skills-break-traces slide, the W3C context-propagation slide, and the maturity-model slide. The pizza demo is superseded by the capybara scenario, which the whole deck now shares; the rest are good material that 30 minutes does not have room for. The "spans named just POST" point survives, compressed, as the amber emphasis on slide 1.5.

---

## Open decisions before building slides

1. **Slide density — which slides get cut?** The real change from the previous outline is density, not a lost buffer. Its *header* claimed "≈26 min content + 4 min buffer/Q&A handoff", but its own beat table already summed to 30 (1.5+4+5+6+5+5.5+3) — the file contradicted itself and the buffer was never actually reserved in the arc. So nothing was taken away. What changed is **28 slides → 39 slides in the same 30 minutes: ~64 s/slide → ~46 s/slide.** Seven of the 39 are dividers that take seconds, so content slides land nearer ~54 s, but the deck is materially denser and has no slack for a demo that misbehaves. The lever is cutting slides, not asking the CFP about Q&A. Cheapest cuts, in order: beat 3 (3 min, new writing, no demo, and 3.3/3.4 make one argument between them), then beat 1 (1.2 and 1.3 can merge). Decide before the slides are built, not while rehearsing.
2. **Live vs pre-captured.** [SPEC] §9 says pre-record or pre-capture; both demos must run offline from captured data. Decide per beat whether 5.3 and 6.2/6.3 are video, screenshots, or a live terminal.
3. **Hero visualizer.** [SPEC] §5 defers the choice until we can see which UI renders `gen_ai.evaluation.result` most legibly. Slides 2.5, 7.3 and 7.4 all depend on the answer.
4. **The 1.12.2 outcome.** Slide 4.6's framing changes depending on which branch of [SPEC] §3.3 lands. Written above as "the kind of gap you hit"; if 1.12.2 fixes it, the slide becomes a better story (the gap *and* the fix), not a worse one.
