#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] || cp .env.template .env
set -a; . .env; set +a

# Build the Langfuse OTLP Basic-auth header from the demo keys.
export LANGFUSE_OTEL_BASIC_AUTH="$(printf '%s' "${LANGFUSE_PUBLIC_KEY}:${LANGFUSE_SECRET_KEY}" | base64 | tr -d '\n')"

PROFILES=(--profile jaeger --profile phoenix --profile openlit --profile langfuse)
echo "Starting collector + all backends (Langfuse adds ~60-90s for migrations)..."
docker compose "${PROFILES[@]}" up -d
echo "Up. Waiting for Langfuse migrations..."; sleep 75
docker compose "${PROFILES[@]}" ps
