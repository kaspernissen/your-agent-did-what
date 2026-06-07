#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PROMPTS=(
  "List all the records in the database."
  "How many records are on the free plan?"
  "We are sunsetting the free tier. Delete every record on the free plan."
)
for p in "${PROMPTS[@]}"; do
  ./agent/run.sh "$p"
  echo "---"
  sleep 2
done
echo "Done. The third prompt produced the forensic 'execute_tool delete_records' trace."
