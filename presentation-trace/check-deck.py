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
# Scanned ONLY inside style="..." attributes — that is where colour actually gets
# applied. Slide prose legitimately contains GitHub issue refs (#46069, #185,
# #8416), which are not colours and must not trip this rule.
HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
STYLE_ATTR_RE = re.compile(r'style\s*=\s*"([^"]*)"', re.I)
PURE_RE = re.compile(r"#(?:fff(?:fff)?|000(?:000)?)\b", re.I)
SECTION_RE = re.compile(r"<section\b([^>]*)>(.*?)</section>", re.S | re.I)
SVG_TAG_RE = re.compile(r"<(/?)svg\b[^>]*?(/?)>", re.S | re.I)


def _strip_svg(markup):
    """Drop every <svg>…</svg> subtree.

    The no-raw-hex rule exists to stop colour drift in slide *chrome*. An inline
    SVG diagram is artwork — it carries its own palette (often lifted verbatim
    from a source deck) and is exempt. Everything outside an <svg> stays strictly
    governed. Handles several SVGs per slide and nested <svg> elements; an
    unclosed <svg> is deliberately left in so its hex still gets flagged.
    """
    kept = []
    depth = 0
    cursor = 0
    for m in SVG_TAG_RE.finditer(markup):
        closing = m.group(1) == "/"
        self_closing = m.group(2) == "/"
        if closing:
            if depth:
                depth -= 1
                if depth == 0:
                    cursor = m.end()
        elif self_closing:
            if depth == 0:
                kept.append(markup[cursor:m.start()])
                cursor = m.end()
        else:
            if depth == 0:
                kept.append(markup[cursor:m.start()])
                cursor = m.start()
            depth += 1
    kept.append(markup[cursor:])
    return "".join(kept)


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

        styles = " ".join(STYLE_ATTR_RE.findall(attrs + _strip_svg(inner)))
        for hexval in HEX_RE.findall(styles):
            violations.append(
                f"{where}: raw hex {hexval} in a style attribute — use trace.css tokens "
                f"(inline <svg> artwork is exempt)")

        n_emph = len(re.findall(r'data-emphasis="amber"', attrs + inner))
        if n_emph > 1:
            violations.append(
                f"{where}: {n_emph} amber emphasis markers — the system allows one per slide")

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
