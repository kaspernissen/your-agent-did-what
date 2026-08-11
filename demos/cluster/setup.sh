#!/usr/bin/env bash
# Create the shared kind cluster both demos deploy into: a collector and Jaeger.
#
# Run once. Then demo-1/deploy.sh and demo-2/deploy.sh add their own workloads to
# the same cluster and send to the same collector.
set -euo pipefail
cd "$(dirname "$0")"

CLUSTER="${CAPYBARA_CLUSTER:-capybara}"

for c in kind kubectl helm docker; do
  command -v "$c" >/dev/null || { echo "$c is required but not installed"; exit 1; }
done

if kind get clusters 2>/dev/null | grep -qx "$CLUSTER"; then
  echo "Cluster '$CLUSTER' already exists."
else
  echo "--- Creating kind cluster '$CLUSTER' ---"
  kind create cluster --name "$CLUSTER"
fi
kubectl config use-context "kind-${CLUSTER}" >/dev/null

echo "--- The Anthropic key, as a secret both demos can use ---"
if [ -f ../.env ]; then set -a; . ../.env; set +a; fi
: "${ANTHROPIC_API_KEY:?Set ANTHROPIC_API_KEY in demos/.env}"
kubectl create secret generic anthropic-secret \
  --from-literal=api-key="$ANTHROPIC_API_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "--- Jaeger ---"
helm repo add jaegertracing https://jaegertracing.github.io/helm-charts >/dev/null 2>&1 || true
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts >/dev/null 2>&1 || true
helm repo update >/dev/null
helm upgrade --install jaeger jaegertracing/jaeger --version 3.4.1 \
  -f jaeger-values.yaml --wait

echo "--- OpenTelemetry Collector (with gen_ai_normalizer) ---"
helm upgrade --install otel-collector open-telemetry/opentelemetry-collector \
  -f otel-collector-values.yaml --wait

cat <<EOF

=== Shared cluster ready ===

  collector  otel-collector-opentelemetry-collector.default.svc:4317 (gRPC) / :4318 (HTTP)
  jaeger UI  kubectl port-forward svc/jaeger-query 16686:16686  →  http://localhost:16686
  spans      kubectl logs -l app.kubernetes.io/name=opentelemetry-collector -f

Next:
  ../demo-1/deploy.sh     the capybara incident
  ../demo-2/deploy.sh     the convention swap

Tear down:  ./teardown.sh
EOF
