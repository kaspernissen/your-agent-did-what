#!/usr/bin/env bash
# Open every port-forward the demo needs, and wait until each one answers.
#
# Run this after any deploy, kubectl set env, or rollout. A port-forward is bound to a
# specific pod, so anything that replaces a pod silently kills it — the console simply
# stops responding, which looks like a broken demo rather than a broken tunnel.
#
#   ./01_start-demo.sh            open them and wait for all three
#   ./01_start-demo.sh --status   just report what is reachable
set -uo pipefail
cd "$(dirname "$0")"

# service:local:remote:probe-path
TARGETS=(
  "capybara-sre:8088:8088:/"
  "jaeger-query:16686:16686:/"
  "prometheus:9090:9090:/-/ready"
)

reachable() {   # port, path
  curl -sf -o /dev/null --max-time 2 "http://localhost:$1$2"
}

status() {
  local all_ok=0
  for t in "${TARGETS[@]}"; do
    IFS=: read -r svc local _ path <<<"$t"
    if reachable "$local" "$path"; then
      printf '  %-22s http://localhost:%-6s up\n' "$svc" "$local"
    else
      printf '  %-22s http://localhost:%-6s DOWN\n' "$svc" "$local"
      all_ok=1
    fi
  done
  return $all_ok
}

if [ "${1:-}" = "--status" ]; then
  status
  exit $?
fi

# Kill only our own forwards, and only for these services, so an unrelated tunnel in
# another terminal survives.
for t in "${TARGETS[@]}"; do
  IFS=: read -r svc local _ _ <<<"$t"
  pkill -f "port-forward svc/${svc} ${local}:" 2>/dev/null
done
sleep 1

for t in "${TARGETS[@]}"; do
  IFS=: read -r svc local remote _ <<<"$t"
  # nohup, because a plain background job dies with the shell that started it — which is
  # how several of these forwards were lost without anyone noticing.
  nohup kubectl port-forward "svc/${svc}" "${local}:${remote}" >"/tmp/pf-${svc}.log" 2>&1 &
done

echo "Waiting for the tunnels…"
for _ in $(seq 1 45); do
  status >/dev/null 2>&1 && break
  sleep 1
done

status
ok=$?

cat <<EOF

  console     http://localhost:8088     ask either agent
  jaeger      http://localhost:16686    traces
  prometheus  http://localhost:9090     graph capybara_records

EOF

if [ $ok -ne 0 ]; then
  echo "Something is not answering. Check the pods:  kubectl get pods"
  echo "Logs for each tunnel are in /tmp/pf-<service>.log"
  exit 1
fi
