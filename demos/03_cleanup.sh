#!/usr/bin/env bash
# Delete the shared cluster and everything in it: the agents, the console, the collector,
# Jaeger, Prometheus and the database. Nothing outside kind is touched, so the images stay in
# your local Docker and a re-run of ./00_run.sh is quick.
set -euo pipefail
CLUSTER="${CAPYBARA_CLUSTER:-capybara}"
kind delete cluster --name "$CLUSTER"
