#!/usr/bin/env bash
# Deploy demo 1 into the shared cluster (see ../cluster/setup.sh).
#
# Builds all three Maven modules in the right order — the shared capybara-db-core
# has to be installed before the two applications can resolve it, which is exactly
# what the old setup script got wrong — then bakes images, loads them into kind, and
# applies the manifests.
set -euo pipefail
cd "$(dirname "$0")"

CLUSTER="${CAPYBARA_CLUSTER:-capybara}"
kind get clusters 2>/dev/null | grep -qx "$CLUSTER" \
  || { echo "No cluster '$CLUSTER'. Run ../cluster/setup.sh first."; exit 1; }
kubectl config use-context "kind-${CLUSTER}" >/dev/null

echo "--- 1/4 Building modules (core first, then both apps) ---"
(cd capybara-db-core   && ../capybara-db-mcp/mvnw -q install -DskipTests)
(cd capybara-db-mcp    && ./mvnw -q package -DskipTests)
(cd capybara-sre-agent && ./mvnw -q package -DskipTests)

echo "--- 2/4 Building images ---"
docker build -q -f capybara-db-mcp/src/main/docker/Dockerfile.jvm    -t capybara-db-mcp:latest    capybara-db-mcp    >/dev/null
docker build -q -f capybara-sre-agent/src/main/docker/Dockerfile.jvm -t capybara-sre-agent:latest capybara-sre-agent >/dev/null

echo "--- 3/4 Loading images into kind ---"
kind load docker-image capybara-db-mcp:latest capybara-sre-agent:latest --name "$CLUSTER"

echo "--- 4/4 Applying manifests ---"

# One schema definition: the ConfigMap is built from the same init.sql the compose
# path mounts, rather than a copy pasted into a manifest.
kubectl create configmap capybara-db-init --from-file=init.sql=postgres/init.sql \
  --dry-run=client -o yaml | kubectl apply -f - >/dev/null

kubectl apply -f k8s/

# init.sql only runs on an empty data directory, so a schema change has to recreate
# the pod or the cluster keeps serving the old tables. Stamping the schema hash on
# the pod template rolls it exactly when the schema changed, and is a no-op otherwise.
kubectl patch deployment capybara-db --type=merge -p \
  "{\"spec\":{\"template\":{\"metadata\":{\"annotations\":{\"capybara.dev/schema-hash\":\"$(shasum -a 256 postgres/init.sql | cut -c1-12)\"}}}}}" >/dev/null
kubectl rollout status deployment/capybara-db --timeout=180s

# The image tag is fixed at :latest, so apply alone sees no change and would leave the
# old pods running with the old code. Restart the two applications explicitly — but not
# the database, which would re-seed and throw away whatever state the stage is in.
#
# MCP server first, and fully ready before the agent. Restarting both at once kills the
# agent's SSE connection mid-flight, and quarkus-langchain4j reconnects by blocking the
# Vert.x event loop (QuarkusHttpMcpTransport.startSseChannel), so Vert.x dumps a
# blocked-thread stack every two seconds until the server is back. Ordering it this way
# is also what the README already says to do locally: the agent resolves its tool list
# at startup, so an agent that starts first can come up with no tools at all.
kubectl rollout restart deployment/capybara-db-mcp
kubectl rollout status  deployment/capybara-db-mcp --timeout=180s
kubectl rollout restart deployment/capybara-sre-agent
kubectl rollout status  deployment/capybara-sre-agent --timeout=180s

cat <<EOF

=== Demo 1 deployed ===

  console   kubectl port-forward svc/capybara-sre-agent 8088:8088  →  http://localhost:8088
  spans     kubectl logs -l app.kubernetes.io/name=opentelemetry-collector -f
  jaeger    kubectl port-forward svc/jaeger-query 16686:16686
  psql      kubectl exec -it deploy/capybara-db -- psql -U capybara -d capybara

Switch the tool path:
  kubectl set env deployment/capybara-sre-agent CAPYBARA_TOOLS=local   # or mcp
EOF
