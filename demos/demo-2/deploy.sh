#!/usr/bin/env bash
# Deploy demo 2 into the shared cluster (see ../cluster/setup.sh).
#
# Beaver SRE comes up and stays up, so there is nothing to build or wait for during the
# talk -- you ask it questions from the console, in the same interface as Capybara.
#
#   ./deploy.sh
#
# It runs OpenInference, which is the point: the library emits llm.* and the collector's
# gen_ai_normalizer rewrites part of it, so one span arrives carrying both vocabularies
# at once. That span is what you put on screen.
set -euo pipefail
cd "$(dirname "$0")"

CLUSTER="${CAPYBARA_CLUSTER:-capybara}"

kind get clusters 2>/dev/null | grep -qx "$CLUSTER" \
  || { echo "No cluster '$CLUSTER'. Run ../cluster/setup.sh first."; exit 1; }
kubectl config use-context "kind-${CLUSTER}" >/dev/null

kubectl get secret anthropic-secret >/dev/null 2>&1 \
  || { echo "No anthropic-secret. Run ../cluster/setup.sh first."; exit 1; }

echo "--- 1/3 Building the image ---"
docker build -q -t capybara-convention-agent:latest agent >/dev/null

echo "--- 2/3 Loading it into kind ---"
kind load docker-image capybara-convention-agent:latest --name "$CLUSTER"

echo "--- 3/3 Applying manifests ---"
kubectl apply -f k8s/ >/dev/null

# The tag is fixed at :latest, so apply sees no change and would leave the old pods
# running the old code. The same trap demo 1's deploy.sh has.
kubectl rollout restart deployment/beaver-sre
kubectl rollout status  deployment/beaver-sre --timeout=180s

# Left over from when this demo was a comparison between two libraries. Removing them
# keeps Jaeger's service dropdown to the three services the talk actually uses.
kubectl delete deployment,service convention-openinference convention-openlit \
  --ignore-not-found >/dev/null 2>&1 || true
kubectl delete job capybara-convention-agent --ignore-not-found >/dev/null 2>&1 || true

cat <<EOF

=== Beaver SRE deployed ===

Ask it questions from the console's "Beaver SRE" tab, or directly:

  kubectl port-forward svc/beaver-sre 8001:8000
  curl -XPOST localhost:8001/run -d '{"prompt":"what happened?"}' | jq .

  the spans   kubectl logs -l app.kubernetes.io/name=opentelemetry-collector --tail=200
  jaeger      kubectl port-forward svc/jaeger-query 16686:16686

In Jaeger it is the service "beaver-sre". Open a trace and look at the chat span: it
carries llm.* AND gen_ai.* together, because the library emitted the first and the
collector rewrote some of it into the second. Half-translated, in one place, easy to
point at before going back to the slides.
EOF
