# Your Agent Did What?

**Forensic Observability for Systems That Don't Leave Obvious Footprints**
Conference talk by **Kasper Borg Nissen** & **Adriana Villela** — on OpenTelemetry, GenAI
semantic conventions, and observing autonomous agents.

> The GenAI observability space is fragmented — OpenInference, OpenLLMetry,
> framework-specific conventions all naming the same things differently. OpenTelemetry is
> where it converges. This talk maps that landscape honestly, shows how to bridge the gap at
> the collector (`gen_ai_normalizer`), and then asks the harder question: your agent just
> deleted a database — what does your telemetry actually tell you?

First delivery **SREday London**; then **OSS Summit EU** (October).

---

## What's in here

| Path | What it is |
|---|---|
| **[`presentation/`](presentation/)** | **The deck.** 50 slides across the nine beats, on the Trace design system, with a conformance checker and a layout audit. |
| **[`outline.md`](outline.md)** | The beat-by-beat outline: timing, who leads each beat, what each slide must land, and the parked cut list. |
| **[`abstract.md`](abstract.md)** | The submitted abstract and ecosystem benefits. |
| **[`demos/`](demos/)** | Two runnable demos, plus the multi-backend fan-out. Every captured attribute in the talk comes from here. |
| **[`demos/RUNBOOK.md`](demos/RUNBOOK.md)** | **How to run the demos on stage** — steps, what to notice in each span, failure modes, timings. |
| **[`demos/ANALYSIS.md`](demos/ANALYSIS.md)** | The measurements, with versions and dates. The talk's evidence base. |
| **[`research.md`](research.md)** | Deep research on agent forensics (sourced, adversarially verified). |
| **[`research-evaluations.md`](research-evaluations.md)** | The same for evaluations and LLM-as-a-judge. |
| **[`landscape.md`](landscape.md)** | The visualization/normalization landscape and the Jaeger roadmap. |
| **[`resources.md`](resources.md)** | Annotated links — conventions, tools, backends, CNCF projects. |
| **`docs/superpowers/`** | The design specs and implementation plans the demos and deck were built from. History, not live documentation. |

---

## Run the deck

```bash
cd presentation
./start.sh
```

Serves locally and opens **two** windows: the deck and a speaker-notes follower (current
note · next note · clock · timer). Put the deck on the projector, notes on your laptop.

- Navigate: `←` `→` · Space · `Home`/`End` · number keys · `R` resets.
- Fully offline-safe — fonts are vendored under `presentation/fonts/`.
- **Before committing slide changes:** `python3 check-deck.py` (exits non-zero on
  violation) and open `audit-layout.html`, which measures real geometry and reports
  overflow, text-on-text collisions, text sitting on a panel, and text under the footer.

The checker covers only the mechanically checkable rules — a `data-label` per slide, no
list elements, no raw hex outside inline `<svg>`, at most one amber emphasis and one mascot
per slide, notes count matching slide count, no pure white or black. The type ramp, mascot
placement and layout budgets are on the author. See
[`presentation/README.md`](presentation/README.md) and
[`presentation/LAYOUTS.md`](presentation/LAYOUTS.md).

---

## Run the demos

Start with **[`demos/RUNBOOK.md`](demos/RUNBOOK.md)** if you are preparing to present.

| Demo | What it shows | Beats |
|---|---|---|
| **[`demos/capybara-sre/`](demos/capybara-sre/)** | A Quarkus + LangChain4j agent that deletes production records. `CAPYBARA_TOOLS=local\|mcp` switches how its tools are registered — the same binary, one variable, and only one of the two paths records what the tool actually did. Plus an LLM-as-a-judge attaching `gen_ai.evaluation.result` events. | 4, 6, 7 |
| **[`demos/agent/`](demos/agent/)** + **[`demos/normalizer/`](demos/normalizer/)** | One Python agent whose instrumentation library is selected by `CAPYBARA_INSTRUMENTATION=openlit\|openinference`, and the collector's `gen_ai_normalizer` rewriting the foreign vocabulary in flight. | 5 |
| **`demos/`** (fan-out) | One agent → one collector → Jaeger, Phoenix, OpenLIT and Langfuse side by side. The "same bytes, four renderings" comparison. | 2 |

**Each demo isolates exactly one variable, with one environment variable.** That symmetry
is the point: if two runs differ in more than one respect, "the collector fixed it" is a
coincidence, not a finding.

### Prerequisites

Docker, Python 3.11+, JDK 21, and an **Anthropic API key**.

```bash
cd demos
cp .env.template .env          # then set ANTHROPIC_API_KEY=sk-ant-...
```

> **Secrets:** `demos/.env` is git-ignored. Only `demos/.env.template` is committed.

---

## Working in this repo

- Every claim on a slide is either measured in `demos/ANALYSIS.md` or flagged on the slide
  as a position. If you change a claim, change the measurement or the flag with it.
- `demos/ANALYSIS.md` records dates and versions, and marks superseded captures rather than
  overwriting them — the talk says "we measured this", so the audit trail matters.
- The deck's speaker notes carry the guardrails: which numbers are real, which are the
  spec's shape rather than our capture, and what not to overclaim.
