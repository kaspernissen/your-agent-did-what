#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ -f ../../.env ]; then set -a; . ../../.env; set +a; fi
: "${ANTHROPIC_API_KEY:?Set ANTHROPIC_API_KEY}"
export OTEL_EXPORTER_OTLP_ENDPOINT="${OTEL_EXPORTER_OTLP_ENDPOINT:-http://localhost:4318}"
[ -d .venv ] || { python3 -m venv .venv; ./.venv/bin/pip install -q -r requirements.txt; }
exec ./.venv/bin/python app.py "$@"
