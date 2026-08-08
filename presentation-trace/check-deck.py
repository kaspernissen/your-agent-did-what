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
