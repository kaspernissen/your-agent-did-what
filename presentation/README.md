# Presentation — *Your Agent Did What?*

A 30-minute talk deck built on Kasper's **`<deck-stage>`** HTML framework (same engine as
the PlatformCon London deck), recolored **blue → purple**, no vendor logo.

```
presentation/
  index.html          # THE DECK — <section> slides + speaker-notes JSON
  deck.css            # theme (copied from the deck framework, recolored)
  deck-stage.js       # the deck web component (auto-scaling, nav, notes)
  notes.html          # speaker-notes follower window
  start.sh            # serve + open deck / notes
  assets/             # tool logos (drop the icons here — see below)
  README.md
```

## Run it

```bash
./start.sh
```

Opens a local server and the **deck** + the **speaker-notes follower** in your browser.
Drag the notes tab to your laptop screen, deck to the projector.

- **Navigate:** `←` `→` · Space · PageUp/Down · `Home`/`End` · number keys · `R` resets.
- **Speaker notes:** they live in the separate `notes.html` window (current note, next
  note, clock, elapsed timer). It follows the deck automatically (same browser, served
  over HTTP). This is how notes are shown — not on the slides themselves.
- **Fills the screen:** `deck-stage` renders a fixed 1920×1080 canvas and scales it to fit
  the viewport (letterboxed), so it always fills the screen at any resolution.

## Export to PDF

`deck-stage` lays out one slide per page for print:
`./start.sh` → in the deck window, **Print** → **Save as PDF** (margins None, background graphics on).

## Editing

- One slide = one `<section>` directly inside `<deck-stage>`.
- **Speaker notes** = the `<script id="speaker-notes" type="application/json">` array near the
  bottom — **one string per slide, in order** (count must equal the number of `<section>`s).
  The verbatim opening script is entry 1; Q&A pre-loads are the last entry.
- Slide kinds: default (light), `class="dark"`, `class="ink"` (near-black); `center-all` to center.
- Layout classes come from `deck.css`: `.display`, `.t-h1/h2/h3`, `.t-lead`, `.bullets`,
  `.ol-big`, `.card` + `.grid .g-2…g-7`, `.stat`, `.lchev` (the maturity chevrons),
  `.ba-row` (before/after), `pre.code`, `.quote`. Custom bits (`.yflow`, `.ynode`, `.attrk`,
  `.umock`) are appended at the end of `deck.css`.
- Recolor: the blue/purple override block is at the bottom of `deck.css` (`--grad`, the
  `--red-*`/`--orange-*` palette remap). Change it there.

## Tool logos

The ecosystem cards + the OTel-substrate slide load logos from `assets/`. Drop these in
(transparent PNG; white/icon-only variants read best on the dark slides):

```
assets/agentgateway.png   assets/holmesgpt.png   assets/kagent.png
assets/k8sgpt.png         assets/otel.png
```

Missing files fail gracefully (the `<img>` hides itself).

## Structure (≈30 min)

| Part | Beat |
|---|---|
| Cold open (title) | the 3am "why did it do that?" |
| 1 · Agents aren't request/response | four properties + the signal-equivalents map |
| 2 · What that does to your traces | context loss · 275-span trace · skills break traces |
| 3 · The fragmentation problem | five conventions · **measured drift** · backend spectrum |
| 4 · Bridging the gap | gen_ai_normalizer · Arconia · "correlation fails" |
| 5 · The forensics payoff | new MTTR · reasoning span · **opt-in forensic content** · gaps |
| 6 · Where this is going | OTel substrate · maturity ladder · ecosystem · CTA |

Grounded in `../outline.md`, `../research.md`, `../landscape.md`, and the **measured** data in
`../demos/ANALYSIS.md`. Demo slides (3–5) are written for **recorded clips** of `../demos/`
plus the captured attribute blocks.
