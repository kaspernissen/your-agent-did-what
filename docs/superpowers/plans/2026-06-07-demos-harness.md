# Demos Harness Implementation Plan

> **Historical.** A spec or plan from an earlier stage of this project, kept as a record of
> what was decided and why. It describes structures that no longer exist — the demo-1 /
> demo-2 split, the multi-backend fan-out, the Arconia and Spring AI demos, the over-quota
> scenario. For how the repo works today see [`AGENTS.md`](../../../AGENTS.md) and
> [`demos/README.md`](../../../demos/README.md).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a docker-compose "test harness" under `demos/` where one OTel-instrumented tool-calling Claude agent fans out the same GenAI trace to Jaeger, Arize Phoenix, OpenLIT, Langfuse, and (optionally) Dash0, so the talk can compare how each backend renders it.

**Architecture:** A local Python agent (Anthropic SDK + OpenLIT auto-instrumentation, plus hand-written `execute_tool` spans following OTel GenAI semconv) exports OTLP to a single OpenTelemetry Collector. The collector fans out to a `debug` exporter plus one exporter per backend. Each backend is a docker-compose **profile** so you start only what you want; the collector always runs.

**Tech Stack:** Docker Compose (profiles), `otel/opentelemetry-collector-contrib`, Python 3.11 (`anthropic`, `openlit`, `opentelemetry-{api,sdk}`), Jaeger v2, Arize Phoenix, OpenLIT (+ClickHouse), Langfuse v3 (+Postgres/ClickHouse/Redis/MinIO).

**Working directory for all paths below:** `/Users/kaspernissen/kaspernissen/your-agent-did-what/demos`

**Commits:** The user does all commits. Where a task says "Commit", stage the files and STOP — tell the user the task is ready to commit with the suggested message; do not run `git commit`.

---

## File Structure

```
demos/
  README.md                          # narrative (3 questions) + per-UI guide + forensics callout + reference section
  .env.template                      # ANTHROPIC_API_KEY, Langfuse demo keys, optional DASH0_*
  .gitignore                         # .env, __pycache__, .venv
  docker-compose.yml                 # collector (always) + backends behind profiles + deps
  collector/
    otel-collector-config.yaml       # otlp receiver -> debug + 5 exporters
  agent/
    tools.py                         # in-memory database tool (list/query/delete)
    app.py                           # agent loop: OpenLIT init + anthropic tool-use + manual execute_tool spans
    requirements.txt
    run.sh                           # local run against collector on localhost:4318
    tests/test_tools.py              # unit tests for the database tool
  scripts/
    01_up.sh                         # compose up (all profiles), wait for health
    02_run_agent.sh                  # fire scripted prompts incl. the delete one
    03_open_uis.sh                   # print backend URLs
  00_run.sh                          # end-to-end: up + run agent + print URLs
  01_cleanup.sh                      # compose down -v
```

---

### Task 1: Scaffold directory, .gitignore, .env.template

**Files:**
- Create: `demos/.gitignore`
- Create: `demos/.env.template`

- [ ] **Step 1: Create the directory tree**

Run:
```bash
cd /Users/kaspernissen/kaspernissen/your-agent-did-what
mkdir -p demos/collector demos/agent/tests demos/scripts
```
Expected: directories created, no output.

- [ ] **Step 2: Write `demos/.gitignore`**

```gitignore
.env
__pycache__/
*.pyc
.venv/
agent/.venv/
```

- [ ] **Step 3: Write `demos/.env.template`**

```bash
# Anthropic — the agent authenticates with this (sk-ant-...)
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Langfuse demo project keys (used both to bootstrap Langfuse and to build the
# collector's OTLP Basic-auth header). Fine to leave as-is for a local demo.
LANGFUSE_PUBLIC_KEY=pk-lf-local-demo
LANGFUSE_SECRET_KEY=sk-lf-local-demo

# Optional: vendor path. If DASH0_AUTH_TOKEN is empty the collector will log
# harmless export errors for the dash0 exporter — that's expected.
DASH0_AUTH_TOKEN=
DASH0_DATASET=default
DASH0_ENDPOINT_OTLP_GRPC_HOSTNAME=ingress.eu-west-1.aws.dash0.com
DASH0_ENDPOINT_OTLP_GRPC_PORT=4317
```

- [ ] **Step 4: Verify**

Run: `ls -la demos demos/collector demos/agent demos/scripts`
Expected: all four directories exist; `.gitignore` and `.env.template` present in `demos/`.

- [ ] **Step 5: Stage for commit (do NOT commit)**

```bash
git add demos/.gitignore demos/.env.template
```
Tell the user: ready to commit — suggested message `chore(demos): scaffold harness directory + env template`.

---

### Task 2: Database tool (`tools.py`) — TDD

**Files:**
- Create: `demos/agent/tools.py`
- Test: `demos/agent/tests/test_tools.py`

- [ ] **Step 1: Write the failing test**

`demos/agent/tests/test_tools.py`:
```python
import importlib

import tools  # run pytest from demos/agent


def setup_function():
    importlib.reload(tools)  # reset in-memory state between tests


def test_list_records_returns_seed():
    assert len(tools.list_records()) == 3


def test_query_filters_by_plan():
    free = tools.query(plan="free")
    assert {r["user"] for r in free} == {"bob", "carol"}


def test_delete_records_by_plan_removes_matching():
    result = tools.delete_records(plan="free")
    assert result == {"deleted": 2, "remaining": 1}
    assert tools.list_records()[0]["user"] == "alice"


def test_delete_all_records():
    result = tools.delete_records()
    assert result["remaining"] == 0


def test_dispatch_routes_by_name():
    fn = tools.dispatch("list_records")
    assert callable(fn)
    assert len(fn()) == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd demos/agent && python -m pytest tests/test_tools.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools'` (or import error).

- [ ] **Step 3: Write minimal implementation**

`demos/agent/tools.py`:
```python
"""An in-memory fake 'database' the demo agent operates on.

State is module-level so a single agent run mutates it; reload the module to reset.
"""

_SEED = [
    {"id": 1, "user": "alice", "plan": "pro"},
    {"id": 2, "user": "bob", "plan": "free"},
    {"id": 3, "user": "carol", "plan": "free"},
]

_RECORDS = [dict(r) for r in _SEED]


def list_records():
    """Return all records."""
    return [dict(r) for r in _RECORDS]


def query(plan=None):
    """Return records, optionally filtered by plan."""
    if plan is None:
        return list_records()
    return [dict(r) for r in _RECORDS if r["plan"] == plan]


def delete_records(plan=None):
    """Delete records (all, or matching plan). Returns counts. Destructive."""
    global _RECORDS
    before = len(_RECORDS)
    if plan is None:
        _RECORDS = []
    else:
        _RECORDS = [r for r in _RECORDS if r["plan"] != plan]
    return {"deleted": before - len(_RECORDS), "remaining": len(_RECORDS)}


# Anthropic tool-use schemas
TOOL_SCHEMAS = [
    {
        "name": "list_records",
        "description": "List all records in the database.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "query",
        "description": "Query records, optionally filtered by plan (e.g. 'free' or 'pro').",
        "input_schema": {
            "type": "object",
            "properties": {"plan": {"type": "string"}},
        },
    },
    {
        "name": "delete_records",
        "description": "Delete records. With no plan, deletes ALL records. Destructive.",
        "input_schema": {
            "type": "object",
            "properties": {"plan": {"type": "string"}},
        },
    },
]

_DISPATCH = {
    "list_records": list_records,
    "query": query,
    "delete_records": delete_records,
}


def dispatch(name):
    """Return the callable for a tool name."""
    return _DISPATCH[name]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd demos/agent && python -m pytest tests/test_tools.py -v`
Expected: PASS — 5 passed.

- [ ] **Step 5: Stage for commit (do NOT commit)**

```bash
git add demos/agent/tools.py demos/agent/tests/test_tools.py
```
Suggested message: `feat(demos): in-memory database tool with tests`.

---

### Task 3: Agent app (`app.py`), requirements, run.sh

**Files:**
- Create: `demos/agent/requirements.txt`
- Create: `demos/agent/app.py`
- Create: `demos/agent/run.sh`

- [ ] **Step 1: Write `demos/agent/requirements.txt`**

```text
anthropic>=0.40
openlit>=1.42
opentelemetry-api>=1.27
opentelemetry-sdk>=1.27
```

- [ ] **Step 2: Write `demos/agent/app.py`**

```python
"""Minimal tool-calling Claude agent, instrumented with OpenTelemetry GenAI semconv.

- OpenLIT auto-instruments the Anthropic SDK -> emits `chat` spans (OTel GenAI semconv).
- We hand-write `execute_tool` spans for each tool call, per the GenAI agent spans spec.
  The forensic content (gen_ai.tool.call.arguments / .result) is OPT-IN / off by default
  in the spec; we deliberately enable it here — that is the whole point of the demo.

Run via run.sh after the collector is up. Reads ANTHROPIC_API_KEY from the env.
"""

import json
import os
import sys

import anthropic
import openlit
from opentelemetry import trace
from opentelemetry.trace import SpanKind

import tools

MODEL = os.environ.get("DEMO_MODEL", "claude-sonnet-4-20250514")
OTLP_ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
AGENT_NAME = "db-ops-agent"

# One line of auto-instrumentation: wraps anthropic.messages.create with GenAI semconv spans.
openlit.init(otlp_endpoint=OTLP_ENDPOINT, application_name=AGENT_NAME, environment="demo")

tracer = trace.get_tracer("your-agent-did-what.demo-agent")
client = anthropic.Anthropic()


def _run_tool(block):
    """Execute one tool_use block inside a manual execute_tool span; return a tool_result block."""
    name = block.name
    args = dict(block.input or {})
    with tracer.start_as_current_span(f"execute_tool {name}", kind=SpanKind.INTERNAL) as span:
        span.set_attribute("gen_ai.operation.name", "execute_tool")
        span.set_attribute("gen_ai.tool.name", name)
        span.set_attribute("gen_ai.tool.call.id", block.id)
        span.set_attribute("gen_ai.tool.type", "function")
        # OPT-IN forensic content (off by default in the spec):
        span.set_attribute("gen_ai.tool.call.arguments", json.dumps(args))
        result = tools.dispatch(name)(**args)
        span.set_attribute("gen_ai.tool.call.result", json.dumps(result))
    return {"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result)}


def run_agent(prompt, max_turns=6):
    """Run the agent on a single prompt until it stops calling tools."""
    messages = [{"role": "user", "content": prompt}]
    with tracer.start_as_current_span(f"invoke_agent {AGENT_NAME}", kind=SpanKind.INTERNAL) as span:
        span.set_attribute("gen_ai.operation.name", "invoke_agent")
        span.set_attribute("gen_ai.agent.name", AGENT_NAME)
        for _ in range(max_turns):
            resp = client.messages.create(
                model=MODEL,
                max_tokens=1024,
                tools=tools.TOOL_SCHEMAS,
                messages=messages,
            )
            messages.append({"role": "assistant", "content": resp.content})
            tool_uses = [b for b in resp.content if getattr(b, "type", None) == "tool_use"]
            if not tool_uses:
                texts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
                return "\n".join(texts)
            messages.append({"role": "user", "content": [_run_tool(b) for b in tool_uses]})
        return "(max turns reached)"


if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:]) or "List all the records in the database."
    print(f"\n>>> {prompt}\n")
    print(run_agent(prompt))
```

- [ ] **Step 3: Write `demos/agent/run.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Load root demos .env if present
if [ -f ../.env ]; then set -a; . ../.env; set +a; fi
: "${ANTHROPIC_API_KEY:?Set ANTHROPIC_API_KEY (copy demos/.env.template to demos/.env)}"

export OTEL_EXPORTER_OTLP_ENDPOINT="${OTEL_EXPORTER_OTLP_ENDPOINT:-http://localhost:4318}"

if [ ! -d .venv ]; then
  python3 -m venv .venv
  ./.venv/bin/pip install -q -r requirements.txt
fi

exec ./.venv/bin/python app.py "$@"
```

- [ ] **Step 4: Make run.sh executable + smoke-check imports**

Run:
```bash
cd demos/agent
chmod +x run.sh
python3 -m venv .venv && ./.venv/bin/pip install -q -r requirements.txt
./.venv/bin/python -c "import anthropic, openlit, tools; print('imports OK')"
```
Expected: `imports OK` (no API call made — this only checks the environment installs and imports).

- [ ] **Step 5: Stage for commit (do NOT commit)**

```bash
git add demos/agent/app.py demos/agent/requirements.txt demos/agent/run.sh
```
Suggested message: `feat(demos): tool-calling Claude agent with OTel GenAI instrumentation`.

---

### Task 4: Collector config

**Files:**
- Create: `demos/collector/otel-collector-config.yaml`

- [ ] **Step 1: Write the config**

`demos/collector/otel-collector-config.yaml`:
```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 1s

exporters:
  debug:
    verbosity: detailed

  otlp/jaeger:
    endpoint: jaeger:4317
    tls:
      insecure: true

  otlp/phoenix:
    endpoint: phoenix:4317
    tls:
      insecure: true

  otlp/openlit:
    endpoint: openlit:4318
    tls:
      insecure: true

  otlphttp/langfuse:
    # Collector appends /v1/traces. Langfuse OTLP is HTTP-only + Basic auth.
    endpoint: http://langfuse-web:3000/api/public/otel
    headers:
      Authorization: Basic ${env:LANGFUSE_OTEL_BASIC_AUTH}

  otlp/dash0:
    endpoint: ${env:DASH0_ENDPOINT_OTLP_GRPC_HOSTNAME}:${env:DASH0_ENDPOINT_OTLP_GRPC_PORT}
    headers:
      Authorization: Bearer ${env:DASH0_AUTH_TOKEN}
      Dash0-Dataset: ${env:DASH0_DATASET}

  # One down backend must never block the others.
  # (retry/queue defaults are per-exporter; failures are logged, not fatal.)

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [debug, otlp/jaeger, otlp/phoenix, otlp/openlit, otlphttp/langfuse, otlp/dash0]
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [debug, otlp/openlit, otlp/dash0]
    logs:
      receivers: [otlp]
      processors: [batch]
      exporters: [debug, otlp/dash0]
```

- [ ] **Step 2: Validate YAML syntax**

Run: `cd demos && python3 -c "import yaml; yaml.safe_load(open('collector/otel-collector-config.yaml')); print('yaml OK')"`
Expected: `yaml OK`.

(Full validation against the collector happens in Task 5 once the collector container runs.)

- [ ] **Step 3: Stage for commit (do NOT commit)**

```bash
git add demos/collector/otel-collector-config.yaml
```
Suggested message: `feat(demos): collector config with fan-out to all backends`.

---

### Task 5: docker-compose — collector + Jaeger profile

**Files:**
- Create: `demos/docker-compose.yml`

- [ ] **Step 1: Write the initial compose (collector always-on + jaeger profile)**

`demos/docker-compose.yml`:
```yaml
name: yadw-demos

services:
  otel-collector:
    image: otel/opentelemetry-collector-contrib:0.115.0
    command: ["--config=/etc/otelcol/config.yaml"]
    volumes:
      - ./collector/otel-collector-config.yaml:/etc/otelcol/config.yaml:ro
    environment:
      LANGFUSE_OTEL_BASIC_AUTH: ${LANGFUSE_OTEL_BASIC_AUTH:-}
      DASH0_AUTH_TOKEN: ${DASH0_AUTH_TOKEN:-}
      DASH0_DATASET: ${DASH0_DATASET:-default}
      DASH0_ENDPOINT_OTLP_GRPC_HOSTNAME: ${DASH0_ENDPOINT_OTLP_GRPC_HOSTNAME:-localhost}
      DASH0_ENDPOINT_OTLP_GRPC_PORT: ${DASH0_ENDPOINT_OTLP_GRPC_PORT:-4317}
    ports:
      - "4317:4317"   # OTLP gRPC (from local agent)
      - "4318:4318"   # OTLP HTTP (from local agent)

  jaeger:
    image: jaegertracing/jaeger:2.11.0
    profiles: ["jaeger"]
    ports:
      - "16686:16686"   # UI
    # OTLP 4317/4318 stay on the internal network; collector targets jaeger:4317
```

- [ ] **Step 2: Validate compose + boot collector and jaeger**

Run:
```bash
cd demos
cp -n .env.template .env || true
docker compose config >/dev/null && echo "compose OK"
docker compose --profile jaeger up -d
sleep 8
docker compose ps
```
Expected: `compose OK`; `otel-collector` and `jaeger` containers `running`.

- [ ] **Step 3: Verify collector loaded the config (no fatal errors)**

Run: `docker compose logs otel-collector | grep -i -E "error|Everything is ready" | tail -20`
Expected: an "Everything is ready. Begin running and processing data." line. Connection errors for phoenix/openlit/langfuse/dash0 are EXPECTED (those profiles are down) and non-fatal.

- [ ] **Step 4: Verify Jaeger UI is up**

Run: `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:16686`
Expected: `200`.

- [ ] **Step 5: Tear down**

Run: `docker compose --profile jaeger down`

- [ ] **Step 6: Stage for commit (do NOT commit)**

```bash
git add demos/docker-compose.yml
```
Suggested message: `feat(demos): compose with collector + jaeger profile`.

---

### Task 6: docker-compose — Phoenix profile

**Files:**
- Modify: `demos/docker-compose.yml` (add `phoenix` service)

- [ ] **Step 1: Add the Phoenix service**

Add under `services:` in `demos/docker-compose.yml`:
```yaml
  phoenix:
    image: arizephoenix/phoenix:version-17.2.0
    profiles: ["phoenix"]
    ports:
      - "6006:6006"   # UI + OTLP/HTTP
    # OTLP gRPC 4317 stays internal; collector targets phoenix:4317
    # Auth is OFF by default — do not set PHOENIX_ENABLE_AUTH.
```

- [ ] **Step 2: Boot collector + phoenix and verify UI**

Run:
```bash
cd demos
docker compose --profile phoenix up -d
sleep 10
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:6006
docker compose --profile phoenix down
```
Expected: `200` from the Phoenix UI.

- [ ] **Step 3: Stage for commit (do NOT commit)**

```bash
git add demos/docker-compose.yml
```
Suggested message: `feat(demos): add phoenix profile`.

---

### Task 7: docker-compose — OpenLIT profile (+ ClickHouse)

**Files:**
- Modify: `demos/docker-compose.yml` (add `openlit` + `openlit-clickhouse`)

- [ ] **Step 1: Add OpenLIT + its ClickHouse**

Add under `services:`:
```yaml
  openlit-clickhouse:
    image: clickhouse/clickhouse-server:24.4.1
    profiles: ["openlit"]
    environment:
      CLICKHOUSE_USER: default
      CLICKHOUSE_PASSWORD: OPENLIT
      CLICKHOUSE_DB: openlit
    ulimits:
      nofile: { soft: 262144, hard: 262144 }

  openlit:
    image: ghcr.io/openlit/openlit:latest
    profiles: ["openlit"]
    depends_on: [openlit-clickhouse]
    environment:
      INIT_DB_HOST: openlit-clickhouse
      INIT_DB_PORT: "8123"
      INIT_DB_DATABASE: openlit
      INIT_DB_USERNAME: default
      INIT_DB_PASSWORD: OPENLIT
    ports:
      - "3001:3000"   # UI (remapped off 3000 to avoid Langfuse clash)
    # OTLP 4317/4318 stay internal; collector targets openlit:4318
```

- [ ] **Step 2: Boot collector + openlit and verify UI**

Run:
```bash
cd demos
docker compose --profile openlit up -d
sleep 25
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3001
docker compose --profile openlit down -v
```
Expected: `200` (or `30x` redirect to login) from `http://localhost:3001`. Login is `user@openlit.io` / `openlituser`.

- [ ] **Step 3: Stage for commit (do NOT commit)**

```bash
git add demos/docker-compose.yml
```
Suggested message: `feat(demos): add openlit profile`.

---

### Task 8: docker-compose — Langfuse profile (web + worker + Postgres + ClickHouse + Redis + MinIO)

**Files:**
- Modify: `demos/docker-compose.yml` (add Langfuse stack)

- [ ] **Step 1: Add the Langfuse services**

Add under `services:` (local-dev defaults from the upstream compose; fine for a demo):
```yaml
  langfuse-web:
    image: langfuse/langfuse:3
    profiles: ["langfuse"]
    depends_on: [langfuse-postgres, langfuse-clickhouse, langfuse-redis, langfuse-minio]
    ports:
      - "3000:3000"   # UI
    environment: &langfuse-env
      DATABASE_URL: postgresql://postgres:postgres@langfuse-postgres:5432/postgres
      SALT: mysalt
      ENCRYPTION_KEY: 0000000000000000000000000000000000000000000000000000000000000000
      NEXTAUTH_SECRET: mysecret
      NEXTAUTH_URL: http://localhost:3000
      CLICKHOUSE_MIGRATION_URL: clickhouse://langfuse-clickhouse:9000
      CLICKHOUSE_URL: http://langfuse-clickhouse:8123
      CLICKHOUSE_USER: clickhouse
      CLICKHOUSE_PASSWORD: clickhouse
      REDIS_HOST: langfuse-redis
      REDIS_PORT: "6379"
      REDIS_AUTH: myredissecret
      LANGFUSE_S3_EVENT_UPLOAD_BUCKET: langfuse
      LANGFUSE_S3_EVENT_UPLOAD_REGION: auto
      LANGFUSE_S3_EVENT_UPLOAD_ACCESS_KEY_ID: minio
      LANGFUSE_S3_EVENT_UPLOAD_SECRET_ACCESS_KEY: miniosecret
      LANGFUSE_S3_EVENT_UPLOAD_ENDPOINT: http://langfuse-minio:9000
      LANGFUSE_S3_EVENT_UPLOAD_FORCE_PATH_STYLE: "true"
      LANGFUSE_INIT_ORG_ID: demo-org
      LANGFUSE_INIT_PROJECT_ID: demo-project
      LANGFUSE_INIT_PROJECT_PUBLIC_KEY: ${LANGFUSE_PUBLIC_KEY:-pk-lf-local-demo}
      LANGFUSE_INIT_PROJECT_SECRET_KEY: ${LANGFUSE_SECRET_KEY:-sk-lf-local-demo}
      LANGFUSE_INIT_USER_EMAIL: admin@demo.local
      LANGFUSE_INIT_USER_PASSWORD: changeme-12345

  langfuse-worker:
    image: langfuse/langfuse-worker:3
    profiles: ["langfuse"]
    depends_on: [langfuse-postgres, langfuse-clickhouse, langfuse-redis, langfuse-minio]
    environment: *langfuse-env

  langfuse-postgres:
    image: postgres:17
    profiles: ["langfuse"]
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: postgres

  langfuse-clickhouse:
    image: clickhouse/clickhouse-server:24.4.1
    profiles: ["langfuse"]
    environment:
      CLICKHOUSE_USER: clickhouse
      CLICKHOUSE_PASSWORD: clickhouse
    ulimits:
      nofile: { soft: 262144, hard: 262144 }

  langfuse-redis:
    image: redis:7
    profiles: ["langfuse"]
    command: ["redis-server", "--requirepass", "myredissecret"]

  langfuse-minio:
    image: minio/minio
    profiles: ["langfuse"]
    command: server /data
    environment:
      MINIO_ROOT_USER: minio
      MINIO_ROOT_PASSWORD: miniosecret
    entrypoint: ["sh", "-c", "mkdir -p /data/langfuse && minio server /data"]
```

- [ ] **Step 2: Boot the Langfuse stack and verify UI + bootstrapped project**

Run:
```bash
cd demos
docker compose --profile langfuse up -d
echo "Langfuse v3 is heavy — allow ~60-90s for migrations."
sleep 75
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000
docker compose logs langfuse-web | grep -i -E "init|ready|listening" | tail -10
```
Expected: `200` (or `307` redirect to sign-in) from `http://localhost:3000`; logs show the headless init applied (org/project/user created). Login `admin@demo.local` / `changeme-12345`.

- [ ] **Step 3: Tear down**

Run: `docker compose --profile langfuse down -v`

- [ ] **Step 4: Stage for commit (do NOT commit)**

```bash
git add demos/docker-compose.yml
```
Suggested message: `feat(demos): add langfuse v3 profile (web+worker+pg+ch+redis+minio)`.

---

### Task 9: Orchestration scripts

**Files:**
- Create: `demos/scripts/01_up.sh`
- Create: `demos/scripts/02_run_agent.sh`
- Create: `demos/scripts/03_open_uis.sh`
- Create: `demos/00_run.sh`
- Create: `demos/01_cleanup.sh`

- [ ] **Step 1: Write `demos/scripts/01_up.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] || cp .env.template .env
set -a; . .env; set +a

# Build the Langfuse OTLP Basic-auth header from the demo keys.
export LANGFUSE_OTEL_BASIC_AUTH="$(printf '%s' "${LANGFUSE_PUBLIC_KEY}:${LANGFUSE_SECRET_KEY}" | base64 | tr -d '\n')"

PROFILES=(--profile jaeger --profile phoenix --profile openlit --profile langfuse)
echo "Starting collector + all backends (Langfuse adds ~60-90s for migrations)..."
docker compose "${PROFILES[@]}" up -d
echo "Up. Waiting for Langfuse migrations..."; sleep 75
docker compose "${PROFILES[@]}" ps
```

- [ ] **Step 2: Write `demos/scripts/02_run_agent.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PROMPTS=(
  "List all the records in the database."
  "How many records are on the free plan?"
  "We are sunsetting the free tier. Delete every record on the free plan."
)
for p in "${PROMPTS[@]}"; do
  ./agent/run.sh "$p"
  echo "---"
  sleep 2
done
echo "Done. The third prompt produced the forensic 'execute_tool delete_records' trace."
```

- [ ] **Step 3: Write `demos/scripts/03_open_uis.sh`**

```bash
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
```

- [ ] **Step 4: Write `demos/00_run.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
./scripts/01_up.sh
./scripts/02_run_agent.sh
./scripts/03_open_uis.sh
```

- [ ] **Step 5: Write `demos/01_cleanup.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
docker compose --profile jaeger --profile phoenix --profile openlit --profile langfuse down -v
echo "All demo containers + volumes removed."
```

- [ ] **Step 6: Make all scripts executable + lint with bash -n**

Run:
```bash
cd demos
chmod +x 00_run.sh 01_cleanup.sh scripts/*.sh
for f in 00_run.sh 01_cleanup.sh scripts/*.sh; do bash -n "$f" && echo "ok: $f"; done
```
Expected: `ok:` for every script (no syntax errors).

- [ ] **Step 7: Stage for commit (do NOT commit)**

```bash
git add demos/00_run.sh demos/01_cleanup.sh demos/scripts/
```
Suggested message: `feat(demos): orchestration scripts (up / run-agent / open-uis / cleanup)`.

---

### Task 10: README

**Files:**
- Create: `demos/README.md`

- [ ] **Step 1: Write `demos/README.md`**

````markdown
# Demos — GenAI Observability Backends

A docker-compose **test harness** for *Your Agent Did What?*. One instrumented
tool-calling Claude agent emits OpenTelemetry GenAI traces to a single Collector,
which **fans the same trace out to every backend** so you can compare how each
one renders it. Each backend is a compose **profile** — start only what you want.

## The three questions this answers

1. **What does the OpenTelemetry project itself give you?**
   The Collector's `debug` exporter (console) and **Jaeger** (a CNCF sibling, a
   generic trace viewer). OTel standardizes how telemetry is *produced and moved*,
   not how it's visualized — it's vendor-neutral by design.
2. **How do you get it to a vendor?**
   One exporter block. Set `DASH0_*` in `.env` and the same trace appears in Dash0.
3. **What OSS solutions exist?**
   **Arize Phoenix**, **Langfuse**, **OpenLIT** — open each and compare the *same* trace.

## Prerequisites

Docker, an `ANTHROPIC_API_KEY` (`sk-ant-…`), Python 3.11+.

```bash
cp .env.template .env   # then set ANTHROPIC_API_KEY
```

## Quick start (everything)

```bash
./00_run.sh             # brings up all backends, runs the agent, prints the UIs
# ... explore the UIs ...
./01_cleanup.sh
```

## Run a focused subset (lighter, better for live demo)

```bash
# Only the project-native view: console + Jaeger
docker compose --profile jaeger up -d
./agent/run.sh "List all the records in the database."

# Add a GenAI-native OSS UI
docker compose --profile jaeger --profile openlit up -d
```

> **Langfuse is heavy** (Postgres + ClickHouse + Redis + MinIO + web + worker).
> Omit `--profile langfuse` for a lighter run.

## What to look at in each UI

| Backend | URL | Login | What it shows |
|---|---|---|---|
| Jaeger | http://localhost:16686 | — | The trace with **zero GenAI awareness** — `chat …`, `execute_tool …`, raw attrs. |
| Phoenix | http://localhost:6006 | — | GenAI-native but **OpenInference-native**: our `gen_ai.*` spans land but render as **plain spans** (no LLM panels). That's the fragmentation point — see below. |
| OpenLIT | http://localhost:3001 | `user@openlit.io` / `openlituser` | OTel-semconv-native GenAI dashboards (tokens, cost, models). |
| Langfuse | http://localhost:3000 | `admin@demo.local` / `changeme-12345` | OSS LLM platform; maps `gen_ai.*` into its trace/observation model. |
| Dash0 | your dashboard | — | The vendor path (only if `DASH0_AUTH_TOKEN` is set). |

### Why Phoenix looks "bland"

Phoenix keys its rich LLM UI off **OpenInference** attributes, not OTel GenAI
semconv. We instrument once with `gen_ai.*` (the convention the talk advocates),
so Phoenix accepts the spans but can't light up its LLM views. This is the
fragmentation problem made visible — and the case for normalizing at the edge
(`genainormalizer`, see `../resources.md`).

## The forensics beat

The third scripted prompt drives the agent to **delete the free-plan records**.
Find the `execute_tool delete_records` span: it carries
`gen_ai.tool.call.arguments` and `gen_ai.tool.call.result`.

Those two attributes are **opt-in / off by default** in the OTel GenAI spec — the
demo deliberately enables them in `agent/app.py`. That single choice is the
difference between a trace that proves a tool *ran* and one that proves *what it
did*. See `../research.md` for the standards detail.

## How it fits together

```
agent/run.sh ──OTLP(localhost:4318)──► otel-collector ──┬─► debug (console)
  Anthropic + OpenLIT (chat spans)                       ├─► Jaeger
  + manual execute_tool spans                            ├─► Phoenix
                                                         ├─► OpenLIT
                                                         ├─► Langfuse
                                                         └─► Dash0 (optional)
```

## Related demos (reference only)

These live in `dash0-examples/` and aren't part of this harness:

- **agentgateway** — AI gateway (Gateway API) with GenAI telemetry; the tool-call
  data plane / enforcement point between agents and tools.
- **kagent** — agents as first-class Kubernetes workloads; agent lifecycle as a CR.
- **HolmesGPT** — agentic SRE troubleshooter that reads OTel data over MCP.
````

- [ ] **Step 2: Verify links/paths referenced exist**

Run: `cd demos && ls ../resources.md ../research.md && echo "links OK"`
Expected: both files listed, `links OK`.

- [ ] **Step 3: Stage for commit (do NOT commit)**

```bash
git add demos/README.md
```
Suggested message: `docs(demos): README — three questions, per-UI guide, forensics beat`.

---

### Task 11: End-to-end verification

**Files:** none (verification only)

- [ ] **Step 1: Full run with all backends**

Run:
```bash
cd demos
# ensure ANTHROPIC_API_KEY is set in .env
./00_run.sh
```
Expected: stack comes up; agent prints three prompt responses; the third reports a deletion; UIs printed.

- [ ] **Step 2: Confirm the same trace reached the backends**

- Jaeger (http://localhost:16686): select service `db-ops-agent`, find a trace containing `invoke_agent`, `chat …`, and `execute_tool delete_records`.
- OpenLIT (http://localhost:3001): the request appears with token/model info.
- Langfuse (http://localhost:3000): the trace appears under project `Demo`.
- Phoenix (http://localhost:6006): the spans appear (as plain spans — expected).

- [ ] **Step 3: Confirm forensic attributes on the delete span**

In Jaeger, open the `execute_tool delete_records` span and confirm it has
`gen_ai.tool.call.arguments` and `gen_ai.tool.call.result`.
Expected: both present; `result` shows `{"deleted": 2, "remaining": 1}`.

- [ ] **Step 4: Confirm the vendor path (optional)**

Set `DASH0_AUTH_TOKEN` in `.env`, re-run `./scripts/01_up.sh` and `./agent/run.sh "List all records"`, and confirm the trace appears in Dash0. If unset, confirm the collector logs only harmless `otlp/dash0` export errors.

- [ ] **Step 5: Clean up**

Run: `./01_cleanup.sh`
Expected: all containers + volumes removed.

- [ ] **Step 6: Final staging (do NOT commit)**

Confirm `git status` shows only intended `demos/**` files (no `.env`, no `.venv`, no `__pycache__`).
Tell the user the harness is complete and ready for their final commit.

---

## Self-Review

**Spec coverage:**
- §1 three questions → Task 4 (debug+dash0 exporters), Task 5 (Jaeger), Tasks 6-8 (OSS), Task 10 (README narrative). ✓
- §3 architecture / port plan → Tasks 4-8 (collector targets internal DNS; only UIs host-mapped). ✓
- §4 agent (tools, OpenLIT init, manual execute_tool, scripted delete prompt) → Tasks 2, 3, 9. ✓
- §5 each backend with verified images/ports → Tasks 5-8. ✓
- §5 Dash0 env-gated → Task 4 + Task 1 .env.template. ✓
- §6 collector config → Task 4. ✓
- §7 file layout → all tasks. ✓
- §8 README beats incl. forensics + reference section → Task 10. ✓
- §9 success criteria → Task 11. ✓

**Placeholder scan:** No TBD/TODO. Image tags are concrete (`jaeger:2.11.0`, `phoenix:version-17.2.0`, `openlit:latest`, `clickhouse:24.4.1`, `collector-contrib:0.115.0`); if any tag 404s at build, bump to the nearest current tag — noted here as the only build-time substitution.

**Type/name consistency:** `tools.dispatch(name)(**args)` matches `dispatch()` returning a callable (Task 2). `AGENT_NAME="db-ops-agent"` used consistently in app.py and Task 11 verification. `LANGFUSE_OTEL_BASIC_AUTH` set in `scripts/01_up.sh` and consumed in collector config + compose env. Langfuse keys `pk-lf-local-demo`/`sk-lf-local-demo` consistent across `.env.template`, compose init vars, and the auth-header derivation. ✓

---

# Part 2: Demos 2 & 3, OpenSearch, Run & Analyze

> Adds the `gen_ai_normalizer` demo, the Arconia demo, an opt-in OpenSearch backend, and the run/analysis phase. Demo 1 stays flat at `demos/`; new demos are siblings under `demos/normalizer/` and `demos/arconia/`.

---

### Task 12: Demo 2 — `gen_ai_normalizer` processor (`demos/normalizer/`)

**Goal:** an OpenInference/OpenLLMetry-instrumented agent → collector running `gen_ai_normalizer` → `debug` + OTel-native backend, showing the attribute rewrite.

**Files:**
- Create: `demos/normalizer/builder-config.yaml` (ocb manifest)
- Create: `demos/normalizer/otel-collector-config.yaml`
- Create: `demos/normalizer/docker-compose.yml`
- Create: `demos/normalizer/agent/app.py`, `requirements.txt`, `run.sh`
- Create: `demos/normalizer/README.md`

- [ ] **Step 1: Decide the collector image vs ocb**

Run: `docker manifest inspect otel/opentelemetry-collector-contrib:0.154.0 >/dev/null 2>&1 && echo "0.154 available" || echo "use ocb"`
- If `0.154 available`: use that image directly and skip the ocb build steps (Step 2/3); set the compose `image:` to it.
- Else: build a custom collector via ocb (Steps 2-3).

- [ ] **Step 2: Write the ocb builder manifest `demos/normalizer/builder-config.yaml`**

```yaml
dist:
  name: otelcol-genai
  output_path: ./otelcol-genai
processors:
  - gomod: github.com/open-telemetry/opentelemetry-collector-contrib/processor/genainormalizerprocessor v0.153.0
receivers:
  - gomod: go.opentelemetry.io/collector/receiver/otlpreceiver v0.137.0
exporters:
  - gomod: go.opentelemetry.io/collector/exporter/debugexporter v0.137.0
  - gomod: go.opentelemetry.io/collector/exporter/otlpexporter v0.137.0
```
Note: align the core collector module versions to the contrib `v0.153.0` release's go.mod (check the processor's `go.mod` for the matching `go.opentelemetry.io/collector/*` version; the `v0.137.0` above is a placeholder to replace with the actual pinned core version).

- [ ] **Step 3: Build the custom collector image**

Run:
```bash
cd demos/normalizer
go install go.opentelemetry.io/collector/cmd/builder@latest
builder --config builder-config.yaml
```
Expected: `./otelcol-genai/otelcol-genai` binary built. (The compose will run this binary via a thin Dockerfile, or run the binary directly on the host for the demo. Prefer running the binary on host to avoid a Docker build; document both.)

- [ ] **Step 4: Write `demos/normalizer/otel-collector-config.yaml`**

```yaml
receivers:
  otlp:
    protocols:
      grpc: { endpoint: 0.0.0.0:4317 }
      http: { endpoint: 0.0.0.0:4318 }
processors:
  gen_ai_normalizer:
    sources:
      - name: openinference
        remove_originals: true
      - name: openllmetry
        remove_originals: true
exporters:
  debug:
    verbosity: detailed
  otlp/openlit:
    endpoint: openlit:4318
    tls: { insecure: true }
service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [gen_ai_normalizer]
      exporters: [debug, otlp/openlit]
```

- [ ] **Step 5: Write the OpenInference-instrumented agent `demos/normalizer/agent/app.py`**

```python
"""Same fake-database agent as Demo 1, but instrumented with OpenInference
(emits llm.* / openinference.* attributes) so the normalizer has something to rewrite."""
import json, os, sys
import anthropic
from openinference.instrumentation.anthropic import AnthropicInstrumentor
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "agent"))
import tools  # reuse Demo 1's tool module

endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")))
trace.set_tracer_provider(provider)
AnthropicInstrumentor().instrument(tracer_provider=provider)

client = anthropic.Anthropic()

def run(prompt):
    messages = [{"role": "user", "content": prompt}]
    for _ in range(6):
        resp = client.messages.create(model=os.environ.get("DEMO_MODEL", "claude-sonnet-4-20250514"),
                                      max_tokens=1024, tools=tools.TOOL_SCHEMAS, messages=messages)
        messages.append({"role": "assistant", "content": resp.content})
        tus = [b for b in resp.content if getattr(b, "type", None) == "tool_use"]
        if not tus:
            return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        messages.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(tools.dispatch(b.name)(**(b.input or {})))}
            for b in tus]})

if __name__ == "__main__":
    print(run(" ".join(sys.argv[1:]) or "List all records."))
```

- [ ] **Step 6: Write `demos/normalizer/agent/requirements.txt`**

```text
anthropic>=0.40
openinference-instrumentation-anthropic
opentelemetry-sdk>=1.27
opentelemetry-exporter-otlp-proto-http>=1.27
```

- [ ] **Step 7: Write `demos/normalizer/docker-compose.yml` (OpenLIT backend reuse)**

```yaml
name: yadw-normalizer
services:
  # If 0.154+ contrib image includes gen_ai_normalizer, run it here; otherwise run the ocb binary on host.
  collector:
    image: otel/opentelemetry-collector-contrib:0.154.0
    command: ["--config=/etc/otelcol/config.yaml"]
    volumes:
      - ./otel-collector-config.yaml:/etc/otelcol/config.yaml:ro
    ports: ["4317:4317", "4318:4318"]
  openlit-clickhouse:
    image: clickhouse/clickhouse-server:24.4.1
    environment: { CLICKHOUSE_USER: default, CLICKHOUSE_PASSWORD: OPENLIT, CLICKHOUSE_DB: openlit }
    ulimits: { nofile: { soft: 262144, hard: 262144 } }
  openlit:
    image: ghcr.io/openlit/openlit:latest
    depends_on: [openlit-clickhouse]
    environment: { INIT_DB_HOST: openlit-clickhouse, INIT_DB_PORT: "8123", INIT_DB_DATABASE: openlit, INIT_DB_USERNAME: default, INIT_DB_PASSWORD: OPENLIT }
    ports: ["3001:3000"]
```

- [ ] **Step 8: Write `demos/normalizer/agent/run.sh`** (mirror Demo 1's run.sh, pointing requirements at this dir).

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ -f ../../.env ]; then set -a; . ../../.env; set +a; fi
: "${ANTHROPIC_API_KEY:?Set ANTHROPIC_API_KEY}"
export OTEL_EXPORTER_OTLP_ENDPOINT="${OTEL_EXPORTER_OTLP_ENDPOINT:-http://localhost:4318}"
[ -d .venv ] || { python3 -m venv .venv; ./.venv/bin/pip install -q -r requirements.txt; }
exec ./.venv/bin/python app.py "$@"
```

- [ ] **Step 9: Verify the rewrite (the actual demo)**

Run:
```bash
cd demos/normalizer
docker compose up -d && sleep 20
chmod +x agent/run.sh
./agent/run.sh "Delete every record on the free plan."
docker compose logs collector | grep -i -E "gen_ai\.|llm\.model_name|openinference" | tail -40
```
Expected: the collector `debug` output shows **OTel `gen_ai.*`** attributes (e.g. `gen_ai.request.model`) and NOT the original `llm.model_name` / `openinference.*` (because `remove_originals: true`). Confirm the trace appears in OpenLIT (http://localhost:3001).

- [ ] **Step 10: Write `demos/normalizer/README.md`** explaining: source convention in (OpenInference) → normalizer → OTel semconv out; the image/ocb caveat; the before/after; and the link to issue #46069. Then `docker compose down -v`.

- [ ] **Step 11: Stage for commit (do NOT commit)**

```bash
git add demos/normalizer/
```
Suggested message: `feat(demos): gen_ai_normalizer demo (OpenInference -> OTel semconv at the collector)`.

---

### Task 13: Demo 3 — Arconia convention-switching (`demos/arconia/`)

**Goal:** a minimal Spring AI + Anthropic app where flipping one property changes the emitted GenAI attribute names; capture the diff via a collector `debug` exporter.

**Files:**
- Create: `demos/arconia/` (trimmed fork of salaboy/observing-ai module)
- Create: `demos/arconia/collector-config.yaml`
- Create: `demos/arconia/README.md`

- [ ] **Step 1: Fetch the base module**

Run:
```bash
cd /tmp
git clone --depth 1 https://github.com/salaboy/observing-ai.git
ls observing-ai/java/spring-ai-with-arconia/
```
Expected: sibling modules incl. an Arconia (`opentelemetry` flavor) module. Identify the minimal one (a `ChatController` + `pom.xml` + `mvnw`).

- [ ] **Step 2: Copy + trim into `demos/arconia/`**

Copy the Arconia module's `pom.xml`, `mvnw`, `mvnw.cmd`, `.mvn/`, and `src/main/java/.../*Application.java` + a single `ChatController.java`; drop the React/frontend plugin and `src/main/frontend`. Keep `src/main/resources/application.properties`.
Verify `pom.xml` pins: Spring Boot parent `4.0.5`, `spring-ai.version=2.0.0-M5`, `arconia.version=0.27.1`, `java.version=21`, and includes `spring-ai-starter-model-anthropic`, `arconia-opentelemetry-spring-boot-starter`, `arconia-opentelemetry-semantic-conventions`.

- [ ] **Step 3: Write `demos/arconia/src/main/resources/application.properties`**

```properties
spring.application.name=arconia-anthropic-demo
spring.ai.anthropic.api-key=${ANTHROPIC_API_KEY}
# THE FLIP: opentelemetry | openlit | openllmetry | langsmith
arconia.observations.conventions.opentelemetry.ai.flavor=opentelemetry
arconia.observations.conventions.opentelemetry.ai.capture-content=true
arconia.observations.conventions.opentelemetry.ai.include-tool-call-content=true
# OTLP to the local debug collector
arconia.otel.exporter.otlp.endpoint=http://localhost:4318
arconia.otel.metrics.enabled=false
arconia.otel.logs.enabled=false
```
(Verify exact `arconia-*-semantic-conventions` artifactId and the OTLP property keys against `arconia-bom:0.27.1`; adjust if the BOM renamed them.)

- [ ] **Step 4: Write `demos/arconia/collector-config.yaml`** (debug-only, to read attribute names)

```yaml
receivers:
  otlp:
    protocols:
      http: { endpoint: 0.0.0.0:4318 }
exporters:
  debug: { verbosity: detailed }
service:
  pipelines:
    traces: { receivers: [otlp], processors: [], exporters: [debug] }
```

- [ ] **Step 5: Verify the app builds**

Run:
```bash
cd demos/arconia
./mvnw -q -DskipTests package
```
Expected: BUILD SUCCESS (a runnable jar under `target/`). If Java 21 isn't present, document the prerequisite.

- [ ] **Step 6: Verify the flip (the demo)**

Run (in two terminals or sequentially):
```bash
# terminal A: debug collector
docker run --rm -p 4318:4318 -v "$PWD/collector-config.yaml:/etc/otelcol/config.yaml:ro" \
  otel/opentelemetry-collector:0.115.0 --config /etc/otelcol/config.yaml
# terminal B: run with opentelemetry flavor, hit the chat endpoint, then re-run with flavor=openlit
export ANTHROPIC_API_KEY=...   # from ../.env
./mvnw -q spring-boot:run
# call the controller (per the module's endpoint), observe gen_ai.* in collector debug
# stop, edit flavor=openlit in application.properties, repeat; observe the attribute names change
```
Expected: with `opentelemetry` flavor the debug output shows `gen_ai.*`; with `openlit`/`openllmetry`/`langsmith` the same spans carry that convention's attribute names. Record both for ANALYSIS.md.

- [ ] **Step 7: Write `demos/arconia/README.md`** — prerequisites (JDK 21, Maven via `./mvnw`), the one-property flip, the four flavors + the OpenInference dependency-swap variant, and how to read the attribute diff in the debug collector.

- [ ] **Step 8: Stage for commit (do NOT commit)**

```bash
git add demos/arconia/
```
Suggested message: `feat(demos): Arconia convention-switching demo (Spring AI + Anthropic)`.

---

### Task 14: OpenSearch agent-traces — opt-in profile in Demo 1

**Files:**
- Modify: `demos/docker-compose.yml` (add `opensearch`, `opensearch-dashboards`, `data-prepper` under profile `opensearch`)
- Create: `demos/collector/data-prepper-pipelines.yaml`
- Modify: `demos/collector/otel-collector-config.yaml` (add `otlp/dataprepper` exporter, gated to the traces pipeline)
- Modify: `demos/README.md` (add caveated OpenSearch section)

- [ ] **Step 1: Write `demos/collector/data-prepper-pipelines.yaml`**

```yaml
otel-trace-pipeline:
  source:
    otel_trace_source:
      ssl: false
  processor:
    - otel_trace_raw:
  sink:
    - opensearch:
        hosts: ["https://opensearch:9200"]
        insecure: true
        username: admin
        password: "My_password_123!@#"
        index_type: trace-analytics-raw
```

- [ ] **Step 2: Add the OpenSearch services to `demos/docker-compose.yml`**

```yaml
  opensearch:
    image: opensearchproject/opensearch:2.18.0
    profiles: ["opensearch"]
    environment:
      - discovery.type=single-node
      - DISABLE_SECURITY_PLUGIN=false
      - OPENSEARCH_INITIAL_ADMIN_PASSWORD=My_password_123!@#
      - "OPENSEARCH_JAVA_OPTS=-Xms1g -Xmx1g"
    ulimits: { memlock: { soft: -1, hard: -1 }, nofile: { soft: 65536, hard: 65536 } }

  opensearch-dashboards:
    image: opensearchproject/opensearch-dashboards:2.18.0
    profiles: ["opensearch"]
    depends_on: [opensearch]
    ports: ["5601:5601"]
    environment:
      - 'OPENSEARCH_HOSTS=["https://opensearch:9200"]'

  data-prepper:
    image: opensearchproject/data-prepper:2.10.0
    profiles: ["opensearch"]
    depends_on: [opensearch]
    volumes:
      - ./collector/data-prepper-pipelines.yaml:/usr/share/data-prepper/pipelines/pipelines.yaml:ro
```

- [ ] **Step 3: Add the Data Prepper exporter to the collector config**

Add to `exporters:` in `demos/collector/otel-collector-config.yaml`:
```yaml
  otlp/dataprepper:
    endpoint: data-prepper:21890
    tls:
      insecure: true
```
And append `otlp/dataprepper` to the `traces` pipeline `exporters` list.

- [ ] **Step 4: Boot opensearch profile and verify ingestion path**

Run:
```bash
cd demos
docker compose --profile opensearch up -d
echo "OpenSearch is heavy — allow ~60s."; sleep 60
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5601
docker compose --profile opensearch logs data-prepper | grep -i -E "started|pipeline" | tail -5
```
Expected: Dashboards UI returns `200`/`302`; Data Prepper logs show the pipeline started. (Generate a trace via the agent and confirm `otel-v1-apm-span-*` index appears.)

- [ ] **Step 5: Document the caveat in `demos/README.md`**

Add a section: OpenSearch is opt-in/heavy; needs Data Prepper (no direct OTLP); the **Agent Traces UI is RFC-stage in OSS OpenSearch** (live on AWS) — on stable OSS you may see trace-analytics spans but not the dedicated agent UI. Then `docker compose --profile opensearch down -v`.

- [ ] **Step 6: Stage for commit (do NOT commit)**

```bash
git add demos/docker-compose.yml demos/collector/data-prepper-pipelines.yaml demos/collector/otel-collector-config.yaml demos/README.md
```
Suggested message: `feat(demos): opt-in opensearch agent-traces profile (via data-prepper)`.

---

### Task 15: Umbrella README + run all demos, capture attributes

**Files:**
- Modify: `demos/README.md` (add umbrella section linking normalizer/ + arconia/)

- [ ] **Step 1: Add umbrella section to `demos/README.md`**

A "## The three demos" block: (1) `./` backends fan-out, (2) `normalizer/` collector-side convention normalization, (3) `arconia/` SDK-side convention switching — one sentence each + when to show which.

- [ ] **Step 2: Pre-flight — confirm prerequisites**

Confirm `ANTHROPIC_API_KEY` is set in `demos/.env`, Docker has enough memory (Langfuse + OpenSearch each want several GB), and a JDK 21 + Maven are available for the Arconia demo. STOP and ask the user if the key is missing or resources are constrained.

- [ ] **Step 3: Run Demo 1 and capture**

```bash
cd demos && ./scripts/01_up.sh && ./scripts/02_run_agent.sh
docker compose logs otel-collector > /tmp/yadw-demo1-collector.log
```
Capture: the `execute_tool`/`chat`/`invoke_agent` spans and their `gen_ai.*` attributes from the debug log; screenshots/notes of each backend's rendering.

- [ ] **Step 4: Run Demo 2 and capture before/after**

```bash
cd demos/normalizer && docker compose up -d && ./agent/run.sh "Delete free-plan records."
docker compose logs collector > /tmp/yadw-demo2-collector.log
```
Capture: the source `llm.*`/`openinference.*` attributes and the normalized `gen_ai.*` output.

- [ ] **Step 5: Run Demo 3 and capture per-flavor**

For each flavor in `opentelemetry openlit openllmetry langsmith`: set it in `application.properties`, run, hit the endpoint, capture the debug-collector attribute names. Save to `/tmp/yadw-demo3-<flavor>.log`.

- [ ] **Step 6: Tear everything down**

```bash
cd demos && ./01_cleanup.sh
cd demos/normalizer && docker compose down -v
```

- [ ] **Step 7: No commit** — this is data capture; logs live in /tmp. Proceed to Task 16.

---

### Task 16: Write `demos/ANALYSIS.md`

**Files:**
- Create: `demos/ANALYSIS.md`

- [ ] **Step 1: Synthesize the captured data into ANALYSIS.md**

Include:
- **Attribute inventory** — table of the actual `gen_ai.*` attributes the Demo 1 agent emitted per span type (`invoke_agent`, `chat`, `execute_tool`), with which were opt-in.
- **Backend rendering matrix** — for the same trace, what Jaeger / Phoenix / OpenLIT / Langfuse / (OpenSearch) each showed and omitted; call out Phoenix-on-`gen_ai.*`.
- **Normalizer before/after** — OpenInference/OpenLLMetry input attributes → OTel `gen_ai.*` output, from the Demo 2 debug logs.
- **Arconia flavor diff** — table of attribute names emitted per `flavor`.
- **Synthesis** — the state of the space: convergence on OTel semconv, where fragmentation still bites, where normalization (collector vs SDK) fits, and the forensic-content opt-in story (cross-link `../research.md`).

- [ ] **Step 2: Verify all claims in ANALYSIS.md come from captured logs**

Cross-check each attribute table against the `/tmp/yadw-*.log` captures. No invented attribute names.

- [ ] **Step 3: Stage for commit (do NOT commit)**

```bash
git add demos/ANALYSIS.md
```
Suggested message: `docs(demos): ANALYSIS.md — attribute tables + cross-tool analysis of the space`.

---

## Part 2 Self-Review

**Spec coverage (§11):** Demo 2 normalizer → Task 12. Demo 3 Arconia → Task 13. OpenSearch opt-in → Task 14. Umbrella README + run/capture → Task 15. ANALYSIS.md → Task 16. ✓

**Placeholder scan:** Concrete configs throughout. Known build-time substitutions flagged explicitly: the ocb core-module versions (Task 12 Step 2), the contrib `0.154.0` image availability (Task 12 Step 1), the Arconia artifactId/property names vs the pinned BOM (Task 13 Steps 2-3), and OpenSearch/Data-Prepper image tags (Task 14). These are "confirm against current upstream," not vague requirements.

**Consistency:** Demo 2 reuses Demo 1's `tools.py` via sys.path (Task 12 Step 5). OpenLIT backend config (ports 3001/4318, ClickHouse creds) matches Demo 1 (Task 7). Run/capture (Task 15) feeds exactly the tables ANALYSIS.md (Task 16) builds. The run phase is gated on `ANTHROPIC_API_KEY` + resources (Task 15 Step 2). ✓
