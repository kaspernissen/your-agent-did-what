# Presentation-Trace — *Your Agent Did What?*

The **Trace** rebuild of the conference deck for *Your Agent Did What? — Forensic
Observability for Systems That Don't Leave Obvious Footprints*, by **Kasper Borg Nissen**
(`@phennex`) and **Adriana Villela** (`@adrianamvillela`). 45 minutes, two speakers.

> **Status: built.** `index.html` holds all **40 slides** across the nine beats mapped in
> `../outline.md`, each with a speaker note. Three slides deliberately show structure
> without data — the beat-6 waterfall's durations, the "what you get for free" attribute
> values, and the evaluation event's values — because Demo 1 and its judge do not exist
> yet. Those carry `[NEEDS SOURCE]` markers in `../outline.md`; fill them from a real run
> rather than plausible numbers.

```
presentation-trace/
  index.html          # the deck — <section> slides + speaker-notes JSON (2 slides so far)
  trace.css           # the Trace design tokens + layout primitives
  LAYOUTS.md          # the eight layouts L01–L08 that outline.md names on every slide
  check-deck.py        # conformance checker — run before committing slide changes
  test-check-deck.py   # its test suite (11 tests)
  deck-stage.js        # the deck web component (auto-scaling, nav, notes) — copied from presentation/
  notes.html           # speaker-notes follower window — copied from presentation/
  start.sh             # serve + open deck / notes
  fonts/               # vendored woff2 files + fonts.css + fetch-fonts.sh
  assets/              # mascot + diagram assets
  design-system/       # the vendored design-system reference sheet LAYOUTS.md is drawn from
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
- **Offline-safe:** the seven woff2 files under `fonts/` are vendored and committed — the
  deck needs no network to run. `fonts/fetch-fonts.sh` regenerates them if they are ever
  lost; it derives the filenames from `fonts.css`, writes nothing unless all seven resolve,
  and fails loudly otherwise.

## The eight layouts

`../outline.md` names a layout (`L01`–`L08`) on all 39 slides. **[`LAYOUTS.md`](LAYOUTS.md)**
defines them: ground, structure, where the amber emphasis goes, which `trace.css`
primitives compose each one, and the per-layout budgets. It is transcribed from the
design system's own reference sheet, vendored at
`design-system/OTel Talk System.dc.html`, which stays the authority.

## Before committing slide changes

```bash
python3 check-deck.py
```

Exits `0` when the deck conforms, `1` otherwise, printing one `✗ ...` line per violation.
`test-check-deck.py` (`python3 test-check-deck.py -v`) covers the checker itself.

**`✓ deck conforms` is not a claim that the deck is on-system.** The checker enforces a
narrow, mechanical subset of the Trace rules. Everything else is on you. The two lists
below are exhaustive — if a rule is in the second list, no command will catch you breaking
it.

### The checker verifies these

Read `check-deck.py` if you doubt any of them; each maps to one block in `check_deck()`.

- **At least one `<section>`.** It looks inside `<deck-stage>` when that element is
  present, and falls back to scanning the whole document when it is not — so a deck
  missing its `<deck-stage>` wrapper entirely still passes this check.
- **Every slide has a `data-label`.**
- **No bullets** — any `<ul>`, `<ol>` or `<li>` in slide markup is rejected outright.
  `.span-bar` and `.axis-list` are what replace them.
- **No raw hex in slide markup** — any `#rrggbb` in a slide's attributes or content is
  rejected, so colour comes from `trace.css` tokens. **Exception: inline `<svg>` subtrees
  are exempt** (see below).
- **At most one `data-emphasis="amber"` marker per slide.** It counts markers only; it
  cannot tell whether the marker is on the element you actually meant to emphasise, and it
  is happy with a slide that has none.
- **At most one element whose `class` contains `mascot` per slide.**
- **Speaker notes**: a parseable `<script id="speaker-notes">` whose array length equals
  the slide count. It matches on the `id` alone — the `type="application/json"` attribute
  is convention here, not something the checker verifies.
- **No pure white or black in `trace.css`** — no `#fff`, `#ffffff`, `#000`, `#000000`.

#### Why inline `<svg>` is exempt from the hex rule

The no-raw-hex rule exists to stop colour drift in **slide chrome**. An inline `<svg>`
diagram is **artwork**: it carries its own palette, often lifted verbatim from a source
deck — `outline.md`'s beat-2 row tells the builder to lift the five provider/attribute
pairs out of `presentation/index.html:292-296`, which is ~15 raw hex values in one `<svg>`.
Rather than have the next author weaken the rule to get that slide in, `<svg>…</svg>`
subtrees are stripped before the hex scan (several per slide and nested `<svg>`s included;
an *unclosed* `<svg>` is left in so its hex still gets flagged). Everything outside an
`<svg>` stays strictly governed. This is settled — please don't re-litigate it. Two
consequences worth naming: the "no pure white/black" rule is enforced against `trace.css`
only, so `fill="#fff"` inside vendored artwork will pass; and an SVG's palette is your
responsibility to keep on-system by eye.

### These are on you

The checker says nothing about any of the following. They are the rest of the design
system (**Trace**, spec §10 — a signal axis with content hanging off it as nodes and span
bars, nothing boxed in), and breaking one still ships.

- **The type ramp.** title 96/1.02 · subtitle 52/1.25 · body 34/1.45 · small 28/1.4 (the
  projector floor) · kicker 26/.2em. Layouts legitimately deviate — see `LAYOUTS.md`.
- **Never bolder than 600.** Space Grotesk at 500/600, Public Sans at 300/400/600.
- **Corner treatment.** The Trace system specifies a 45° chamfer — one corner cut, never
  four rounded. **The speaker has overridden this for the big surfaces:** `.chamfer` and
  `.code-block` now use `border-radius`. The angled cut survives on `.tag`, where it reads
  as a detail rather than a container. `trace.css` carries the original polygons in a
  comment if this is ever reverted. There is no check either way.
- **Mascot placement.** The capybara appears only on the cover, the close, and at most
  **one** mid-deck breath; never on a data slide (so never on L05 or L07); never below
  **90px**; and it *sits on* the axis rather than floating above it. The checker only
  refuses **two on one slide** — it will pass a 40px mascot parked on the beat-6 waterfall.
- **The ~72° diagonal** for section dividers and before/after comparisons
  (`.diagonal-split`).
- **Amber text below 40px uses `--amber-text` (`#8A5B00`);** `--amber-lift` (`#FFC842`) is
  for ink grounds only. The rule keys off **what surface the text sits on**, not the
  slide's `.ground-*` class: text inside a `.code-block` always sits on that block's own
  near-black panel, so it always takes `--amber-lift` regardless of the slide's ground —
  two implementers got this backwards before, so it's written down here.
- **Layout budgets.** L01 and L08 appear **exactly once**; **L03 Statement is "use
  sparingly — twice a talk"**; L02 is one per beat transition. `LAYOUTS.md` has the table.
- **Whether the amber emphasis is on the right thing**, and whether a slide that needs one
  has one at all.

## Where things come from

- `design-system/OTel Talk System.dc.html` — the design system's own reference sheet, the
  authority behind `LAYOUTS.md` and `trace.css`. Vendored so it is never a temp directory
  again. It is a reference *document*, not part of the deck: the deck never loads it, and
  it does link out to Google Fonts, unlike the deck. (`start.sh` serves the whole
  directory, so it is reachable in a browser — it just is not part of the presentation.)
- `outline.md` (repo root) — the nine-beat, 39-slide talk arc this deck will fill in.
- `../presentation/` — the previous 48-slide deck. Removed 2026-08-10 once the lift was complete;
  read it as source material, don't edit it.
- `docs/superpowers/` (repo root) — the design spec and implementation plans behind both
  the Trace system and the talk content.

### Layout audit

`check-deck.py` reads markup and cannot see geometry, so text overflowing a slide or
printing on top of other text passes it. Two such bugs reached the speaker before this
existed. `audit-layout.html` closes that gap: it renders every slide at its authored
1920×1080, unscaled, and measures real bounding boxes.

```bash
python3 -m http.server 8000 &
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu --virtual-time-budget=12000 \
  --dump-dom http://localhost:8000/audit-layout.html | grep -A99 '<pre id="out">'
```

It reports two classes — `OVERFLOW` (text past the slide bounds) and `OVERLAP` (two text
elements on the same pixels) — with the slide number, its label, and the offending text.
Verified by planting a deliberate overflow and a deliberate collision and confirming both
are caught; a silent audit would be worse than none.
