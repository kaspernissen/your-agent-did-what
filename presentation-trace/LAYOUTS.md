# Trace layouts L01–L08

The eight slide layouts of the **Trace** design system, authored at **1920 × 1080**
(`deck-stage` scales the whole slide, so every number here is a literal pixel value at
authoring size). `outline.md` names one of these on all 39 slides — this file is what
those names mean.

**Origin.** Transcribed from the design system's own reference sheet, vendored in-repo at
[`design-system/OTel Talk System.dc.html`](design-system/OTel%20Talk%20System.dc.html)
(§06 "Slide layouts"), which is the authority if this file and it ever disagree. The
sheet is a *reference document*, not part of the deck: the deck never loads it, and
unlike the deck it does link out to `fonts.googleapis.com` and expects a `./support.js`
runtime shim that was not vendored, so it renders as static HTML with fallback faces. Its
`assets/` is a symlink to `../assets/` — the five files it references are byte-identical to
the ones the deck already ships. The spec's summary of the same system is
`docs/superpowers/specs/2026-08-07-talk-scope-deck-and-two-demos-design.md` §10.

**The idea.** A trace is a line with events on it. Every slide hangs off one horizontal
**signal axis** (`.axis`) and content attaches to it as **nodes** (`.axis-node`, circles)
and **spans** (`.span-bar`, stadium bars). Nothing gets boxed in. Where a surface is
genuinely needed it takes the 45° chamfer (`.chamfer`) — **one** corner cut, top-right,
never four rounded corners. Slide margins are `--pad-x: 120px`.

---

## Budgets

| Layout | Budget | Used in `outline.md` |
|---|---|---|
| **L01 Cover** | **exactly once** | 1 |
| **L02 Section divider** | one per beat transition | 7 |
| **L03 Statement** | **use sparingly — twice a talk** | 2 |
| **L04 Text + diagram** | the workhorse, no budget | 14 |
| **L05 Waterfall** | the signature slide; save it | 2 |
| **L06 Code** | no budget | 7 |
| **L07 Figures** | no budget | 5 |
| **L08 Close** | **exactly once** | 1 |

Two more budgets cut across all eight, and neither is machine-checked beyond a count
(see `README.md` → "The checker verifies these" / "These are on you"):

- **One amber emphasis per slide, never two.** Amber marks the one thing the room should
  read first. The checker counts `data-emphasis="amber"` markers; it cannot tell whether
  the marker is on the right element.
- **The mascot** (`.mascot`) appears on the cover, the close, and at most **one** mid-deck
  breath. Never on a data slide (so: never on L05 or L07), never below 90px, never twice
  on a slide. It sits *on* the axis like any other node, not floating above it.

---

## L01 — Cover

**Ground:** ink (`.ground-ink`), with an ink→navy gradient and a darker navy field clipped
into a diagonal down the right ~46%.

**Structure.** OTel logo top-left (120, 92; 54px tall). Text block at (120, 262):
`.kicker` → `.title` (the cover runs it at **110px**, above the ramp's 96) → a 44px
`--blue-mute` subtitle line. A full-bleed `.axis` at **y = 786**. Speaker names and
handles in a row at (120, 836) — Space Grotesk 38px over mono 24px `--on-ink-dim`.
`.mascot` at the right, 322px wide, its feet on the axis.

**Amber.** The **first speaker's `.axis-node.is-amber`** (34px, at x = 214) — the two
speakers are literally nodes on the trace, and one of them is the amber one. The `.axis`
gradient's amber tail is part of the axis primitive, not a second emphasis. The second
speaker's node is `--blue-lift`, 22px.

**Employer marks.** A small mono mark sits beside each speaker's handle in the (120, 836)
row — Dash0 for Kasper, Dynatrace for Adriana. Cap them at **28px tall**, half the OTel
logo's 54px: this is affiliation, and it must never compete with the community mark above
it. They carry no colour of their own and introduce no second amber. See
*Employer marks* at the end of this file.

**Primitives:** `.ground-ink` · `.kicker` · `.title` · `.axis` · `.axis-node` (`.is-amber`)
· `.mascot` · `.diagonal-split` (for the right-hand field) · `.employer-mark`.

---

## L02 — Section divider

**Ground:** ink, with an **amber flood** poured into `.diagonal-split` (`polygon(0 0, 58% 0,
42% 100%, 0 100%)` — the system's ~72° diagonal). **This is the only place amber fills a
slide.**

**Structure.** On the amber field, left at (120, 300): the beat number as a Space Grotesk
numeral at **220px / weight 600 / line-height .9** in `--ink`, then the section title at
86px, also `--ink`. On the ink side, right at (120 from the right edge, 300): a `.kicker`
("Up next") in `--on-ink-dim`, then the beat's slides as 36px lines — the one you are
entering in `--paper`, the rest in a dim navy. **No `.axis` on this layout** — the diagonal
is the event.

**Amber.** The flood *is* the emphasis. Nothing else on the slide takes amber.

**Primitives:** `.ground-ink` · `.diagonal-split` · `.kicker` · display type. No `.axis`,
no `.mascot`.

---

## L03 — Statement

**Ground:** paper (`.ground-paper`). One sentence, axis underneath. **Use sparingly —
twice a talk.**

**Structure.** `.kicker` at (120, 150). One sentence as an oversized `.title` at
(120, 280), **104px**, running to 1520px wide. An **inset** `.axis` at y = 800 (left and
right both 120px, so it starts and stops rather than bleeding), with an `.axis-node` at
each end: blue at the left, `.is-amber` at the right. A `.small` caption at (120, 860),
under the axis — the line that does the honest qualifying.

**Amber.** The **operative clause inside the sentence**, wrapped in `.amber-text`. On paper
that resolves to `--amber-text` (#8A5B00) even at 104px, which is what the reference sheet
does; the terminal `.axis-node.is-amber` reads as the same emphasis landing on the axis.

**Primitives:** `.ground-paper` · `.kicker` · `.title` · `.amber-text` · `.axis` ·
`.axis-node` (`.is-amber`) · `.small`.

---

## L04 — Text and diagram

**Ground:** paper. The workhorse: axis list at left, diagram at right.

**Structure.** `.title` at (120, 120), 72px, 1200px wide. `.axis-list` at (120, 360),
760px wide, holding three `.axis-list-item`s. At the right, a **`--paper-2` panel** at
(120 from the right, 300), 800 × 540, wearing `.chamfer` (the sheet cuts 48px on this
panel), with the diagram aspect-fit inside it (`max-width/max-height: 100%;
object-fit: contain`) and 48px of padding. Attribution line bottom-right at y = 872 in
mono 24px, muted — community diagrams carry their licence.

**Amber.** The **one `.axis-list-item.is-amber`** — its node dot goes amber, the text does
not. The other two items keep blue dots.

**Primitives:** `.ground-paper` · `.title` · `.axis-list` / `.axis-list-item` (`.is-amber`)
· `.chamfer` · `.small` (attribution).

> Inline `<svg>` diagrams are exempt from `check-deck.py`'s no-raw-hex rule — see
> `README.md`. Artwork carries its own palette; slide chrome does not.

---

## L05 — Waterfall

**Ground:** ink. **The signature slide. One amber span carries the point.** Never carries
the mascot — it is a data slide.

**Structure.** `.title` at (120, 110), 72px. `.waterfall` spanning the margins at y = 340,
26px between rows. Each `.wf-row` is `.wf-label` (300px, mono 26px, right-aligned) ·
`.wf-track` holding one `.wf-bar` positioned by `--x` and `--w` · `.wf-dur` (150px, mono
26px). Non-emphasis bars step down through `.wf-bar` (blue), `.is-blue-lift` and
`.is-blue-mute` so depth reads without colour drift. Below the rows: a hairline rule
aligned to the **track** start (left: 452px = 120 + 300 label + 32 gap) at y = 790, and at
y = 820 a legend line — a 14px amber dot plus the one attribute that carries the point
(`gen_ai.usage.output_tokens = 1,840` in the sheet).

**Amber.** The **single `.wf-row.is-amber`**: `.wf-bar.is-amber`, and its `.wf-label` /
`.wf-dur` lift with it. On ink those become `--amber-lift`; on paper, `--amber-text`.
(`.wf-label` / `.wf-dur` are ground-qualified in `trace.css` — `--muted-ink` on paper,
`--on-ink-dim` on ink.)

**Primitives:** `.ground-ink` · `.title` · `.waterfall` / `.wf-row` / `.wf-label` /
`.wf-track` / `.wf-bar` (`.is-amber`, `.is-blue-lift`, `.is-blue-mute`) / `.wf-dur`.

---

## L06 — Code

**Ground:** ink. One code panel, one amber highlight.

**Structure.** `.title` at (120, 110), 68px. `.code-block` spanning the margins at y = 300
— its own near-black `#080B1E` panel with a 44px chamfer. (The sheet's own caption calls
this a "right-angled block", following the system's *right angles are reserved for imagery
and code*; the markup it ships chamfers it, and `trace.css` `.code-block` follows the
markup.) Inside, `.code-block pre` at mono 34px / 1.9 in `--on-ink`, coloured with
`.c-key`, `.c-attr` and `.c-str`. At (120, 840): a `.tag.is-solid` plus a `.small` caveat —
this is where "Experimental" lives.

**Amber.** Pick **one**: either the `.tag.is-solid` (amber fill) or the highlighted string.
Note that `.c-str` inside `.code-block` is always `--amber-lift` regardless of the slide's
ground, because it sits on the block's own near-black panel — that is the code block's
palette, not the slide's emphasis. Put the `data-emphasis="amber"` marker on whichever one
you actually mean.

**Primitives:** `.ground-ink` · `.title` · `.code-block` (+ `.c-key` / `.c-attr` /
`.c-str`) · `.tag.is-solid` · `.small`.

---

## L07 — Figures

**Ground:** paper. **Three stats hung off the axis. No cards.** A data slide — no mascot.

**Structure.** `.kicker` at (120, 130), `.title` at (120, 210) at 72px. A three-column grid
across the margins at y = 440, 80px gutters, each column a `.stat`: `.stat-figure` (Space
Grotesk 132px) → a 26px `.axis-node` → `.stat-label` (32px, weight 300). An inset `.axis`
at **y = 600** with a symmetric `--blue-mute` fade. The geometry is the point: the figures
end at ~572 and their nodes land at ~603, so the three stats **sit on the axis** rather
than floating in a grid.

**Amber.** Exactly **one** of the three nodes is `.axis-node.is-amber` — the figure that
matters. The other two stay blue.

**Primitives:** `.ground-paper` · `.kicker` · `.title` · `.stat` / `.stat-figure` /
`.stat-label` · `.axis` · `.axis-node` (`.is-amber`).

---

## L08 — Close

**Ground:** ink, with a 160° ink→navy gradient. **Exactly once.**

**Structure.** A full-bleed `.axis` at y = 706, weighted amber across its middle. `.mascot`
at (1180, 490), 270px wide — **sitting on the axis**, which is the rule stated as a
picture. `.title` at (120, 220), 104px, 1000px wide. Below the axis at (120, 800): the
canonical link in mono 30px `--amber-lift`, then the two speaker handles in mono 28px
`--on-ink-dim`. At the right, (120 from the right, 220): a 300 × 300 `--paper` panel with
`.chamfer` holding the slides QR.

**Amber.** The **link line** in `--amber-lift` (on ink, so lift is correct), with the
axis's amber run underneath it pointing at it.

**Employer marks.** Same treatment as L01 — beside the two handles at (120, 800), 28px
tall. They must not sit near the amber link line: the link is this slide's one emphasis
and the marks are the quietest thing on it.

**Primitives:** `.ground-ink` · `.title` · `.axis` · `.mascot` · `.chamfer` · mono link and
handles · `.employer-mark`.

> Per spec §10.3, the close link must point at the **`semantic-conventions-genai`** page.
> The reference sheet's `opentelemetry.io/docs/specs/semconv/gen-ai` is now only a redirect
> notice — do not copy it verbatim.

---

## Employer marks

The two speakers' employers appear **only on L01 Cover and L08 Close** — nowhere else.
This is a deliberate limit, not an oversight. The design system's own header states
*"Vendor-neutral · community marks only"*, and beats 2 and 3 argue for a vendor-neutral
standard; a vendor mark sitting on those slides would undercut the argument being made on
them. Bookends read as affiliation and disclosure, which is what they are.

Rules:

- **28px tall, maximum** — half the OTel mark's 54px on the cover.
- **Monochrome only.** No brand colours. They must not read as a second amber emphasis,
  and neither slide has an emphasis to spare: L01's is the first speaker's amber node,
  L08's is the link line.
- **Never on a content slide**, never on a data slide, never in a section divider.
- Both bookends are **ink grounds**, so both marks must be legible on `#10142E`.

### Assets

| Mark | File | Status |
|---|---|---|
| Dash0 | `assets/dash0-logo.svg` | **Present.** Vendored from the dash0-website repo (`public/shared/logo_bw.svg`). It paints with `fill="currentColor"`, so it inherits whatever `color` the slide sets — one file works on ink and paper alike. |
| Dynatrace | `assets/dynatrace-logo-white.svg` | **MISSING — must be supplied before L01/L08 are built.** |

The Dynatrace mark needs the **white** variant for both bookends, because both are ink
grounds and the black wordmark is invisible on `#10142E`. If a paper-ground use ever
appears, add the black variant as `assets/dynatrace-logo-black.svg` rather than
recolouring the white one.

Do not substitute a redrawn or re-typeset wordmark for either company's official mark.

### The `.employer-mark` class

Not yet in `trace.css` — it is added by the task that builds L01. It should set the height
cap and inherit colour, roughly:

```css
.employer-mark{height:28px;width:auto;color:var(--paper)}
.ground-paper .employer-mark,.ground-paper-2 .employer-mark{color:var(--ink)}
```

`color` is what drives the Dash0 mark (via `currentColor`); the Dynatrace mark is a fixed
white file and ignores it, which is why the black variant is a separate asset rather than
a CSS switch.
