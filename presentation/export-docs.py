#!/usr/bin/env python3
"""Write the human-facing side of the export: type spec, copy deck, and a README."""
import json, re, unicodedata
from pathlib import Path
from collections import Counter

HERE = Path(__file__).resolve().parent
OUT = HERE / 'export'
model = json.loads(Path('/tmp/model.json').read_text())
spoken = next(m['n'] for m in model if m['label'] == 'Divider — Appendix') - 1

def slug(s, n=40):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return (re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', s.lower())).strip('-') or 'slide')[:n]

hexcol = lambda c: '#%02X%02X%02X' % tuple(int(v) for v in re.findall(r'\d+', c)[:3])

# ── type census, measured off the real render rather than read off the stylesheet
runs = [t for m in model for t in m['text']]
census = Counter((t['font'], t['size'], t['weight'], hexcol(t['color'])) for t in runs)

FONTS = f"""# Type & colour spec — Trace deck

Everything here is measured off the rendered deck ({len(runs)} text runs across {len(model)} slides),
not read off the stylesheet, so it is what the slides actually show.

## Page setup — do this first

The deck is authored at **1920 × 1080 px**. In Google Slides go to
**File → Page setup → Custom** and enter **13.333 × 7.5 inches**.

That makes the conversion exactly **1 px = 0.5 pt**, so every size below halves.
If you leave Slides on its default 10 × 5.63in widescreen, the factor is 0.375
instead and every number needs multiplying by 0.375 — which is why it is worth
changing the page setup before you place anything.

## Fonts

All three are Google Fonts, so they are in the Slides font picker already. Add
them once via **Font → More fonts**.

| Family | Weights used | Used for |
|---|---|---|
| **Space Grotesk** | 500, 600 | Titles, divider numbers, card headings |
| **Public Sans** | 300, 400, 600 | Body copy, captions, statements |
| **JetBrains Mono** | 400 | Kickers, labels, attribute names, code |

## Type roles

| Role | Family | px | **pt** | Weight | Tracking |
|---|---|---|---|---|---|
| Divider number | Space Grotesk | 220 | **110** | 600 | −0.05em |
| Divider heading | Space Grotesk | 86 | **43** | 500 | −0.03em |
| Title, statement slide | Space Grotesk | 96 | **48** | 500 | −0.03em |
| Title, standard | Space Grotesk | 56–72 | **28–36** | 500 | −0.03em |
| Subtitle | Space Grotesk | 52 | **26** | 400 | −0.015em |
| Kicker | JetBrains Mono | 26 | **13** | 400 | +0.2em, UPPERCASE |
| Body | Public Sans | 34 | **17** | 300 | — |
| Body, small | Public Sans | 26–28 | **13–14** | 300 | — |
| Card statement | Public Sans | 27 | **13.5** | 400 or 600 | — |
| Card caption | Public Sans | 21–24 | **10.5–12** | 300 | — |
| Label, in-card | JetBrains Mono | 16–19 | **8–9.5** | 400 | +0.14em, UPPERCASE |
| Mono data | JetBrains Mono | 20–26 | **10–13** | 400 | — |
| Code | JetBrains Mono | 34 | **17** | 400 | line spacing 1.9 |

Line spacing: titles 1.02, body 1.45, captions 1.35–1.4, code 1.9.

## Colours

| Token | Hex | Where |
|---|---|---|
| ink | `#10142E` | Body text on light, and the dark slide ground |
| navy | `#202C5F` | Filled panels on light slides |
| paper | `#FAF7F2` | Light slide ground, text on dark |
| paper-2 | `#F2ECE0` | Card fill on light slides |
| amber | `#F5A800` | Divider panels, diagram accents |
| amber-lift | `#FFC842` | Amber emphasis **on dark** slides, code strings |
| amber-text | `#8A5B00` | Amber emphasis **on light** slides |
| blue | `#425CC7` | Kickers, links, diagram lines |
| blue-lift | `#6E85E0` | Secondary diagram lines |
| blue-mute | `#A9B6EE` | Kickers on dark, faint rules |
| muted-ink | `#5B6180` | Secondary text on light |
| on-ink | `#C9CEE8` | Body text on dark |
| on-ink-dim | `#8A93BC` | Secondary text on dark |
| code bg | `#080B1E` | Code panels |
| code bg, muted | `#0E1226` | Second code panel on the same slide |

Amber emphasis flips by ground: `#8A5B00` on paper, `#FFC842` on ink. One amber
phrase per slide — that rule is what keeps it meaning anything.

## Geometry

| Thing | px | **pt** |
|---|---|---|
| Slide | 1920 × 1080 | **960 × 540** |
| Side margin | 120 | **60** |
| Kicker baseline, top | 120 | **60** |
| Title, top | 186 | **93** |
| Card corner radius | 22 | **11** |
| Small corner radius | 14 | **7** |
| Footer rail | y = 1000 | **y = 500** |

Backgrounds: light slides `#FAF7F2`, dark slides `#10142E`. Set the slide
background to match before placing any element PNG — the crops are opaque, and
they are cut from those two grounds.

## Every combination actually used

Top 30 of {len(census)} distinct (family, size, weight, colour) combinations:

| Family | px | pt | Weight | Colour | Count |
|---|---|---|---|---|---|
"""
for (f, s, w, c), n in census.most_common(30):
    FONTS += f'| {f} | {s} | {s/2:g} | {w} | `{c}` | {n} |\n'
(OUT / 'FONTS.md').write_text(FONTS)

# ── copy deck: every text run, in reading order, ready to paste
lines = ['# Slide copy\n',
         'Every text run in reading order, so it can be pasted rather than retyped.',
         'Sizes are px — halve them for points at the 13.333 × 7.5in page setup.\n']
for m in model:
    part = 'SPOKEN' if m['n'] <= spoken else 'APPENDIX'
    lines.append(f"\n---\n\n## {m['n']:02d} · {m['label']}  ({part}, {m['ground']})\n")
    lines.append(f"`export/slides/{m['n']:02d}-{slug(m['label'])}.png`\n")
    for t in m['text']:
        lines.append(f"- **{t['t']}**  \n  <sub>{t['font']} {t['size']}px / {t['size']/2:g}pt · "
                     f"w{t['weight']} · {hexcol(t['color'])} · at {t['x']},{t['y']}</sub>")
    if m['note']:
        lines.append(f"\n<details><summary>Speaker notes</summary>\n\n{m['note']}\n\n</details>")
(OUT / 'COPY.md').write_text('\n'.join(lines))
print('FONTS.md and COPY.md written')
