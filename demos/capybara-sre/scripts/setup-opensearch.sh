#!/usr/bin/env bash
# Idempotent script to deploy OpenSearch, Dashboards, Data Prepper, and rewire the OTel collector
# into the existing kind-capybara-sre cluster.
set -euo pipefail

CONTEXT="kind-capybara-sre"
NAMESPACE="default"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
VALUES_DIR="${REPO_ROOT}/demos/capybara-sre/helm-values"

echo "[1/4] Installing OpenSearch (single-node, security ON, image 2.14.0)..."
helm upgrade --install opensearch opensearch/opensearch \
  --kube-context "${CONTEXT}" \
  --namespace "${NAMESPACE}" \
  --values "${VALUES_DIR}/opensearch-values.yaml" \
  --wait --timeout 10m

echo "[2/4] Installing OpenSearch Dashboards (image 2.14.0)..."
helm upgrade --install opensearch-dashboards opensearch/opensearch-dashboards \
  --kube-context "${CONTEXT}" \
  --namespace "${NAMESPACE}" \
  --values "${VALUES_DIR}/opensearch-dashboards-values.yaml" \
  --wait --timeout 5m

echo "[3/4] Installing Data Prepper (otel_trace_source -> opensearch trace-analytics-raw)..."
helm upgrade --install data-prepper opensearch/data-prepper \
  --kube-context "${CONTEXT}" \
  --namespace "${NAMESPACE}" \
  --values "${VALUES_DIR}/data-prepper-values.yaml" \
  --wait --timeout 5m

echo "[4/4] Upgrading OTel Collector with Data Prepper fan-out (otlp/data-prepper -> :21890)..."
helm upgrade otel-collector open-telemetry/opentelemetry-collector \
  --kube-context "${CONTEXT}" \
  --namespace "${NAMESPACE}" \
  --values "${VALUES_DIR}/otel-collector-values.yaml" \
  --wait --timeout 5m

echo ""
echo "All components deployed. Verify with:"
echo "  kubectl --context ${CONTEXT} get pods"
echo ""
echo "Port-forward OpenSearch:   kubectl --context ${CONTEXT} port-forward svc/opensearch-cluster-master 9200:9200"
echo "Port-forward Dashboards:   kubectl --context ${CONTEXT} port-forward svc/opensearch-dashboards 5601:5601"
echo "Dashboards URL (after pf): http://localhost:5601  (login: admin / see values file)"
echo "Trace Analytics:           http://localhost:5601/app/observability-traces"
