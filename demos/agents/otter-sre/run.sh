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

# The collector is NOT one of 01_start-demo.sh's port-forwards, so by default this exports to
# a port with nothing behind it and drops every span without a word -- which looks exactly
# like a working run. Warn rather than exit: the agent's answer is still worth having.
#
# No -f on the curl. The collector answers 404 at /, and -f turns that into a failure, so the
# check would report a healthy collector as missing. A connection is the question here.
if ! curl -s -o /dev/null --max-time 2 "$OTEL_EXPORTER_OTLP_ENDPOINT" 2>/dev/null; then
  echo "⚠️  Nothing is listening on $OTEL_EXPORTER_OTLP_ENDPOINT — this run's spans go nowhere." >&2
  echo "    kubectl port-forward -n observability svc/otel-collector-opentelemetry-collector 4318:4318 &" >&2
  echo >&2
fi
export AGENT_NAME="${AGENT_NAME:-otter-sre}"

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
