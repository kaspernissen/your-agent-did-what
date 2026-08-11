#!/usr/bin/env bash
# Start the demo collector on :14317, printing spans to stdout.
#
# Adds the Dash0 exporter automatically when DASH0_AUTH_TOKEN is set in demos/.env,
# and stays stdout-only when it is not — so the output you read on stage is never
# polluted by export failures from an unconfigured vendor endpoint.
#
#   ./scripts/collector.sh          # follow the output (Ctrl-C to stop)
#   ./scripts/collector.sh -d       # detached; docker logs capy-col
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f ../.env ] && { set -a; . ../.env; set +a; }

NAME="${CAPYBARA_COLLECTOR:-capy-col}"
IMAGE="otel/opentelemetry-collector-contrib:0.158.0"

if [ -n "${DASH0_AUTH_TOKEN:-}" ]; then
  CONFIG="otel-collector-config.dash0.yaml"
  echo "Dash0 token found — exporting to stdout AND ${DASH0_ENDPOINT_OTLP_GRPC_HOSTNAME:-<unset>}" >&2
else
  CONFIG="otel-collector-config.yaml"
  echo "No DASH0_AUTH_TOKEN — stdout only. Set it in demos/.env for the vendor path." >&2
fi

docker rm -f "$NAME" >/dev/null 2>&1 || true
exec docker run ${1:--i} --rm --name "$NAME" -p 14317:4317 \
  -e DASH0_AUTH_TOKEN="${DASH0_AUTH_TOKEN:-}" \
  -e DASH0_DATASET="${DASH0_DATASET:-default}" \
  -e DASH0_ENDPOINT_OTLP_GRPC_HOSTNAME="${DASH0_ENDPOINT_OTLP_GRPC_HOSTNAME:-ingress.eu-west-1.aws.dash0.com}" \
  -e DASH0_ENDPOINT_OTLP_GRPC_PORT="${DASH0_ENDPOINT_OTLP_GRPC_PORT:-4317}" \
  -v "$PWD/$CONFIG:/etc/otelcol/config.yaml:ro" \
  "$IMAGE" --config=/etc/otelcol/config.yaml
