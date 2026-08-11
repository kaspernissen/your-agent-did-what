#!/usr/bin/env bash
# The database both agents read.
#
# The schema is not duplicated into a manifest: the ConfigMap is built from
# postgres/init.sql, the same file the compose path mounts, so there is one definition and
# the two paths cannot drift. An earlier version embedded a copy and claimed the same
# thing, which is how a UUID migration silently failed to reach the cluster.
set -euo pipefail
cd "$(dirname "$0")"

kubectl create configmap capybara-db-init --from-file=init.sql=postgres/init.sql \
  --dry-run=client -o yaml | kubectl apply -f - >/dev/null

kubectl apply -f k8s/ >/dev/null

# init.sql only runs on an empty data directory, so a schema change has to recreate the
# pod or the cluster keeps serving the old tables. Stamping the schema hash on the pod
# template rolls it exactly when the schema changed, and is a no-op otherwise.
kubectl patch deployment capybara-db --type=merge -p \
  "{\"spec\":{\"template\":{\"metadata\":{\"annotations\":{\"capybara.dev/schema-hash\":\"$(shasum -a 256 postgres/init.sql | cut -c1-12)\"}}}}}" >/dev/null

kubectl rollout status deployment/capybara-db --timeout=180s
