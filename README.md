# Your Agent Did What?

**Forensic Observability for Systems That Don't Leave Obvious Footprints**
Conference talk by **Kasper Borg Nissen** & **Adriana Villela** — on OpenTelemetry, GenAI semantic conventions, and observing autonomous agents.

> The GenAI observability space is fragmented — OpenInference, OpenLLMetry, framework-specific
> conventions all naming the same things differently. OpenTelemetry is where it converges.
> This talk maps that landscape honestly, shows how to bridge the gap at the collector
> (`gen_ai_normalizer`) and the SDK (Arconia), and then asks the harder question: your agent
> just deleted a database — what does your telemetry actually tell you?

---

## What's in here

| Path | What it is |
|---|---|
| **`abstract.md`** | The talk abstract + ecosystem benefits. |
| **`outline.md`** | The 30-minute talk outline (timing, beats, source-deck map). |
| **`presentation/`** | The **slide deck** (HTML, reveal-free `<deck-stage>` framework) + speaker notes. |
| **`presentation-trace/`** | The **Trace rebuild** of the deck — new design system + conformance checker, scaffold only (2 slides) so far. |
| **`research.md`** | Deep research on agent forensics (sourced, adversarially verified). |
| **`landscape.md`** | The visualization/normalization landscape + the Jaeger roadmap. |
| **`resources.md`** | Annotated links (conventions, tools, backends, CNCF projects). |
| **`demos/`** | Runnable demos — the captured data behind the talk's claims. |
| **`demos/ANALYSIS.md`** | The measured findings (attribute tables, normalizer before/after, Arconia flavor diff). |
| **`docs/superpowers/`** | Design spec + implementation plan for the demos. |

---

## Run the slide deck

Two decks live in this repo:

| Deck | What it is |
|---|---|
| **`presentation/`** | The **current, presentable 48-slide deck** — what you'd actually show at the conference today. |
| **`presentation-trace/`** | The **Trace rebuild in progress** — a new design system + conformance checker, but only **2 scaffold slides** so far (cover + a "kitchen sink" of every layout primitive). The talk's real 39 slides land in a later plan; this deck does not yet carry the talk content. Kept alongside `presentation/` until it supersedes it. |

Both use the same `<deck-stage>` framework and the same run/navigate pattern:

```bash
cd presentation          # or: cd presentation-trace
./start.sh
```

Serves locally and opens **two** windows: the **deck** and a **speaker-notes follower**
(current note · next note · clock · timer). Drag the notes window to your laptop screen, put
the deck on the projector.

- Navigate: `←` `→` · Space · `Home`/`End` · number keys · `R` resets.
- Both decks vendor their engine, but only **`presentation-trace/`** is fully offline-safe
  (fonts vendored under `presentation-trace/fonts/` too). **`presentation/`** still fetches
  Roboto and Martian Mono live from `fonts.googleapis.com`/`fonts.gstatic.com` — presenting
  it offline loses the title and mono faces.
- `presentation-trace/` also ships `check-deck.py` — run `python3 check-deck.py` from
  inside it before committing slide changes; it enforces the Trace design-system rules
  (one amber emphasis per slide, no bullets, one chamfered corner, mascot placement, no
  pure white/black) and exits non-zero on violation.
- More detail: [`presentation/README.md`](presentation/README.md) ·
  [`presentation-trace/README.md`](presentation-trace/README.md).

---

## Run the demos

The demos are the source of every captured attribute in the talk. Three of them:

| Demo | What it shows |
|---|---|
| **`demos/`** (root) | One tool-calling Claude agent → one collector → **fanned out to Jaeger, Phoenix, OpenLIT, Langfuse** (and optional Dash0 / OpenSearch). |
| **`demos/normalizer/`** | The `gen_ai_normalizer` collector processor rewriting OpenInference → OTel GenAI semconv. |
| **`demos/arconia/`** | A Spring AI app where flipping one property re-emits spans under a different convention. |

### Prerequisites

- Docker, Python 3.11+, an **Anthropic API key**. (Demo 3 also needs JDK 21.)

```bash
cd demos
cp .env.template .env          # then set ANTHROPIC_API_KEY=sk-ant-...
./00_run.sh                    # brings up the backends, runs the agent, prints the UIs
./01_cleanup.sh                # tears everything down
```

See [`demos/README.md`](demos/README.md) for the full walkthrough, the three "questions"
the harness answers, and the per-UI guide.

> **Secrets:** `demos/.env` (your real key) is git-ignored. Only `demos/.env.template`
> (placeholders) is committed.

---

## Working in this repo

- **Commits are made by the repo owner** — tooling here stages changes but does not commit.
- The deck content is grounded in `research.md`, `landscape.md`, and the **measured** data in
  `demos/ANALYSIS.md` — not assumptions.
