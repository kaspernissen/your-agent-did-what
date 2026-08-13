#!/usr/bin/env bash
# Create the shared kind cluster both demos deploy into: a collector and Jaeger.
#
# Run once. Then ../infrastructure/deploy.sh and ../agents/deploy.sh add their workloads to
# the same cluster, sending to the same collector. ../00_run.sh does all three in order.
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
helm upgrade --install jaeger jaegertracing/jaeger --version 4.12.0 \
  -f ../observability/jaeger/values.yaml --wait

echo "--- Prometheus ---"
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts >/dev/null 2>&1 || true
helm repo update >/dev/null
helm upgrade --install prometheus prometheus-community/prometheus \
  -f ../observability/prometheus/values.yaml --wait

echo "--- OpenTelemetry Collector (with gen_ai_normalizer) ---"
# The vendor path is opt-in on the token, exactly like the local compose path. Without
# it the collector still exports to stdout and Jaeger, so the demo works offline.
DASH0_VALUES=()
if [ -n "${DASH0_AUTH_TOKEN:-}" ]; then
  kubectl create secret generic dash0-secret \
    --from-literal=token="$DASH0_AUTH_TOKEN" \
    --from-literal=dataset="${DASH0_DATASET:-default}" \
    --from-literal=endpoint="${DASH0_ENDPOINT_OTLP_GRPC_HOSTNAME:-ingress.eu-west-1.aws.dash0.com}" \
    --from-literal=port="${DASH0_ENDPOINT_OTLP_GRPC_PORT:-4317}" \
    --dry-run=client -o yaml | kubectl apply -f -
  DASH0_VALUES=(-f ../observability/collector/values.dash0.yaml)
  echo "Dash0 token found — also exporting to ${DASH0_ENDPOINT_OTLP_GRPC_HOSTNAME:-ingress.eu-west-1.aws.dash0.com}"
else
  echo "No DASH0_AUTH_TOKEN — stdout and Jaeger only. Set it in demos/.env for the vendor path."
fi

helm upgrade --install otel-collector open-telemetry/opentelemetry-collector \
  -f ../observability/collector/values.yaml "${DASH0_VALUES[@]}" --wait

cat <<EOF

=== Shared cluster ready ===

  collector  otel-collector-opentelemetry-collector.default.svc:4317 (gRPC) / :4318 (HTTP)
  jaeger UI  kubectl port-forward svc/jaeger 16686:16686  →  http://localhost:16686
  prometheus kubectl port-forward svc/prometheus 9090:9090       →  http://localhost:9090
  spans      kubectl logs -l app.kubernetes.io/name=opentelemetry-collector -f

Next:
  ../infrastructure/deploy.sh   the database
  ../agents/deploy.sh           both agents

Or ../00_run.sh to do all of it, then ../01_start-demo.sh for the port-forwards.
Tear down:  ../02_cleanup.sh
EOF
