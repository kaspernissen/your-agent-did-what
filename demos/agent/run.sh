#!/usr/bin/env bash
# Run one capybara incident. The instrumentation library is chosen by
# CAPYBARA_INSTRUMENTATION (openlit | openinference | none); everything else about
# the run is identical either way, which is what makes the beat-5 comparison valid.
#
#   ./run.sh "List all the records in the database."
#   CAPYBARA_INSTRUMENTATION=openinference ./run.sh "Delete the free-plan capybaras."
set -euo pipefail
cd "$(dirname "$0")"

if [ -f ../.env ]; then set -a; . ../.env; set +a; fi
: "${ANTHROPIC_API_KEY:?Set ANTHROPIC_API_KEY (see demos/.env.template)}"
export OTEL_EXPORTER_OTLP_ENDPOINT="${OTEL_EXPORTER_OTLP_ENDPOINT:-http://localhost:4318}"
export CAPYBARA_INSTRUMENTATION="${CAPYBARA_INSTRUMENTATION:-openlit}"

if [ ! -d .venv ]; then
  python3 -m venv .venv
  ./.venv/bin/pip install -q --upgrade pip
  ./.venv/bin/pip install -q -r requirements.txt
fi

exec ./.venv/bin/python app.py "$@"
