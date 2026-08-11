#!/usr/bin/env bash
set -euo pipefail
cat <<'EOF'
Backend UIs (whichever profiles are running):
  Jaeger    http://localhost:16686                 (generic trace viewer — no GenAI awareness)
  Phoenix   http://localhost:6006                  (GenAI-native, OpenInference — our gen_ai.* shows as plain spans)
  OpenLIT   http://localhost:3001                  (OTel-native GenAI dashboard; login user@openlit.io / openlituser)
  Langfuse  http://localhost:3000                  (OSS LLM platform; login admin@demo.local / changeme-12345)
Vendor (if DASH0_AUTH_TOKEN set): your Dash0 dashboard.
EOF
