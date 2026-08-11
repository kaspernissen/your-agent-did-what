#!/usr/bin/env bash
# Deploy demo 2 into the shared cluster (see ../cluster/setup.sh).
#
# Both convention agents come up and stay up, so there is nothing to build or wait for
# during the talk -- you trigger them from demo 1's console and jump between them.
#
#   ./deploy.sh
#
# One image, two Deployments. Both instrumentation libraries are inside the image and
# the choice is an environment variable, because two images could drift and then a
# difference in the spans would stop being attributable to the convention.
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
kubectl rollout restart deployment/convention-openinference deployment/convention-openlit
kubectl rollout status  deployment/convention-openinference --timeout=180s
kubectl rollout status  deployment/convention-openlit       --timeout=180s

cat <<EOF

=== Demo 2 deployed ===

Both agents are up. Trigger them from demo 1's console (the Conventions tab), or
directly:

  kubectl port-forward svc/convention-openinference 8001:8000
  curl -XPOST localhost:8001/run | jq .

  the spans   kubectl logs -l app.kubernetes.io/name=opentelemetry-collector --tail=200
  jaeger      kubectl port-forward svc/jaeger-query 16686:16686

In Jaeger the two are separate services -- convention-openinference and
convention-openlit -- so you can open one trace of each and compare.

One caveat worth knowing on stage: Jaeger shows what ARRIVED, after
gen_ai_normalizer. The openinference trace is half-translated there, which is the
finding. To see what the library actually emitted, read the collector's debug output.
EOF
