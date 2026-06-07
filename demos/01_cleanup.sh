#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
docker compose --profile jaeger --profile phoenix --profile openlit --profile langfuse down -v
echo "All demo containers + volumes removed."
