#!/usr/bin/env bash
set -euo pipefail

kubectl port-forward svc/capybara-sre-agent 8088:8088 >/dev/null 2>&1 &
PF=$!
trap 'kill $PF 2>/dev/null || true' EXIT

for i in $(seq 1 30); do curl -sf -o /dev/null "http://localhost:8088/q/health" 2>/dev/null && break; sleep 1; done

curl -s -XPOST localhost:8088/chat -H 'content-type: application/json' \
  -d "{\"prompt\":\"${1:-The free-plan capybaras are eating our storage budget. Investigate and clean it up.}\"}" | tee /dev/stderr
