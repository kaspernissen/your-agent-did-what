#!/usr/bin/env bash
# Run demo 2 in the shared cluster (see ../cluster/setup.sh).
#
#   ./deploy.sh                 openinference — llm.* / openinference.*, rewritten by the collector
#   ./deploy.sh openlit         openlit       — already gen_ai.*, so the normalizer has nothing to do
#   ./deploy.sh none            no library    — only the hand-written spans
#
# One agent run per invocation, as a Job, with the logs tailed to completion. That is
# the whole demo: same image, same prompt, same collector, one variable.
set -euo pipefail
cd "$(dirname "$0")"

CLUSTER="${CAPYBARA_CLUSTER:-capybara}"
INSTRUMENTATION="${1:-openinference}"

case "$INSTRUMENTATION" in
  openinference|openlit|none) ;;
  *) echo "Unknown instrumentation '$INSTRUMENTATION' (openinference | openlit | none)"; exit 1 ;;
esac

kind get clusters 2>/dev/null | grep -qx "$CLUSTER" \
  || { echo "No cluster '$CLUSTER'. Run ../cluster/setup.sh first."; exit 1; }
kubectl config use-context "kind-${CLUSTER}" >/dev/null

kubectl get secret anthropic-secret >/dev/null 2>&1 \
  || { echo "No anthropic-secret. Run ../cluster/setup.sh first."; exit 1; }

echo "--- 1/3 Building the image ---"
docker build -q -t capybara-convention-agent:latest agent >/dev/null

echo "--- 2/3 Loading it into kind ---"
kind load docker-image capybara-convention-agent:latest --name "$CLUSTER"

echo "--- 3/3 Running one investigation ($INSTRUMENTATION) ---"
# A Job name cannot be reused while the old one exists, and its pod holds the logs
# from the previous run, so replace it rather than trying to patch it.
kubectl delete job capybara-convention-agent --ignore-not-found >/dev/null

kubectl apply -f - >/dev/null <<YAML
apiVersion: batch/v1
kind: Job
metadata:
  name: capybara-convention-agent
  labels: { app: capybara-convention-agent }
spec:
  backoffLimit: 0          # one run means one run; a retry would double the spans
  ttlSecondsAfterFinished: 3600
  template:
    metadata:
      labels: { app: capybara-convention-agent }
    spec:
      restartPolicy: Never
      containers:
        - name: agent
          image: capybara-convention-agent:latest
          imagePullPolicy: Never          # loaded into kind, never pulled
          env:
            - name: CAPYBARA_INSTRUMENTATION
              value: "$INSTRUMENTATION"
            - name: OTEL_EXPORTER_OTLP_ENDPOINT
              value: http://otel-collector-opentelemetry-collector.default.svc:4318
            - name: ANTHROPIC_API_KEY
              valueFrom:
                secretKeyRef: { name: anthropic-secret, key: api-key }
          resources:
            requests: { memory: 256Mi }
            limits:   { memory: 512Mi }
YAML

kubectl wait --for=condition=ready pod -l app=capybara-convention-agent --timeout=120s >/dev/null 2>&1 || true
kubectl logs -f job/capybara-convention-agent 2>/dev/null || \
  kubectl logs job/capybara-convention-agent

cat <<EOF

=== What to look at ===

  the spans   kubectl logs -l app.kubernetes.io/name=opentelemetry-collector --tail=200
  jaeger      kubectl port-forward svc/jaeger-query 16686:16686

With openinference the library emits llm.* / openinference.*, and gen_ai_normalizer in
the shared collector rewrites it to gen_ai.* — so what the library produced and what
arrives are not the same thing. With openlit it is already gen_ai.* and the normalizer
has nothing to do. Same image, same prompt, same collector.

Run the other side:  ./deploy.sh openlit
EOF
