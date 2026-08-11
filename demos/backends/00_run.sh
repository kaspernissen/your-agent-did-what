#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
./scripts/01_up.sh
./scripts/02_run_agent.sh
./scripts/03_open_uis.sh
