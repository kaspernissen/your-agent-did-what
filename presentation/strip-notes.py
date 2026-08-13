#!/usr/bin/env python3
"""Remove the speaker notes from a copy of the deck, for publishing.

The notes live inside index.html: notes.html fetches the deck and reads
<script type="application/json" id="speaker-notes"> out of it. So publishing the deck
publishes the notes, and every "do not say this", "if asked" and withdrawn-claim caveat
goes with it. A password on a separate page would be theatre, because the payload ships in
the public file either way.

deck-stage.js already tolerates a missing tag, so the deck works without it.

    ./strip-notes.py path/to/index.html
"""
import re
import sys

PATTERN = re.compile(
    r'\n?<script type="application/json" id="speaker-notes">.*?</script>', re.S)


def main(path: str) -> int:
    src = open(path, encoding="utf-8").read()

    stripped, count = PATTERN.subn("", src)
    if count != 1:
        print(f"strip-notes: expected exactly one notes block, found {count}", file=sys.stderr)
        return 1

    # Fail loudly rather than publish a deck that still carries them.
    for probe in ("speaker-notes", "application/json"):
        if probe in stripped:
            print(f"strip-notes: {probe!r} still present after stripping", file=sys.stderr)
            return 1
    if not stripped.rstrip().endswith("</html>"):
        print("strip-notes: document tail damaged", file=sys.stderr)
        return 1

    open(path, "w", encoding="utf-8").write(stripped)
    removed = len(src) - len(stripped)
    print(f"strip-notes: removed {removed} bytes of speaker notes from {path}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
