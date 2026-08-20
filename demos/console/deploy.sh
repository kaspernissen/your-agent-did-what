#!/usr/bin/env bash
# Build and deploy the console.
#
# Cheap compared to the agents — no Maven, no pip, just five files into an nginx image — so
# this is safe to re-run on its own while iterating on the page:
#
#   ./deploy.sh && ../01_start-demo.sh
#
# It deploys after the agents in 00_run.sh, but nothing here depends on them existing: the
# upstreams are resolved per request, so a console deployed first serves the page and answers
# 503 on the agent routes until they arrive. That took a deliberate `resolver` plus a variable
# in every proxy_pass — with a literal hostname nginx resolves once at startup and refuses to
# boot when the name is missing, which turns "agents not deployed yet" into a crash loop.
set -euo pipefail
cd "$(dirname "$0")"

CLUSTER="${CAPYBARA_CLUSTER:-capybara}"

echo "--- 1/3 Image ---"
docker build -q -t console:latest . >/dev/null

echo "--- 2/3 Loading into kind ---"
kind load docker-image console:latest --name "$CLUSTER"

echo "--- 3/3 Applying manifests ---"
kubectl apply -f k8s/ >/dev/null

# :latest again, so apply sees no change and would leave the old page being served.
kubectl rollout restart -n frontend deployment/console
kubectl rollout status  -n frontend deployment/console --timeout=120s
