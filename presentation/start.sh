#!/usr/bin/env bash
# Serve the deck and open BOTH the slides and the speaker-notes follower.
#   ./start.sh            # serve on :8000, open deck + notes
#   ./start.sh 9000       # custom port
#
# Drag the notes tab onto your laptop screen; put the deck on the projector.
# Keys (in the deck): ← →  navigate · R reset · number keys jump.
# Notes window: live current/next note + clock + elapsed timer (F = fullscreen).
set -euo pipefail
cd "$(dirname "$0")"

PORT="${1:-8000}"
DECK="index.html"
DECK_URL="http://localhost:${PORT}/${DECK}"
NOTES_URL="http://localhost:${PORT}/notes.html?deck=${DECK}"

SRV=""
if lsof -nP -i ":${PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Reusing existing server on :${PORT}"
else
  python3 -m http.server "${PORT}" >/dev/null 2>&1 &
  SRV=$!
  trap '[ -n "$SRV" ] && kill "$SRV" 2>/dev/null; echo; echo "Server stopped."' INT TERM EXIT
  for _ in $(seq 1 20); do curl -s -o /dev/null "http://localhost:${PORT}/" && break; sleep 0.1; done
fi

cat <<EOF

  Deck:   ${DECK_URL}
  Notes:  ${NOTES_URL}   ← speaker notes follower (drag to your screen)

  Ctrl-C to stop.
EOF

if command -v open >/dev/null 2>&1; then
  open "${DECK_URL}"; sleep 0.5; open "${NOTES_URL}"
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "${DECK_URL}"; sleep 0.5; xdg-open "${NOTES_URL}"
fi

if [ -n "$SRV" ]; then wait "$SRV"; else echo "(server was already running)"; fi
