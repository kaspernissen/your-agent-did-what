#!/usr/bin/env bash
# Build and deploy both agents.
#
#   capybara-sre      Java · Quarkus + LangChain4j, tools over MCP, reads PostgreSQL
#   sre-agents-mcp   the MCP server it calls
#   beaver-sre        Python · Anthropic SDK, instrumented by OpenInference
#   otter-sre         the same agent, instrumented by OpenLLMetry
#
# customer-db-core is a shared library and has to be installed before either Java
# application can resolve it — which is exactly what the original setup script got wrong.
set -euo pipefail
cd "$(dirname "$0")"

CLUSTER="${CAPYBARA_CLUSTER:-capybara}"

echo "--- 1/4 Java modules (core first, then both applications) ---"
(cd customer-db-core && ../customer-db-mcp/mvnw -q install -DskipTests)
(cd customer-db-mcp  && ./mvnw -q package -DskipTests)
(cd capybara-sre     && ./mvnw -q package -DskipTests)

# The two Python agents are separate copies; this fails if they have drifted apart in
# anything but the instrumentation library.
./check-agents-agree.sh

echo "--- 2/4 Images ---"
docker build -q -f customer-db-mcp/src/main/docker/Dockerfile.jvm -t customer-db-mcp:latest  customer-db-mcp >/dev/null
docker build -q -f capybara-sre/src/main/docker/Dockerfile.jvm    -t capybara-sre:latest     capybara-sre    >/dev/null
# One image per Python agent. They were a single image switched by an env var; separate
# images mean what a pod emits is decided by the Dockerfile that built it, and each
# directory is readable on its own as an example of instrumenting under one convention.
docker build -q -t beaver-sre:latest beaver-sre >/dev/null
docker build -q -t otter-sre:latest  otter-sre  >/dev/null

echo "--- 3/4 Loading into kind ---"
kind load docker-image customer-db-mcp:latest capybara-sre:latest beaver-sre:latest \
  otter-sre:latest --name "$CLUSTER"

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
# Both MCP servers, and goose-mcp is easy to forget: it runs the same image under different
# credentials, so a stale replica silently serves the Goose path with old code. It did, for
# three days, which is why that path emitted no server spans at all.
kubectl rollout restart deployment/sre-agents-mcp deployment/goose-mcp
kubectl rollout status  deployment/sre-agents-mcp --timeout=180s
kubectl rollout status  deployment/goose-mcp    --timeout=180s

kubectl rollout restart deployment/capybara-sre deployment/beaver-sre deployment/otter-sre
kubectl rollout status  deployment/capybara-sre --timeout=180s
kubectl rollout status  deployment/beaver-sre   --timeout=180s
kubectl rollout status  deployment/otter-sre    --timeout=180s
