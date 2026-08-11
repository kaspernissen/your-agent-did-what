#!/usr/bin/env bash
# Re-fetch the three Trace families as woff2 into this directory.
#
# The woff2 files are committed so the deck works offline; you only need this if
# they ever have to be regenerated. The output filenames are the ones fonts.css
# already references — this script reads fonts.css to learn what it must produce,
# so the two can never drift. It writes nothing unless all of them resolve, and
# exits non-zero (loudly) if any does not.
#
# Note: Google serves variable fonts, so several weights of one family can map to
# the same file. That is expected — the resulting duplicates are intentional.
set -euo pipefail
cd "$(dirname "$0")"

UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'
CSS_URL='https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600&family=Public+Sans:wght@300;400;600&family=JetBrains+Mono:wght@400;500&display=swap'

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

echo "Fetching font CSS…"
curl -sSf -A "$UA" "$CSS_URL" -o "$WORK/google.css"

echo "Resolving @font-face blocks → expected filenames…"
python3 - "$WORK/google.css" fonts.css > "$WORK/plan.tsv" <<'PY'
import re, sys

google_css, local_css = (open(p, encoding="utf-8").read() for p in sys.argv[1:3])

FACE_RE = re.compile(r"@font-face\s*\{(.*?)\}", re.S)


def field(block, name):
    # The last declaration in a minified block has no trailing ';', so stop at
    # ';' *or* the end of the block.
    m = re.search(rf"\b{name}\s*:\s*([^;]+)", block)
    return m.group(1).strip().strip("'\"") if m else None


# What fonts.css says must exist: (family, weight) -> output filename.
wanted = {}
for block in FACE_RE.findall(local_css):
    fam, weight = field(block, "font-family"), field(block, "font-weight")
    src = field(block, "src") or ""
    m = re.search(r'url\(\s*["\']?\./([^"\')]+\.woff2)', src)
    if fam and weight and m:
        wanted[(fam, weight)] = m.group(1)
if not wanted:
    sys.exit("fonts.css declared no ./*.woff2 @font-face sources — nothing to fetch")

# What Google serves: pick the `latin` subset, identified by its unicode-range
# (the Basic-Latin block), not by the CSS comment above it.
served = {}
for block in FACE_RE.findall(google_css):
    fam, weight = field(block, "font-family"), field(block, "font-weight")
    urange = field(block, "unicode-range") or ""
    m = re.search(r"url\(\s*[\"']?(https://[^\"')]+\.woff2)", field(block, "src") or "")
    if fam and weight and m and urange.startswith("U+0000-00FF"):
        served[(fam, weight)] = m.group(1)

missing = [f"{f} {w}" for (f, w) in wanted if (f, w) not in served]
if missing:
    sys.exit("no latin subset served for: " + ", ".join(sorted(missing))
             + "\nGoogle's CSS shape may have changed — fix this script, do not "
               "hand-patch the fonts directory.")

for (fam, weight), name in sorted(wanted.items()):
    print(f"{name}\t{served[(fam, weight)]}")
PY

n_expected=$(grep -c . "$WORK/plan.tsv")
echo "Downloading $n_expected woff2 files…"
while IFS=$'\t' read -r name url; do
  [ -n "$name" ] || continue
  curl -sSf -A "$UA" "$url" -o "$WORK/$name"
  # woff2 files start with the magic number wOF2 — a redirect or error page does not.
  if [ "$(head -c 4 "$WORK/$name")" != "wOF2" ]; then
    echo "✗ $name is not a woff2 file — aborting, nothing written." >&2
    exit 1
  fi
  echo "  $name"
done < "$WORK/plan.tsv"

# Only now touch the real directory.
while IFS=$'\t' read -r name _; do
  [ -n "$name" ] || continue
  mv "$WORK/$name" "./$name"
done < "$WORK/plan.tsv"

echo "Done. $n_expected files, all named as fonts.css expects."
