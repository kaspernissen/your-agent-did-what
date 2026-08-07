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
