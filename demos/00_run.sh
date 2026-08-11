#!/usr/bin/env bash
# Build and deploy everything, from nothing to a cluster ready to present.
#
#   ./00_run.sh          the shared cluster, then both demos
#   ./01_start-demo.sh   open the port-forwards and wait for them
#   ./02_cleanup.sh      delete the cluster
#
# Safe to re-run: the cluster is reused if it exists, and each demo rebuilds and rolls its
# own pods. Roughly five minutes cold, under two warm.
#
# The individual steps still exist and are still the thing to use while iterating on one
# piece — cluster/setup.sh, infrastructure/deploy.sh, agents/deploy.sh. This just runs them
# in the order they depend on each other.
set -euo pipefail
cd "$(dirname "$0")"

# ANTHROPIC_API_KEY is checked here rather than three minutes into a build, because
# discovering it in the last step means doing the first two again.
if [ -f .env ]; then set -a; . ./.env; set +a; fi
: "${ANTHROPIC_API_KEY:?Set ANTHROPIC_API_KEY in demos/.env (see .env.template)}"

echo "═══ 1/3 · Shared cluster ═══════════════════════════════════════════"
./cluster/setup.sh

echo
echo "═══ 2/3 · Infrastructure · the database both agents read ═══════════"
./infrastructure/deploy.sh

echo
echo "═══ 3/3 · Agents · Capybara, its MCP server, and Beaver ════════════"
./agents/deploy.sh

cat <<'DONE'

═══════════════════════════════════════════════════════════════════════

  Everything is deployed. Next:

    ./01_start-demo.sh        open the port-forwards, wait until they answer

  Then, on stage:

    1. Reset the database, and show the five capybaras
    2. Unleash the kangaroos — three rows gone, and not by the agent
    3. Watch capybara_records drop in Prometheus
    4. Ask Capybara what happened; read the judge
    5. Ask Beaver the same thing, and open its trace

  Tear down with ./02_cleanup.sh

═══════════════════════════════════════════════════════════════════════
DONE
