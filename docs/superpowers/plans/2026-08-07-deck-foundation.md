# Deck Foundation Implementation Plan

> **Path note (2026-08-11):** this document says `presentation-trace/`. That directory was
> renamed to `presentation/` once the old deck was removed and it became the only one.
> The text below is left as written — it is a record of the design at the time.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up `presentation-trace/` — a new, self-contained deck built on the "Trace" design system, with a machine-checkable conformance harness and a restructured nine-beat outline that the content plan will draw its slides from.

**Architecture:** The deck reuses the existing `<deck-stage>` web component, which already authors at 1920×1080 — the exact size the design system is drawn at. Design tokens and layout primitives live in one stylesheet (`trace.css`) so slide markup carries no raw colors or geometry. A Python conformance checker enforces the design system's rules mechanically, so drift is caught by a command rather than by eye.

**Tech Stack:** Static HTML/CSS + the vendored `deck-stage.js` web component; Python 3.11+ (stdlib only) for the conformance checker; `python3 -m http.server` for serving.

## Global Constraints

Copied verbatim from `docs/superpowers/specs/2026-08-07-talk-scope-deck-and-two-demos-design.md` §10. Every task's requirements implicitly include this section.

- **Grounds:** ink `#10142E`, paper `#FAF7F2`, paper-2 `#F2ECE0`.
- **Signal amber `#F5A800`: one emphasis per slide, never two.** Amber text below 40px must use `#8A5B00` instead — amber fails contrast on paper. Amber lift `#FFC842` is ink-ground only.
- **Structure blue `#425CC7`**; blue lift `#6E85E0`; blue mute `#A9B6EE`; deep navy `#202C5F`; muted ink `#5B6180`.
- **No pure white, no pure black.** The capybara's browns are mascot-only and never enter the interface palette.
- **Type:** Space Grotesk (display, 500/600, tracking −.025em, **never bolder than 600**); Public Sans (body, 300 long lines / 400 short); JetBrains Mono (code, attribute names, kickers, all-caps labels at .2em tracking).
- **Slide-scale type ramp:** title 96/1.02, subtitle 52/1.25, body 34/1.45, small 28/1.4 (the projector floor), kicker 26/.2em.
- **Geometry:** 45° chamfer, **one** corner cut (top-right), 40px at slide scale. Never four rounded corners. Section dividers split on a ~72° diagonal. Right angles reserved for imagery and code.
- **Span bars are the list primitive — they replace bullets.** No `<ul>`/`<ol>`/`<li>` in slide markup.
- **Mascot:** cover, close, and at most one mid-deck breath. Never on a data slide, never below 90px, never twice on a slide. Sits *on* the axis, not floating above it.
- **Title is "Your Agent Did What?"** — subtitle "Forensic Observability for Systems That Don't Leave Obvious Footprints". Speakers: Adriana Villela (`@adrianamvillela`) and Kasper Nissen (`@phennex`).
- **Fonts are vendored locally.** No Google Fonts requests at runtime — the deck must survive a conference network.
- **The existing `presentation/` deck is not modified by any task in this plan.**

---

## File Structure

| Path | Responsibility |
|---|---|
| `presentation-trace/index.html` | The deck: `<deck-stage>` + `<section>` slides + the speaker-notes JSON block |
| `presentation-trace/trace.css` | Design tokens and layout primitives. The only place colors and geometry are defined |
| `presentation-trace/deck-stage.js` | Presenter engine, copied verbatim from `presentation/` |
| `presentation-trace/notes.html` | Speaker-notes follower, copied verbatim from `presentation/` |
| `presentation-trace/start.sh` | Serves the deck and opens both windows, copied from `presentation/` |
| `presentation-trace/check-deck.py` | Conformance checker enforcing the Global Constraints |
| `presentation-trace/fonts/` | Vendored woff2 files + `fonts.css` `@font-face` block |
| `presentation-trace/fonts/fetch-fonts.sh` | One-shot script that downloads the woff2 files |
| `presentation-trace/assets/` | `capybara-mascot.png`, `otel-logo.svg`, `collector-pipeline.svg`, `data-sources.svg`, `signal-traces.svg` |
| `presentation-trace/README.md` | How to run, and the design-system rules in short form |
| `outline.md` | Rewritten to the nine-beat arc; the content plan's source |

**Bundle source path** (referred to below as `$BUNDLE`):
`/private/tmp/claude-501/-Users-kaspernissen-kaspernissen-your-agent-did-what/547b1c54-679d-45f5-9ba2-6b4498adabc4/scratchpad/design/opentelemetry-talk-design-system/project`

If that scratchpad has been cleared, re-extract it first:
```bash
mkdir -p /tmp/otel-ds && cd /tmp/otel-ds && \
  unzip -o "$HOME/Downloads/OpenTelemetry talk design system-handoff.zip"
```
and set `$BUNDLE` to `/tmp/otel-ds/opentelemetry-talk-design-system/project`.

---

### Task 1: Scaffold the deck directory and vendor the fonts

**Files:**
- Create: `presentation-trace/deck-stage.js` (copy), `presentation-trace/notes.html` (copy), `presentation-trace/start.sh` (copy)
- Create: `presentation-trace/assets/*` (copy from `$BUNDLE/assets`)
- Create: `presentation-trace/fonts/fetch-fonts.sh`, `presentation-trace/fonts/fonts.css`
- Create: `presentation-trace/index.html` (minimal, one slide — proves the harness boots)

**Interfaces:**
- Consumes: nothing.
- Produces: a servable deck at `presentation-trace/index.html`; the CSS custom-property-free font stack `--font-display: "Space Grotesk"`, `--font-body: "Public Sans"`, `--font-mono: "JetBrains Mono"` declared in `fonts/fonts.css`.

- [ ] **Step 1: Copy the presenter machinery and assets**

```bash
cd /Users/kaspernissen/kaspernissen/your-agent-did-what
mkdir -p presentation-trace/assets presentation-trace/fonts
cp presentation/deck-stage.js presentation/notes.html presentation/start.sh presentation-trace/
chmod +x presentation-trace/start.sh
cp "$BUNDLE/assets/capybara-mascot.png" \
   "$BUNDLE/assets/otel-logo.svg" \
   "$BUNDLE/assets/collector-pipeline.svg" \
   "$BUNDLE/assets/data-sources.svg" \
   "$BUNDLE/assets/signal-traces.svg" \
   presentation-trace/assets/
ls -la presentation-trace/assets/
```

Expected: five asset files listed.

- [ ] **Step 2: Write the font-fetch script**

Create `presentation-trace/fonts/fetch-fonts.sh`:

```bash
#!/usr/bin/env bash
# Download the three Trace families as woff2 into this directory.
# Run once; the woff2 files are committed so the deck works offline.
set -euo pipefail
cd "$(dirname "$0")"

UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'
CSS_URL='https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600&family=Public+Sans:wght@300;400;600&family=JetBrains+Mono:wght@400;500&display=swap'

echo "Fetching font CSS…"
curl -sS -A "$UA" "$CSS_URL" -o /tmp/trace-fonts.css

echo "Downloading woff2 files…"
grep -oE 'https://[^)]+\.woff2' /tmp/trace-fonts.css | sort -u | while read -r url; do
  name=$(basename "$url")
  curl -sS -A "$UA" "$url" -o "$name"
  echo "  $name"
done

echo "Done. $(ls -1 ./*.woff2 | wc -l | tr -d ' ') files."
```

- [ ] **Step 3: Run the font fetch and verify files landed**

Run:
```bash
chmod +x presentation-trace/fonts/fetch-fonts.sh && presentation-trace/fonts/fetch-fonts.sh
ls -1 presentation-trace/fonts/*.woff2 | wc -l
```
Expected: a non-zero count (at least 6 — three families across the listed weights). If the count is 0, the Google Fonts endpoint changed shape; fall back to downloading the families from `https://fonts.bunny.net/css2?...` with the same query string, which serves the same faces with a stable API.

- [ ] **Step 4: Write `fonts/fonts.css`**

Create `presentation-trace/fonts/fonts.css`. Replace each `src` filename with the actual filenames produced by Step 3 (`ls presentation-trace/fonts/*.woff2`); the family/weight pairing below is what matters.

```css
/* Vendored — no network at runtime. Regenerate with ./fetch-fonts.sh */
@font-face{font-family:"Space Grotesk";font-style:normal;font-weight:500;font-display:swap;src:url("./SpaceGrotesk-500.woff2") format("woff2")}
@font-face{font-family:"Space Grotesk";font-style:normal;font-weight:600;font-display:swap;src:url("./SpaceGrotesk-600.woff2") format("woff2")}
@font-face{font-family:"Public Sans";font-style:normal;font-weight:300;font-display:swap;src:url("./PublicSans-300.woff2") format("woff2")}
@font-face{font-family:"Public Sans";font-style:normal;font-weight:400;font-display:swap;src:url("./PublicSans-400.woff2") format("woff2")}
@font-face{font-family:"Public Sans";font-style:normal;font-weight:600;font-display:swap;src:url("./PublicSans-600.woff2") format("woff2")}
@font-face{font-family:"JetBrains Mono";font-style:normal;font-weight:400;font-display:swap;src:url("./JetBrainsMono-400.woff2") format("woff2")}
@font-face{font-family:"JetBrains Mono";font-style:normal;font-weight:500;font-display:swap;src:url("./JetBrainsMono-500.woff2") format("woff2")}
```

Rename the downloaded woff2 files to match these `src` names so the mapping is explicit:
```bash
cd presentation-trace/fonts && ls -1 *.woff2
# rename each to the SpaceGrotesk-500.woff2 / PublicSans-300.woff2 / … scheme above
```

- [ ] **Step 5: Write a minimal `index.html` that boots**

Create `presentation-trace/index.html`:

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Your Agent Did What?</title>
<link rel="stylesheet" href="fonts/fonts.css">
<link rel="stylesheet" href="trace.css">
</head>
<body>
<deck-stage width="1920" height="1080">
  <section data-label="Cover" class="ground-ink">
    <h1 class="title">Your Agent Did What?</h1>
  </section>
</deck-stage>

<script type="application/json" id="speaker-notes">
["Cover — hold here while the room settles."]
</script>
<script src="deck-stage.js"></script>
</body>
</html>
```

Create a placeholder `presentation-trace/trace.css` containing only `/* tokens land in Task 2 */` so the stylesheet link resolves.

- [ ] **Step 6: Verify the deck serves and renders one slide**

Run:
```bash
cd presentation-trace && python3 -m http.server 8009 >/dev/null 2>&1 &
sleep 1
curl -s http://localhost:8009/index.html | grep -c "deck-stage"
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8009/deck-stage.js
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8009/assets/capybara-mascot.png
kill %1
```
Expected: a count ≥ 2, then `200`, then `200`.

- [ ] **Step 7: Commit**

```bash
cd /Users/kaspernissen/kaspernissen/your-agent-did-what
git add presentation-trace/
git commit -m "feat(deck): scaffold presentation-trace with vendored fonts and assets"
```

---

### Task 2: Design tokens and layout primitives

**Files:**
- Modify: `presentation-trace/trace.css` (replace the placeholder)
- Modify: `presentation-trace/index.html` (add a kitchen-sink slide exercising every primitive)

**Interfaces:**
- Consumes: `fonts/fonts.css` families from Task 1.
- Produces: the class vocabulary every later slide is written against —
  grounds `.ground-ink` / `.ground-paper` / `.ground-paper-2`;
  type `.kicker` / `.title` / `.subtitle` / `.body` / `.small`;
  geometry `.chamfer` (40px) / `.chamfer-sm` (24px) / `.diagonal-split`;
  trace primitives `.axis`, `.axis-node` (+ `.is-amber` / `.is-hollow` / `.is-halo`), `.span-bar` (+ `.is-amber` / `.is-blue` / `.is-blue-lift` / `.is-blue-mute`, width via `style="--w:57%"`);
  parts `.tag` (+ `.is-solid` / `.is-outline` / `.is-navy`), `.attr-chip` (+ `.is-amber` / `.is-blue` on its dot), `.stat` / `.stat-figure` / `.stat-label`, `.code-block`, `.axis-list` / `.axis-list-item`, `.waterfall` / `.wf-row` / `.wf-label` / `.wf-bar` / `.wf-dur`, `.mascot`;
  and the emphasis marker attribute `data-emphasis="amber"`.

- [ ] **Step 1: Write `trace.css`**

Replace `presentation-trace/trace.css` entirely:

```css
/* ── Trace — design tokens ─────────────────────────────────────────── */
:root{
  --ink:#10142E; --navy:#202C5F; --paper:#FAF7F2; --paper-2:#F2ECE0;
  --amber:#F5A800; --amber-lift:#FFC842; --amber-text:#8A5B00;
  --blue:#425CC7; --blue-lift:#6E85E0; --blue-mute:#A9B6EE;
  --muted-ink:#5B6180; --on-ink:#C9CEE8; --on-ink-dim:#8A93BC;
  --font-display:"Space Grotesk",system-ui,sans-serif;
  --font-body:"Public Sans",system-ui,sans-serif;
  --font-mono:"JetBrains Mono",ui-monospace,monospace;
  --chamfer:40px; --chamfer-sm:24px;
  --pad-x:120px;
}

*{box-sizing:border-box}

deck-stage>section{
  font-family:var(--font-body); background:var(--paper); color:var(--ink);
  padding:110px var(--pad-x); overflow:hidden; position:relative;
}
.ground-ink{background:var(--ink); color:var(--paper)}
.ground-paper{background:var(--paper); color:var(--ink)}
.ground-paper-2{background:var(--paper-2); color:var(--ink)}

/* ── Type ramp (authored at 1920×1080) ─────────────────────────────── */
.kicker{font-family:var(--font-mono);font-size:26px;letter-spacing:.2em;
  text-transform:uppercase;color:var(--blue);margin:0 0 40px}
.ground-ink .kicker{color:var(--blue-mute)}
.title{font-family:var(--font-display);font-weight:500;font-size:96px;
  line-height:1.02;letter-spacing:-.03em;margin:0}
.subtitle{font-family:var(--font-display);font-weight:400;font-size:52px;
  line-height:1.25;letter-spacing:-.015em;margin:0}
.body{font-size:34px;line-height:1.45;font-weight:300;margin:0;text-wrap:pretty}
.small{font-size:28px;line-height:1.4;color:var(--muted-ink);margin:0}
.ground-ink .small{color:var(--on-ink-dim)}
.amber-text{color:var(--amber-text)}
.ground-ink .amber-text{color:var(--amber-lift)}

/* ── Geometry ──────────────────────────────────────────────────────── */
.chamfer{clip-path:polygon(0 0,calc(100% - var(--chamfer)) 0,100% var(--chamfer),100% 100%,0 100%)}
.chamfer-sm{clip-path:polygon(0 0,calc(100% - var(--chamfer-sm)) 0,100% var(--chamfer-sm),100% 100%,0 100%)}
.diagonal-split{position:absolute;inset:0;clip-path:polygon(0 0,58% 0,42% 100%,0 100%)}

/* ── The signal axis ───────────────────────────────────────────────── */
.axis{position:absolute;left:0;right:0;height:2px;
  background:linear-gradient(90deg,transparent,var(--blue) 10%,var(--blue) 60%,var(--amber) 86%,transparent)}
.axis-node{position:absolute;width:26px;height:26px;border-radius:50%;
  background:var(--blue);margin:-13px 0 0 -13px}
.axis-node.is-amber{background:var(--amber)}
.axis-node.is-hollow{background:transparent;border:3px solid var(--blue)}
.axis-node.is-halo{box-shadow:0 0 0 9px rgba(66,92,199,.18)}

/* ── Span bar — the list primitive; replaces bullets ───────────────── */
.span-bar{height:40px;border-radius:20px;background:var(--blue);width:var(--w,100%)}
.span-bar.is-amber{background:var(--amber)}
.span-bar.is-blue-lift{background:var(--blue-lift)}
.span-bar.is-blue-mute{background:var(--blue-mute)}

/* ── Axis list — the other bullet replacement ──────────────────────── */
.axis-list{position:relative;padding-left:52px;display:flex;
  flex-direction:column;gap:44px}
.axis-list::before{content:"";position:absolute;left:13px;top:14px;bottom:14px;
  width:2px;background:linear-gradient(180deg,transparent,var(--blue-mute) 12%,var(--blue-mute) 88%,transparent)}
.axis-list-item{position:relative;font-size:34px;line-height:1.4;font-weight:300}
.axis-list-item::before{content:"";position:absolute;left:-46px;top:12px;
  width:18px;height:18px;border-radius:50%;background:var(--blue)}
.axis-list-item.is-amber::before{background:var(--amber)}

/* ── Parts ─────────────────────────────────────────────────────────── */
.tag{font-family:var(--font-mono);font-size:24px;letter-spacing:.1em;
  text-transform:uppercase;padding:14px 26px;display:inline-block;
  clip-path:polygon(0 0,calc(100% - 16px) 0,100% 16px,100% 100%,0 100%)}
.tag.is-solid{background:var(--amber);color:var(--ink)}
.tag.is-outline{border:1.5px solid var(--blue);color:var(--blue)}
.tag.is-navy{background:var(--navy);color:var(--on-ink)}

.attr-chip{display:inline-flex;align-items:center;gap:10px;
  font-family:var(--font-mono);font-size:26px;padding:12px 22px;
  border-radius:24px;background:var(--paper-2);color:var(--navy)}
.attr-chip::before{content:"";width:10px;height:10px;border-radius:50%;
  background:var(--blue)}
.attr-chip.is-amber::before{background:var(--amber)}

.stat{display:flex;flex-direction:column;gap:18px}
.stat-figure{font-family:var(--font-display);font-weight:500;font-size:132px;
  letter-spacing:-.04em;line-height:1}
.stat-label{font-size:32px;line-height:1.4;font-weight:300;color:#3C4266}
.ground-ink .stat-label{color:var(--on-ink)}

.code-block{background:#080B1E;padding:56px 64px;
  clip-path:polygon(0 0,calc(100% - 44px) 0,100% 44px,100% 100%,0 100%)}
.code-block pre{margin:0;font-family:var(--font-mono);font-size:34px;
  line-height:1.9;color:var(--on-ink)}
.code-block .c-str{color:var(--amber-lift)}
.code-block .c-key{color:#6E7BA8}
.code-block .c-attr{color:#9FADEE}

.waterfall{display:flex;flex-direction:column;gap:26px}
.wf-row{display:flex;align-items:center;gap:32px}
.wf-label{font-family:var(--font-mono);font-size:26px;color:var(--on-ink-dim);
  width:300px;flex:none;text-align:right}
.wf-track{flex:1;height:40px;position:relative}
.wf-bar{position:absolute;top:0;bottom:0;border-radius:20px;
  background:var(--blue);left:var(--x,0);width:var(--w,100%)}
.wf-bar.is-amber{background:var(--amber)}
.wf-bar.is-blue-lift{background:var(--blue-lift)}
.wf-bar.is-blue-mute{background:var(--blue-mute)}
.wf-dur{font-family:var(--font-mono);font-size:26px;color:var(--on-ink-dim);
  width:150px;flex:none}
.wf-row.is-amber .wf-label,.wf-row.is-amber .wf-dur{color:var(--amber-lift)}

.mascot{position:absolute;height:auto}
```

- [ ] **Step 2: Add a kitchen-sink slide exercising every primitive**

Append this `<section>` inside `<deck-stage>` in `presentation-trace/index.html`, after the cover, and add a matching second entry to the speaker-notes array:

```html
  <section data-label="Kitchen sink" class="ground-paper">
    <p class="kicker">every primitive, once</p>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:60px">
      <div class="axis-list">
        <p class="axis-list-item is-amber">Span bars replace bullets.</p>
        <p class="axis-list-item">Nodes mark events on the axis.</p>
      </div>
      <div style="display:flex;flex-direction:column;gap:20px">
        <div class="span-bar" style="--w:100%"></div>
        <div class="span-bar is-blue-lift" style="--w:72%"></div>
        <div class="span-bar is-amber" style="--w:41%" data-emphasis="amber"></div>
      </div>
      <div style="display:flex;gap:16px;align-items:center">
        <span class="tag is-solid">Experimental</span>
        <span class="tag is-outline">Stable</span>
        <span class="tag is-navy">Traces</span>
      </div>
      <div style="display:flex;gap:16px;align-items:center;flex-wrap:wrap">
        <span class="attr-chip is-amber">gen_ai.evaluation.name</span>
        <span class="attr-chip">gen_ai.request.model</span>
      </div>
      <div class="waterfall">
        <div class="wf-row"><span class="wf-label">agent.run</span>
          <div class="wf-track"><div class="wf-bar" style="--x:0;--w:100%"></div></div>
          <span class="wf-dur">4.2 s</span></div>
        <div class="wf-row is-amber"><span class="wf-label">chat</span>
          <div class="wf-track"><div class="wf-bar is-amber" style="--x:19%;--w:71%"></div></div>
          <span class="wf-dur">3.0 s</span></div>
      </div>
      <div class="code-block"><pre><span class="c-key">span</span>.set_attribute(<span class="c-attr">"gen_ai.tool.name"</span>, <span class="c-str">"delete_records"</span>)</pre></div>
    </div>
    <div class="axis" style="top:940px"></div>
    <div class="axis-node is-amber" style="left:200px;top:940px"></div>
  </section>
```

- [ ] **Step 3: Verify it serves and every class resolves**

Run:
```bash
cd presentation-trace && python3 -m http.server 8009 >/dev/null 2>&1 &
sleep 1
for c in ground-ink axis-node span-bar axis-list attr-chip code-block waterfall chamfer mascot; do
  printf "%s: " "$c"; curl -s http://localhost:8009/trace.css | grep -c "\.$c"
done
kill %1
```
Expected: every line reports a count ≥ 1.

- [ ] **Step 4: Commit**

```bash
cd /Users/kaspernissen/kaspernissen/your-agent-did-what
git add presentation-trace/trace.css presentation-trace/index.html
git commit -m "feat(deck): Trace design tokens and layout primitives"
```

---

### Task 3: Conformance checker

Enforces the Global Constraints mechanically. Written test-first: the checker's own rules are exercised against fixtures before it is pointed at the real deck.

**Files:**
- Create: `presentation-trace/check-deck.py`
- Create: `presentation-trace/test-check-deck.py`

**Interfaces:**
- Consumes: the class vocabulary and `data-emphasis` marker from Task 2.
- Produces: `check_deck(html: str, css: str) -> list[str]` returning a list of human-readable violation strings, empty when clean. CLI: `python3 check-deck.py` exits `0` when clean, `1` otherwise.

- [ ] **Step 1: Write the failing test**

Create `presentation-trace/test-check-deck.py`:

```python
import unittest
from importlib.machinery import SourceFileLoader

check = SourceFileLoader("check_deck", "check-deck.py").load_module()

CLEAN_HTML = """
<deck-stage width="1920" height="1080">
  <section data-label="One" class="ground-ink"><h1 class="title">A</h1>
    <div class="span-bar is-amber" data-emphasis="amber"></div></section>
</deck-stage>
<script type="application/json" id="speaker-notes">["note one"]</script>
"""
CLEAN_CSS = ":root{--ink:#10142E}"


class TestCheckDeck(unittest.TestCase):
    def test_clean_deck_has_no_violations(self):
        self.assertEqual(check.check_deck(CLEAN_HTML, CLEAN_CSS), [])

    def test_flags_missing_data_label(self):
        html = CLEAN_HTML.replace(' data-label="One"', "")
        self.assertTrue(any("data-label" in v for v in check.check_deck(html, CLEAN_CSS)))

    def test_flags_note_count_mismatch(self):
        html = CLEAN_HTML.replace('["note one"]', '["a","b"]')
        self.assertTrue(any("notes" in v.lower() for v in check.check_deck(html, CLEAN_CSS)))

    def test_flags_bullets(self):
        html = CLEAN_HTML.replace("<h1 class=\"title\">A</h1>", "<ul><li>x</li></ul>")
        self.assertTrue(any("bullet" in v.lower() for v in check.check_deck(html, CLEAN_CSS)))

    def test_flags_raw_hex_in_slide_markup(self):
        html = CLEAN_HTML.replace('class="title"', 'class="title" style="color:#FF0000"')
        self.assertTrue(any("hex" in v.lower() for v in check.check_deck(html, CLEAN_CSS)))

    def test_flags_two_amber_emphases_on_one_slide(self):
        html = CLEAN_HTML.replace(
            '<div class="span-bar is-amber" data-emphasis="amber"></div>',
            '<div data-emphasis="amber"></div><div data-emphasis="amber"></div>')
        self.assertTrue(any("emphasis" in v.lower() for v in check.check_deck(html, CLEAN_CSS)))

    def test_flags_pure_white_or_black_in_css(self):
        self.assertTrue(any("pure" in v.lower()
                            for v in check.check_deck(CLEAN_HTML, ":root{--x:#ffffff}")))

    def test_flags_two_mascots_on_one_slide(self):
        html = CLEAN_HTML.replace("<h1 class=\"title\">A</h1>",
                                  '<img class="mascot"><img class="mascot">')
        self.assertTrue(any("mascot" in v.lower() for v in check.check_deck(html, CLEAN_CSS)))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd presentation-trace && python3 test-check-deck.py -v`
Expected: FAIL — `FileNotFoundError` / `ModuleNotFoundError` for `check-deck.py`.

- [ ] **Step 3: Write the checker**

Create `presentation-trace/check-deck.py`:

```python
#!/usr/bin/env python3
"""Conformance checker for the Trace deck.

Enforces the design-system rules that are mechanically checkable, so drift is
caught by a command rather than by eye. Run with no arguments from
presentation-trace/; exits non-zero if the deck violates a rule.
"""
import json
import re
import sys

# Colors the slide markup may never hard-code — everything comes from trace.css.
HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
PURE_RE = re.compile(r"#(?:fff(?:fff)?|000(?:000)?)\b", re.I)
SECTION_RE = re.compile(r"<section\b([^>]*)>(.*?)</section>", re.S | re.I)


def _sections(html):
    """Yield (attrs, inner_html) for each slide."""
    start = html.lower().find("<deck-stage")
    end = html.lower().find("</deck-stage>")
    scope = html[start:end] if start != -1 and end != -1 else html
    return SECTION_RE.findall(scope)


def _notes(html):
    m = re.search(
        r'<script[^>]*id="speaker-notes"[^>]*>(.*?)</script>', html, re.S | re.I)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def check_deck(html, css):
    violations = []
    sections = _sections(html)

    if not sections:
        violations.append("no <section> slides found inside <deck-stage>")

    for i, (attrs, inner) in enumerate(sections, start=1):
        where = f"slide {i}"
        if "data-label" not in attrs:
            violations.append(f"{where}: missing data-label")

        if re.search(r"<(ul|ol|li)\b", inner, re.I):
            violations.append(
                f"{where}: uses bullets — span bars and .axis-list replace them")

        for hexval in HEX_RE.findall(attrs + inner):
            violations.append(
                f"{where}: raw hex {hexval} in slide markup — use trace.css tokens")

        n_emph = len(re.findall(r'data-emphasis="amber"', attrs + inner))
        if n_emph > 1:
            violations.append(
                f"{where}: {n_emph} amber emphases — the system allows one per slide")

        n_mascot = len(re.findall(r'class="[^"]*\bmascot\b', inner))
        if n_mascot > 1:
            violations.append(f"{where}: {n_mascot} mascots — never more than one")

    notes = _notes(html)
    if notes is None:
        violations.append("missing or unparseable <script id='speaker-notes'>")
    elif len(notes) != len(sections):
        violations.append(
            f"speaker notes count {len(notes)} != slide count {len(sections)}")

    for pure in PURE_RE.findall(css):
        violations.append(f"trace.css uses pure {pure} — no pure white or black")

    return violations


def main():
    with open("index.html", encoding="utf-8") as f:
        html = f.read()
    with open("trace.css", encoding="utf-8") as f:
        css = f.read()
    violations = check_deck(html, css)
    for v in violations:
        print(f"✗ {v}")
    if violations:
        print(f"\n{len(violations)} violation(s).")
        return 1
    print("✓ deck conforms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd presentation-trace && python3 test-check-deck.py -v`
Expected: PASS — 8 tests OK.

- [ ] **Step 5: Run the checker against the real deck and fix what it finds**

Run: `cd presentation-trace && python3 check-deck.py`
Expected: `✓ deck conforms`.

The Task 2 kitchen-sink slide uses inline `style="--w:41%"` and `style="top:940px"`, which are geometry rather than color and so pass. If the checker reports raw-hex violations from the kitchen sink, move those colors into `trace.css` classes rather than weakening the rule.

- [ ] **Step 6: Commit**

```bash
cd /Users/kaspernissen/kaspernissen/your-agent-did-what
git add presentation-trace/check-deck.py presentation-trace/test-check-deck.py
git commit -m "test(deck): conformance checker for the Trace design rules"
```

---

### Task 4: Restructure `outline.md` to the nine-beat arc

The content plan's source. Until this exists, slide-level tasks cannot be written honestly.

**Files:**
- Modify: `outline.md` (full rewrite)
- Read for material: `abstract.md`, `landscape.md`, `research.md`, `demos/ANALYSIS.md`, `docs/superpowers/specs/2026-08-07-talk-scope-deck-and-two-demos-design.md`

**Interfaces:**
- Consumes: the nine beats and their source-material mapping from spec §2; the layout vocabulary from spec §10.2.
- Produces: for every beat — a duration, a slide list where each slide names its layout (L01–L08), its one-line message, and its amber emphasis. This is what the content plan turns into `<section>` elements.

- [ ] **Step 1: Read the existing outline and source material**

Run:
```bash
cd /Users/kaspernissen/kaspernissen/your-agent-did-what
wc -l outline.md abstract.md landscape.md research.md demos/ANALYSIS.md
```
Then read `outline.md` in full, plus the "Reusable-assets map" section at its end — it records which existing slides can be salvaged.

- [ ] **Step 2: Write the new outline**

Rewrite `outline.md` with this structure, preserving the existing file's "Arc at a glance (timing)" table format. Total 30 minutes. Beats and their sources are fixed by spec §2:

| Beat | Minutes | Source |
|---|---|---|
| 0 Cold open — "your agent did what?" | 1.5 | existing slides |
| 1 Agents aren't request/response | 4 | `research.md` |
| 2 The competing semantics that exist | 4 | `landscape.md` |
| 3 Why OpenTelemetry should be the standard | 3 | new writing |
| 4 The conventions: what you get, what setup costs | 5 | `demos/ANALYSIS.md`, Demo 1 |
| 5 Your tool doesn't speak OTel? Normalize at the edge | 4 | Demo 2, `demos/arconia` |
| 6 Reasoning — what did the agent actually do? | 4 | Demo 1 |
| 7 Evaluation quality via the OTel evaluation semantics | 3.5 | Demo 1 judge |
| 8 Where this is going + close | 1 | `landscape.md` |

For each beat write: the beat's single message in one sentence, then a numbered slide list. Each slide entry must name its layout (`L01`–`L08`), its headline, and its **one** amber emphasis. Two content requirements from spec §2.1 must appear in beat 4:

- the GenAI conventions moved to `open-telemetry/semantic-conventions-genai` in semconv v1.42.0 (June 2026);
- nothing GenAI is marked Stable as of July 2026.

Respect the system's own budget rules while allocating layouts: L03 Statement is "use sparingly — twice a talk", and the mascot appears on cover, close, and at most one mid-deck breath.

- [ ] **Step 3: Verify the outline is complete and budgeted**

Run:
```bash
cd /Users/kaspernissen/kaspernissen/your-agent-did-what
grep -c "^### " outline.md          # slide entries
grep -oE "L0[1-8]" outline.md | sort | uniq -c
grep -ci "statement" outline.md
```
Expected: the layout histogram shows at most two `L03`, exactly one `L01` and one `L08`, and the beat durations in the timing table sum to 30.

- [ ] **Step 4: Commit**

```bash
cd /Users/kaspernissen/kaspernissen/your-agent-did-what
git add outline.md
git commit -m "docs(talk): restructure outline to the nine-beat arc"
```

---

### Task 5: Deck README and the run path

**Files:**
- Create: `presentation-trace/README.md`
- Modify: `README.md` (root — add the new deck to the "Run the slide deck" section)

**Interfaces:**
- Consumes: everything above.
- Produces: the documented run command `cd presentation-trace && ./start.sh`.

- [ ] **Step 1: Write `presentation-trace/README.md`**

Cover: what the deck is; `./start.sh` (deck + notes follower, `←`/`→`, `R` resets, number keys jump); that fonts are vendored and the deck is offline-safe; `python3 check-deck.py` before committing slide changes; and a short restatement of the non-negotiable rules — one amber emphasis per slide, no bullets, one chamfered corner, mascot on cover/close/one breath only, no pure white or black.

- [ ] **Step 2: Point the root README at both decks**

Modify the root `README.md` "Run the slide deck" section to list `presentation/` as the current deck and `presentation-trace/` as the Trace rebuild, noting the old one is retained until the new one supersedes it.

- [ ] **Step 3: Verify the documented path actually works**

Run:
```bash
cd /Users/kaspernissen/kaspernissen/your-agent-did-what/presentation-trace
bash -n start.sh && python3 check-deck.py
```
Expected: no syntax errors, then `✓ deck conforms`.

- [ ] **Step 4: Commit**

```bash
cd /Users/kaspernissen/kaspernissen/your-agent-did-what
git add presentation-trace/README.md README.md
git commit -m "docs(deck): document presentation-trace and its conformance check"
```

---

## What this plan deliberately does not cover

The slide content itself. Task 4 produces the slide list; the **content plan**
(`docs/superpowers/plans/2026-08-07-deck-content.md`, written after Task 4 lands) turns
each outline entry into a `<section>` plus its speaker note, beat by beat. Writing those
tasks now would mean inventing a slide list and then building against it.

Also out of scope here, tracked in spec §11: the two demos, `demos/ANALYSIS.md` updates,
and re-pointing `resources.md` at `semantic-conventions-genai`.

---

## Self-Review

**Spec coverage.** §10.1 tokens → Task 2. §10.1 type ramp → Task 2. §10.1 geometry and
mascot rules → Tasks 2 and 3. §10.2 layouts → Task 4 assigns them per slide; primitives
exist in Task 2. §10.3 new directory → Task 1; framework reuse → Task 1; title → Task 1
and Global Constraints; vendored fonts → Task 1. §11 deliverable 1 (outline + deck) →
Tasks 4 and the content plan.

**Gap found and accepted:** §10.3's "fix the close slide's dead link" lands on the close
slide, which belongs to the content plan, not this one. It is restated in the content
plan's scope note above so it cannot be lost.

**Type consistency.** `check_deck(html, css) -> list[str]` is defined in Task 3's
Interfaces and used with that exact signature in the tests and in `main()`. The class
vocabulary in Task 2's Interfaces matches the selectors written in `trace.css` and the
markup in the kitchen-sink slide: `.span-bar` takes width via `--w`, `.wf-bar` takes
`--x` and `--w`, and `data-emphasis="amber"` is the single marker the checker counts.
