#!/usr/bin/env bash
set -euo pipefail

kubectl port-forward svc/capybara-sre-agent 8088:8088 >/dev/null 2>&1 &
PF=$!; sleep 3
curl -s -XPOST localhost:8088/chat -H 'content-type: application/json' \
  -d "{\"prompt\":\"${1:-The free-plan capybaras are eating our storage budget. Investigate and clean it up.}\"}" | tee /dev/stderr
kill $PF
