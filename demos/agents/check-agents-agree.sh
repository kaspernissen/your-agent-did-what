#!/usr/bin/env bash
# beaver-sre and otter-sre are separate copies on purpose — each one readable on its own as an
# example of instrumenting an agent under one convention. The cost of that choice is drift: if
# the loop, the tools or the database access diverge, the two agents differ in more than the
# instrumentation library and the talk's comparison quietly stops being valid.
#
# So the files that are supposed to be identical are checked to be identical. This runs from
# deploy.sh; a failure here is not a style complaint, it is the comparison breaking.
#
# agent.py is deliberately NOT in the list: the span vocabulary is the one thing that differs.
set -euo pipefail
cd "$(dirname "$0")"

SHARED=(app.py db.py mcp_db.py service.py tools.py tests/test_tools.py tests/test_mcp_db.py)
fail=0

for f in "${SHARED[@]}"; do
  if ! diff -q "beaver-sre/$f" "otter-sre/$f" >/dev/null 2>&1; then
    echo "DRIFT  $f differs between beaver-sre and otter-sre"
    diff -u "beaver-sre/$f" "otter-sre/$f" | sed -n '1,20p' | sed 's/^/    /'
    fail=1
  fi
done

if [ "$fail" -ne 0 ]; then
  echo
  echo "These files are meant to be byte-identical: the two agents must differ only in which"
  echo "library instruments the model call. Copy the intended version across, or if the change"
  echo "belongs to one agent only, say so in its README and remove the file from SHARED here."
  exit 1
fi

echo "✅ beaver-sre and otter-sre agree on all ${#SHARED[@]} shared files"
