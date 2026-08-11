#!/usr/bin/env bash
# Delete the shared cluster and everything in it.
set -euo pipefail
CLUSTER="${CAPYBARA_CLUSTER:-capybara}"
kind delete cluster --name "$CLUSTER"
