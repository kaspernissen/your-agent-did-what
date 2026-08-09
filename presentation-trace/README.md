# Presentation-Trace — *Your Agent Did What?*

The **Trace** rebuild of the conference deck for *Your Agent Did What? — Forensic
Observability for Systems That Don't Leave Obvious Footprints*, by **Kasper Borg Nissen**
(`@phennex`) and **Adriana Villela** (`@adrianamvillela`). 30 minutes, two speakers.

> **Status: foundation only.** `index.html` currently holds **two** slides — a cover and a
> "Kitchen sink" slide that demonstrates every layout primitive the design system provides.
> The talk's actual 39 slides (mapped beat-by-beat in `../outline.md`) land in a later plan.
> Don't expect a presentable talk here yet — expect the scaffold it gets built on.

```
presentation-trace/
  index.html          # the deck — <section> slides + speaker-notes JSON (2 slides so far)
  trace.css           # the Trace design tokens + layout primitives
  check-deck.py        # conformance checker — run before committing slide changes
  test-check-deck.py   # its test suite (8 tests)
  deck-stage.js        # the deck web component (auto-scaling, nav, notes) — copied from presentation/
  notes.html           # speaker-notes follower window — copied from presentation/
  start.sh             # serve + open deck / notes
  fonts/               # vendored woff2 files + fonts.css + fetch-fonts.sh
  assets/              # mascot + diagram assets
```

## Run it

```bash
cd presentation-trace
./start.sh
```

Serves locally and opens **two** windows: the **deck** and a **speaker-notes follower**
(current note · next note · clock · elapsed timer). Drag the notes window to your laptop
screen, put the deck on the projector.

- **Navigate:** `←` `→` · number keys jump to a slide · `R` resets.
- **Offline-safe:** fonts are vendored under `fonts/` (see `fonts/fetch-fonts.sh` if they
  ever need re-fetching) — the deck needs no network to run.

## Before committing slide changes

```bash
python3 check-deck.py
```

Exits `0` when the deck conforms, `1` otherwise, printing one `✗ ...` line per violation.
It mechanically enforces the rules below wherever they're checkable, so drift is caught by
a command instead of by eye. `test-check-deck.py` (`python3 -m unittest test-check-deck.py`)
covers the checker itself.

## The non-negotiable rules

The design system (**Trace**, spec §10) is a signal axis with content hanging off it as
nodes and span bars — nothing gets boxed in. A few rules are load-bearing and the checker
enforces what it can:

- **One amber emphasis per slide, never two.** Marked with `data-emphasis="amber"`.
- **No bullets.** `.span-bar` and `.axis-list` replace `<ul>`/`<ol>`/`<li>` — the checker
  rejects any of the three tags outright.
- **One chamfered corner.** `.chamfer` cuts exactly the **top-right** corner. Never four
  rounded corners — that's a different design language.
- **The capybara mascot** appears only on the cover, the close, and at most **one**
  mid-deck moment — never on a data slide, never below 90px, never twice on the same slide.
- **No pure white, no pure black.** `trace.css` uses `--paper`/`--ink`, not `#fff`/`#000` —
  checked against both the CSS and, for slide markup, any raw hex at all (tokens only).
- **Amber text below 40px uses `--amber-text` (`#8A5B00`);** `--amber-lift` (`#FFC842`) is
  for ink grounds only. The rule keys off **what surface the text sits on**, not the
  slide's `.ground-*` class: text inside a `.code-block` always sits on that block's own
  near-black panel, so it always takes `--amber-lift` regardless of the slide's ground —
  two implementers got this backwards before, so it's written down here.

## Where things come from

- `outline.md` (repo root) — the nine-beat, 39-slide talk arc this deck will fill in.
- `../presentation/` — the current, presentable 48-slide deck. Untouched by this rebuild;
  read it as source material, don't edit it.
- `docs/superpowers/` (repo root) — the design spec and implementation plans behind both
  the Trace system and the talk content.
