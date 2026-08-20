#!/usr/bin/env bash
# One local run of otter-sre, outside the cluster.
#
#   ./run.sh "List all the records in the database."
#
# There is no instrumentation switch: this directory *is* the OpenLLMetry agent. For the other
# vocabulary run ../beaver-sre/run.sh — same loop, same tools, one library different.
set -euo pipefail
cd "$(dirname "$0")"

if [ -f ../../.env ]; then set -a; . ../../.env; set +a; fi   # demos/.env
: "${ANTHROPIC_API_KEY:?Set ANTHROPIC_API_KEY (see demos/.env.template)}"
export OTEL_EXPORTER_OTLP_ENDPOINT="${OTEL_EXPORTER_OTLP_ENDPOINT:-http://localhost:4318}"
export CAPYBARA_AGENT_NAME="${CAPYBARA_AGENT_NAME:-otter-sre}"

# Create the venv on first use, and reinstall whenever requirements.txt changes — checking
# only for .venv's existence silently leaves a stale environment behind, which shows up as a
# ModuleNotFoundError for whichever library was added last.
STAMP=.venv/.requirements.sha
WANT=$(shasum requirements.txt | cut -d" " -f1)
if [ ! -d .venv ]; then
  python3 -m venv .venv
  ./.venv/bin/pip install -q --upgrade pip
fi
if [ ! -f "$STAMP" ] || [ "$(cat "$STAMP")" != "$WANT" ]; then
  echo "installing dependencies…" >&2
  ./.venv/bin/pip install -q -r requirements.txt
  echo "$WANT" > "$STAMP"
fi

exec ./.venv/bin/python app.py "$@"
