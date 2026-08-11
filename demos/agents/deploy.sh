#!/usr/bin/env bash
# Build and deploy both agents.
#
#   capybara-sre      Java · Quarkus + LangChain4j, tools over MCP, reads PostgreSQL
#   capybara-db-mcp   the MCP server it calls
#   beaver-sre        Python · Anthropic SDK, instrumented by OpenInference
#
# capybara-db-core is a shared library and has to be installed before either Java
# application can resolve it — which is exactly what the original setup script got wrong.
set -euo pipefail
cd "$(dirname "$0")"

CLUSTER="${CAPYBARA_CLUSTER:-capybara}"

echo "--- 1/4 Java modules (core first, then both applications) ---"
(cd capybara-db-core && ../capybara-db-mcp/mvnw -q install -DskipTests)
(cd capybara-db-mcp  && ./mvnw -q package -DskipTests)
(cd capybara-sre     && ./mvnw -q package -DskipTests)

echo "--- 2/4 Images ---"
docker build -q -f capybara-db-mcp/src/main/docker/Dockerfile.jvm -t capybara-db-mcp:latest  capybara-db-mcp >/dev/null
docker build -q -f capybara-sre/src/main/docker/Dockerfile.jvm    -t capybara-sre:latest     capybara-sre    >/dev/null
docker build -q -t beaver-sre:latest beaver-sre >/dev/null

echo "--- 3/4 Loading into kind ---"
kind load docker-image capybara-db-mcp:latest capybara-sre:latest beaver-sre:latest --name "$CLUSTER"

echo "--- 4/4 Applying manifests ---"
kubectl apply -f k8s/ >/dev/null

# The tags are fixed at :latest, so apply sees no change and would leave the old pods
# running the old code.
#
# The MCP server goes first and is fully ready before the agent. Restarting both at once
# kills the agent's SSE connection mid-flight, and quarkus-langchain4j reconnects by
# blocking the Vert.x event loop, so Vert.x dumps a blocked-thread stack every two seconds
# until the server is back. The agent also resolves its tool list at startup, so one that
# starts first can come up with no tools at all.
kubectl rollout restart deployment/capybara-db-mcp
kubectl rollout status  deployment/capybara-db-mcp --timeout=180s

kubectl rollout restart deployment/capybara-sre deployment/beaver-sre
kubectl rollout status  deployment/capybara-sre --timeout=180s
kubectl rollout status  deployment/beaver-sre   --timeout=180s
