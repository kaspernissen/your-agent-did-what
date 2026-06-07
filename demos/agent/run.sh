#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Load root demos .env if present
if [ -f ../.env ]; then set -a; . ../.env; set +a; fi
: "${ANTHROPIC_API_KEY:?Set ANTHROPIC_API_KEY (copy demos/.env.template to demos/.env)}"

export OTEL_EXPORTER_OTLP_ENDPOINT="${OTEL_EXPORTER_OTLP_ENDPOINT:-http://localhost:4318}"

if [ ! -d .venv ]; then
  python3 -m venv .venv
  ./.venv/bin/pip install -q -r requirements.txt
fi

exec ./.venv/bin/python app.py "$@"
