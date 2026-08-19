# Type & colour spec — Trace deck

Everything here is measured off the rendered deck (899 text runs across 72 slides),
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

Top 30 of 191 distinct (family, size, weight, colour) combinations:

| Family | px | pt | Weight | Colour | Count |
|---|---|---|---|---|---|
| JetBrains Mono | 20 | 10 | 400 | `#10142E` | 66 |
| Public Sans | 28 | 14 | 400 | `#5B6180` | 45 |
| JetBrains Mono | 26 | 13 | 400 | `#425CC7` | 40 |
| JetBrains Mono | 17 | 8.5 | 400 | `#5B6180` | 29 |
| Public Sans | 21 | 10.5 | 300 | `#5B6180` | 20 |
| JetBrains Mono | 26 | 13 | 400 | `#A9B6EE` | 17 |
| Public Sans | 26 | 13 | 300 | `#10142E` | 17 |
| Space Grotesk | 72 | 36 | 500 | `#10142E` | 15 |
| Public Sans | 34 | 17 | 300 | `#10142E` | 14 |
| JetBrains Mono | 19 | 9.5 | 400 | `#425CC7` | 14 |
| JetBrains Mono | 26 | 13 | 400 | `#8A93BC` | 14 |
| Public Sans | 24 | 12 | 300 | `#5B6180` | 13 |
| JetBrains Mono | 19 | 9.5 | 400 | `#5B6180` | 13 |
| Public Sans | 36 | 18 | 300 | `#8A93BC` | 12 |
| Public Sans | 28 | 14 | 400 | `#8A93BC` | 12 |
| JetBrains Mono | 18 | 9 | 400 | `#5B6180` | 12 |
| JetBrains Mono | 24 | 12 | 400 | `#C9CEE8` | 12 |
| JetBrains Mono | 21 | 10.5 | 400 | `#C9CEE8` | 11 |
| JetBrains Mono | 21 | 10.5 | 400 | `#10142E` | 10 |
| JetBrains Mono | 22 | 11 | 400 | `#10142E` | 10 |
| JetBrains Mono | 20 | 10 | 400 | `#8A5B00` | 9 |
| Public Sans | 24 | 12 | 400 | `#10142E` | 9 |
| JetBrains Mono | 20 | 10 | 400 | `#5B6180` | 8 |
| JetBrains Mono | 24 | 12 | 400 | `#10142E` | 8 |
| Public Sans | 26 | 13 | 300 | `#8A93BC` | 7 |
| Space Grotesk | 86 | 43 | 500 | `#10142E` | 7 |
| Public Sans | 34 | 17 | 400 | `#425CC7` | 7 |
| JetBrains Mono | 26 | 13 | 400 | `#202C5F` | 7 |
| JetBrains Mono | 21 | 10.5 | 400 | `#8A93BC` | 7 |
| JetBrains Mono | 34 | 17 | 400 | `#9FADEE` | 7 |
