#!/usr/bin/env bash
# Run the goose recipe against the cluster's database, exporting to the cluster's collector.
#
# goose stays on the host on purpose: on a Mac, Docker cannot pass the GPU to a container, so a
# containerised Ollama falls back to CPU and gets several times slower.
#
# Needs goose v1.46.0 or newer. Earlier releases emit no gen_ai.* attributes at all: the two PRs
# that added them merged four hours after 1.45.0 was cut, and shipped in 1.46.0.
set -euo pipefail
cd "$(dirname "$0")"

if [ -f ../../.env ]; then set -a; . ../../.env; set +a; fi   # demos/.env
echo "✅ Loaded environment variables."

command -v goose >/dev/null || { echo "goose not installed: brew install block-goose-cli"; exit 1; }

if [ "$GOOSE_PROVIDER" = "ollama" ]; then
  command -v ollama >/dev/null || { echo "ollama not installed: see ollama.com"; exit 1; }
  ollama list 2>/dev/null | grep -q "${GOOSE_MODEL%%:*}" \
    || { echo "Model $GOOSE_MODEL not pulled. Run: ollama pull $GOOSE_MODEL"; exit 1; }
fi

# The MCP server the recipe points at, and the collector goose reports to.
pkill -f "port-forward svc/prod-db-mcp" 2>/dev/null || true
kubectl port-forward svc/prod-db-mcp 8086:8086 >/tmp/pf-prod-mcp.log 2>&1 &
pkill -f "port-forward svc/otel-collector" 2>/dev/null || true
kubectl port-forward svc/otel-collector-opentelemetry-collector 4318:4318 >/tmp/pf-col.log 2>&1 &
echo "✅ Set up port-forwarding."

echo "Waiting on OTel Collector readiness..."
for _ in $(seq 1 30); do
  curl -sf -o /dev/null "http://localhost:4318/" 2>/dev/null && break || sleep 1
  echo "..."
done
echo "✅ Ready!"

export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4318"
export OTEL_SERVICE_NAME="goose"
export OTEL_METRICS_EXPORTER=none
export OTEL_LOGS_EXPORTER=none
# The convention's own variable. It takes the literal string "true", compared case-insensitively;
# `1` is silently ignored. Without it there are no tool call arguments or results to read, which
# is the whole reason for pointing goose at this collector.
export OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true

echo "--- goose $(goose --version 2>/dev/null | tr -d '\n') · provider $GOOSE_PROVIDER · model $GOOSE_MODEL ---"
goose run --recipe tidy-free-plan.yaml