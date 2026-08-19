# Outline — Your Agent Did What?

**Forensic Observability for Systems That Don't Leave Obvious Footprints**
Kasper Borg Nissen (Dash0) · Adriana Villela (Dynatrace) — 35 minutes.

Aligned to the **Google Slides deck, 46 slides**. Slide numbers here are that deck's numbers.
Full stage directions are in `SPEAKER-NOTES.md`, kept with the deck archive at
`~/Documents/your-agent-did-what/` — one section per slide.

## The argument in five sentences

1. Agents are not request/response, and the thing that makes them hard is that the decision
   is taken at runtime and never written down.
2. Five conventions name the same span five ways, for legitimate reasons, and the cost of
   that lands on you rather than on them.
3. OpenTelemetry is where they are all converging, and a collector processor gets you there
   today without touching an application.
4. Then something deletes production data, and the trace answers *what* and *when* and never
   answers *why* — because no convention has a field for it.
5. A judge can score the run, the audit trail can name the credential, and neither is the
   same as knowing why. Build the footprints before you need them.

## Timing

| Section | Slides | Target |
|---|---|---|
| Opening | 1–3 | 2 min |
| 01 · Agents aren't request/response | 4–11 | 6 min |
| 02 · Five conventions, one span | 12–15 | 4 min |
| 03 · Why OpenTelemetry should be the standard | 16–24 | 7 min |
| 04 · Rows went missing (incl. the live demo) | 25–30 | 7 min |
| 05 · What did it actually do? | 31–36 | 5 min |
| 06 · Was it any good? | 37–41 | 3 min |
| 07 · Wrapping up | 42–46 | 2 min |

The demo is the only elastic part. If it misbehaves, the rehearsal endpoint puts the database
in the same state and costs you only goose's own telemetry — see *The extra door* in
[`demos/README.md`](demos/README.md).

---

## Opening · 1–3

| # | Slide | Its job |
|---|---|---|
| 1 | Your Agent Did WHAT? | Title. The subtitle does the work — leave it up. |
| 2 | Who? | Twenty seconds each. Credentials, not biography. |
| 3 | We keep changing what we have to understand | Monolith → microservices → event-driven → LLM apps. Building got easier; understanding got harder every time. |

## 01 · Agents aren't request/response · 4–11

Establish what an agent is and what is genuinely new about operating one. Do not rush 8 and 9.

| # | Slide | Its job |
|---|---|---|
| 4 | Section divider | Up next. |
| 5 | An agent is one part of an LLM application | Zoom out first: orchestration, model, retrieval, tools, scaffolding. Only the right-hand box is new. |
| 6 | Five words we will use for the next half hour | provider · model · MCP · agent · harness. Defined once so nobody decodes vocabulary later. |
| 7 | An agent is a loop around a model that can call your tools | The loop, drawn. Two things are yours: the prompt and the tool list. |
| 8 | Four properties we've never operated before | Non-determinism, runtime call graph, tokens as the cost model — and opaque decisions, which is the one the talk is about. |
| 9 | Nobody builds an agent to do something destructive | The stakes without the scaremongering. Useful and destructive are the same capability pointed at different rows. |
| 10 | You either build one, or you run someone else's | Two audiences. The second has two problems: it reads your telemetry *and* acts on your systems. |
| 11 | Every familiar signal has a new equivalent | Our practice isn't wrong, it's incomplete. Point back here in section 06. |

## 02 · Five conventions, one span · 12–15

| # | Slide | Its job |
|---|---|---|
| 12 | Section divider | Up next. |
| 13 | One model call. Five names for the model. | The fan-out. One HTTP call, five names, and your dashboard silently returns nothing on someone else's spans. |
| 14 | Instrumenting the agent is not instrumenting the SDK | The distinction that changes what you get: only the agent's own instrumentation knows *why* a tool was called. |
| 15 | Four teams, four problems, and no standard to adopt | The diagnosis. Every one shipped before the conventions existed — which cost nothing until you started running agents you did not choose. |

## 03 · Why OpenTelemetry should be the standard · 16–24

The longest section, and the one that earns the demo. It runs: what OTel is → everyone aims
at it → the code is already moving → here is the processor → where to put it → here it is
working → what it cannot do → the baseline you get for free.

| # | Slide | Its job |
|---|---|---|
| 16 | Section divider | Up next. |
| 17 | A toolkit and a specification | What OTel is and is not. The line that matters: of everything on the left, this talk turns on semantic conventions. |
| 18 | They already agree more than they admit | The fan turned the other way up. Nobody is proposing a fifth convention. |
| 19 | The code is converging. The vocabulary is not, yet. | Two code grants on one timeline: sixteen months to nothing, versus one month to accepted. |
| 20 | A collector processor that renames as it passes | `gen_ai_normalizer`, contrib 0.158.0. No application change, any language, alpha and traces only. |
| 21 | Downstream in the pipeline, or upstream in the SDK | Collector versus Arconia. Both target OTel names; platforms will want the collector. |
| 22 | The wrong vocabulary, fixed in flight | The animation. Seven renames on a real span, with `llm.system` riding through untouched. |
| 23 | It converts the attributes, not the result. | The limit. `output.value` has no entry in the mapping table — the arguments convert and the result does not. |
| 24 | This much arrives without you doing anything | The baseline before the incident. Captured verbatim; nothing hand-written. |

## 04 · Rows went missing · 25–30

Where the talk turns. **The live demo sits at slide 28.**

| # | Slide | Its job |
|---|---|---|
| 25 | Section divider | Up next. |
| 26 | It deleted the rows. The incident is over. Now prove why. | The situation. Don't name a culprit — the reveal is that no agent did it. |
| 27 | Something deleted production data. No agent admits to it. | The architecture: three investigators, one database, one collector — plus the loop and `_meta` propagation absorbed from a cut slide. |
| 28 | It's demo time! — the cast | **Slides down, terminal up.** Deletion, then the same question to each investigator, then the traces side by side. |
| 29 | Three agents, three vocabularies | The run you just watched, as three stacks. |
| 30 | One column needs translating. The other two do not. | Seven facts, three sets of names. Not a missing fact — a rename, seven times. |

## 05 · What did it actually do? · 31–36

| # | Slide | Its job |
|---|---|---|
| 31 | Section divider | Up next. |
| 32 | invoke_agent: 19.05s, 21 spans… | The incident as a trace, and the SELECTs are not in it at all. |
| 33 | The answer is in the result, not the arguments | The two attributes the whole argument turns on — both Opt-In. |
| 34 | The agent that did it wrote down what it deleted | goose's own telemetry. A harness that instruments itself records more than a library wrapped around one. |
| 35 | It records what it concluded, and what it did next | The closest the conventions come to reasoning — and why that still isn't *why*. |
| 36 | No convention has a field of why | The honest limits. One is a specification gap the SIG wants feedback on; the others are not gaps anyone can close. |

## 06 · Was it any good? · 37–41

| # | Slide | Its job |
|---|---|---|
| 37 | Section divider | Up next. |
| 38 | LLM as a judge is just another model call | What scoring actually is, and that we really run one. |
| 39 | `gen_ai.evaluation.result` | It is an **event in the logs data model**, not a span. Open PR #185 proposes a span. |
| 40 | A number you improve, and a gate you don't cross | Two judgements on one span, and the difference between a metric and a gate. |
| 41 | The further from the decision, the less it can see | Where the judge sits — and the *when* question the appendix covers. |

## 07 · Wrapping up · 42–46

| # | Slide | Its job |
|---|---|---|
| 42 | Section divider | Up next. |
| 43 | A realistic path, in the order that actually works | What to do on Monday if you are on someone else's convention today. |
| 44 | The agent worth watching first is the one on your laptop | One environment variable each. The coding agent lands in the collector you already run. |
| 45 | Build the footprints before you need them. | The close. You cannot mitigate what you cannot reconstruct. |
| 46 | Thank you. | Both of us, both employers, both QR codes. |

---

## What lives where

- **Slides** — Google Slides. The HTML deck it came from is archived outside this
  repository; see [`README.md`](README.md).
- **Speaker notes** — `SPEAKER-NOTES.md`, aligned slide-for-slide, in `~/Documents/your-agent-did-what/`.
- **Type and colour** — `SLIDES-STYLE.md`, same place, so edits stay on-brand.
- **The demo** — [`demos/`](demos/), with the measured record in
  [`demos/ANALYSIS.md`](demos/ANALYSIS.md).
- **Sourcing** — [`research.md`](research.md).

## One correction to make in the deck

Slide 44's title reads *"The agent worth watching first **it** the one on your laptop"*.
Should be *is*.
