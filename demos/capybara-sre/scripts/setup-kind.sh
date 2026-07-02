#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="capybara-sre"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Capybara SRE - KIND Setup ==="
echo "Project root: $PROJECT_ROOT"
echo ""

# -------------------------------------------------------
# Pre-flight: Require kind
# -------------------------------------------------------
if ! command -v kind &>/dev/null; then
  echo "kind not found, installing..."
  brew install kind
fi

# -------------------------------------------------------
# Pre-flight: Require ANTHROPIC_API_KEY
# -------------------------------------------------------
# Source the shared demos/.env (same pattern as demos/agent/run.sh) so secrets
# live in one git-ignored file instead of a manual export.
if [ -f "$PROJECT_ROOT/../.env" ]; then set -a; . "$PROJECT_ROOT/../.env"; set +a; fi
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  echo "ERROR: ANTHROPIC_API_KEY is not set."
  echo "The agent services require an Anthropic API key to function."
  echo ""
  echo "Set it in demos/.env (cp demos/.env.template demos/.env) or export it:"
  echo "  export ANTHROPIC_API_KEY=<YOUR_KEY>"
  exit 1
fi

# -------------------------------------------------------
# 1. Create KIND cluster
# -------------------------------------------------------
echo "--- Step 1: Creating KIND cluster '$CLUSTER_NAME' ---"
if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
  echo "Cluster '$CLUSTER_NAME' already exists, skipping creation."
else
  kind create cluster --name "$CLUSTER_NAME"
fi
kubectl config use-context "kind-${CLUSTER_NAME}"
kubectl cluster-info --context "kind-${CLUSTER_NAME}"
echo ""

# -------------------------------------------------------
# 2. Create secrets
# -------------------------------------------------------
echo "--- Step 2: Creating secrets ---"
kubectl create secret generic anthropic-secret \
  --from-literal=api-key="$ANTHROPIC_API_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -
echo "Secret 'anthropic-secret' created."
echo ""

# -------------------------------------------------------
# 3. Install Jaeger
# -------------------------------------------------------
echo "--- Step 3: Installing Jaeger ---"
helm repo add jaegertracing https://jaegertracing.github.io/helm-charts 2>/dev/null || true
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts 2>/dev/null || true
helm repo update
if helm status jaeger &>/dev/null; then
  echo "Jaeger is already installed, skipping."
else
  helm install jaeger jaegertracing/jaeger --version 3.4.1 \
    -f "$PROJECT_ROOT/helm-values/jaeger-values.yaml" \
    --wait
fi
echo "Jaeger pods:"
kubectl get pods -l app.kubernetes.io/name=jaeger
echo ""

# -------------------------------------------------------
# 4. Install OpenTelemetry Collector
# -------------------------------------------------------
# Release name: otel-collector
# Resulting Service: otel-collector-opentelemetry-collector (default namespace)
# Agent points to: http://otel-collector-opentelemetry-collector.default.svc.cluster.local:4317
# Collector forwards to: jaeger-collector.default.svc.cluster.local:4317
echo "--- Step 4: Installing OpenTelemetry Collector ---"
if helm status otel-collector &>/dev/null; then
  echo "OpenTelemetry Collector is already installed, upgrading with current config."
  helm upgrade otel-collector open-telemetry/opentelemetry-collector \
    -f "$PROJECT_ROOT/helm-values/otel-collector-values.yaml" \
    --wait
else
  helm install otel-collector open-telemetry/opentelemetry-collector \
    -f "$PROJECT_ROOT/helm-values/otel-collector-values.yaml" \
    --wait
fi
echo "OpenTelemetry Collector pods:"
kubectl get pods -l app.kubernetes.io/name=opentelemetry-collector
echo ""

# -------------------------------------------------------
# 5. Build and load images into kind
# -------------------------------------------------------
echo "--- Step 5: Building Docker images ---"
echo "Building capybara-db-mcp..."
docker build -t capybara-db-mcp:latest "$PROJECT_ROOT/capybara-db-mcp"

echo "Building capybara-sre-agent..."
docker build -t capybara-sre-agent:latest "$PROJECT_ROOT/capybara-sre-agent"

echo "Loading images into kind cluster '$CLUSTER_NAME'..."
kind load docker-image capybara-db-mcp:latest --name "$CLUSTER_NAME"
kind load docker-image capybara-sre-agent:latest --name "$CLUSTER_NAME"
echo ""

# -------------------------------------------------------
# 6. Deploy application manifests
# -------------------------------------------------------
echo "--- Step 6: Deploying application manifests ---"
kubectl apply -f "$PROJECT_ROOT/k8s/"
kubectl rollout status deployment/capybara-db-mcp --timeout=120s
kubectl rollout status deployment/capybara-sre-agent --timeout=180s || true
echo ""

echo "=== Setup complete ==="
echo ""
echo "Check pod status:"
echo "  kubectl get pods"
echo ""
echo "To access the SRE agent:"
echo "  kubectl port-forward svc/capybara-sre-agent 8088:8088"
echo "Then POST to http://localhost:8088/chat"
echo ""
echo "To access Jaeger UI:"
echo "  kubectl port-forward svc/jaeger-query 16686:16686"
echo "Then open http://localhost:16686"
echo ""
echo "To tear down the cluster:"
echo "  kind delete cluster --name $CLUSTER_NAME"
