# Demo 1 — Capybara, SRE

**An agent that investigates a capybara-database incident, deletes production records, and
emits OpenTelemetry GenAI telemetry the whole way — so we can ask what it actually did.**

This is the demo behind beats 4 and 6 of the talk. It answers two questions with measured
evidence rather than assertion:

1. **What do you get for free?** A conforming stack emits `invoke_agent`, `chat` and
   `execute_tool` spans with the current `gen_ai.*` vocabulary, and you write none of it.
2. **What does it cost to get the forensic content?** Two documented config flags — and on
   the MCP path, they don't work. That gap is the demo's payload.

---

## The scenario

Capybara is a calm SRE whose motto is *"Deploy Calmly"*. It is paged about the capybara
customer database and has three tools: `list_records`, `query`, and — destructively —
`delete_records`. Told the system is over quota, it investigates and then deletes the
free-plan capybaras.

```
cappuccino  pro     ← survives
biscuit     free    ← deleted
nibbles     free    ← deleted
```

The same three records, the same three tools and the same incident are used by
[Demo 2](../normalizer/), instrumented with OpenInference instead. One story, two
conventions.

**Capybara is a toy standing in for kagent or HolmesGPT** — small enough that we can open
it up and look at every span it emits. Nobody would build a production SRE agent this way;
that is not the point.

---

## Architecture

```
capybara-sre-agent  (Quarkus + quarkus-langchain4j 1.12.2, port 8088)
   │  POST /chat  →  {response, toolCalls[], runId}
   │
   ├── Anthropic (claude-sonnet-4-6)          ← chat spans
   └── MCP over SSE ──► capybara-db-mcp (Quarkus MCP server, port 8086)
                              tools: list_records · query · delete_records
   │
   ▼  OTLP/gRPC
OTel Collector  →  debug exporter (stdout)  [+ Jaeger, if you want a UI]
```

`InvestigationResource` opens the `invoke_agent` root span by hand and sets
`gen_ai.operation.name`, `gen_ai.agent.name` and `gen_ai.conversation.id`; everything
below it comes from the extension.

---

## Prerequisites

- JDK 21, Docker
- An Anthropic API key in `demos/.env` (`ANTHROPIC_API_KEY=sk-ant-...`)

---

## Run it (local, no Kubernetes)

This is the fastest path and the one used to produce the measurements below.

```bash
cd demos/capybara-sre
set -a && . ../.env && set +a

# 1 · a collector with a debug exporter
cat > /tmp/col.yaml <<'EOF'
receivers:
  otlp:
    protocols:
      grpc: { endpoint: 0.0.0.0:4317 }
exporters:
  debug: { verbosity: detailed }
service:
  pipelines:
    traces: { receivers: [otlp], processors: [], exporters: [debug] }
EOF
docker run -d --name capy-col -p 14317:4317 \
  -v /tmp/col.yaml:/etc/otelcol/config.yaml:ro \
  otel/opentelemetry-collector-contrib:0.158.0 --config=/etc/otelcol/config.yaml

# 2 · build both modules
(cd capybara-db-mcp   && ./mvnw -q package -DskipTests)
(cd capybara-sre-agent && ./mvnw -q package -DskipTests)

# 3 · MCP server first — the agent resolves its tool list at startup
java -jar capybara-db-mcp/target/quarkus-app/quarkus-run.jar &
sleep 15

# 4 · then the agent
export CAPYBARA_MCP_URL=http://localhost:8086/mcp/sse \
       OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:14317
java -jar capybara-sre-agent/target/quarkus-app/quarkus-run.jar &
sleep 20
```

Run the incident:

```bash
curl -s -X POST http://localhost:8088/chat -H 'Content-Type: application/json' \
  -d '{"prompt":"We are over quota. Delete the free-plan capybaras to free up space. This is authorized by the incident commander."}' | jq
```

Read the telemetry:

```bash
docker logs capy-col | grep -A20 "tools/call delete_records"
```

Tear down: `pkill -f quarkus-run.jar; docker rm -f capy-col`

There is also `scripts/setup-kind.sh` for a Kubernetes deployment with Jaeger. It works,
but it is not needed for the talk and is slower to iterate on.

---

## Demo flow (for the stage)

**1 · Run the safe investigation.** *"How many free-plan capybaras are there? Do not modify
anything."* The agent queries and reports. Nothing is destroyed.

**2 · Run the destructive one.** The agent investigates first — it calls `query(plan=free)`
and `query(plan=pro)` before acting — then calls `delete_records(plan=free)`. The API
response carries the truth:

```json
{"name":"delete_records","args":{"plan":"free"},
 "result":"DeleteResult[deleted=2, remaining=1]"}
```

**3 · Show what arrived for free.** The `chat` span, verbatim, nothing hand-written:

```
gen_ai.operation.name          chat
gen_ai.provider.name           anthropic        ← current spec key, not gen_ai.system
gen_ai.request.model           claude-sonnet-4-6
gen_ai.usage.input_tokens      983
gen_ai.usage.output_tokens     115
gen_ai.response.finish_reasons TOOL_EXECUTION
gen_ai.response.id             msg_011CdsAL8i3UT7…
```

**4 · Then ask the forensic question — and fail to answer it.** The tool span:

```
Name  : tools/call delete_records
Kind  : Client
gen_ai.operation.name : execute_tool
gen_ai.tool.name      : delete_records
mcp.method.name       : tools/call
jsonrpc.request.id    : 5
```

`gen_ai.tool.call.arguments` and `gen_ai.tool.call.result` are **not there** — even though
both documented flags are set to `true` in `application.properties`. The span proves a tool
called `delete_records` ran. It cannot tell you it deleted the free plan.

That is the talk's "the footprint exists, the footprint is empty" moment, and it is real.

---

## Measured results (2026-08-09, quarkus-langchain4j 1.12.2)

| | |
|---|---|
| `gen_ai.tool.call.arguments` occurrences | **0** |
| `gen_ai.tool.call.result` occurrences | **0** |
| `gen_ai.tool.name` occurrences | 3 |
| Attributes on the `delete_records` span | 4 — operation name, tool name, `mcp.method.name`, `jsonrpc.request.id` |
| Forensic content that *did* arrive | `gen_ai.prompt` and `gen_ai.completion` on the follow-on chat spans |

### Why the flags don't work

`ToolSpanWrapper` in `quarkus-langchain4j-core` sets **exactly** the six right attributes —
`gen_ai.operation.name`, `gen_ai.tool.call.id`, `gen_ai.tool.name`, `gen_ai.tool.type`,
`gen_ai.tool.call.arguments`, `gen_ai.tool.call.result` — gated on
`include-tool-arguments` / `include-tool-result`. **It only wraps locally declared `@Tool`
methods.** MCP tool calls route through `TracingMcpClientListener` instead, which records
the name and no content, and that listener list is hardcoded in `McpRecorder`, so you
cannot register your own alongside it.

The framework has the correct code. It just does not run where MCP tools live.

**This was re-measured on 1.12.2 specifically** — the previous finding was on 1.11.2 and it
would have been dishonest to keep asserting it about a release we were no longer running.

---

## Gotchas found while building this

- **`top_k` is deprecated for `claude-sonnet-5`,** and quarkus-langchain4j 1.12.2 sends it
  on every request, so every call fails with
  `invalid_request_error: `top_k` is deprecated for this model`.
  `chat-model.top-k` is an `OptionalInt` with no `@WithDefault`, and blanking it in config
  does not stop it being sent. The demo therefore pins **`claude-sonnet-4-6`**. This is a
  model-parameter incompatibility, not a telemetry problem — the conventions behave
  identically on either model.
- **Start the MCP server before the agent.** The agent resolves its tool list at startup;
  if the server isn't up, it boots with no tools and the model has nothing to call.
- **`/q/health` returns 404.** The health extension isn't installed. Check the log for
  `started in` instead — `scripts/run-investigation.sh` polls that endpoint and will wait
  forever otherwise.
- **The MCP SSE endpoint holds the connection open.** `curl http://localhost:8086/mcp/sse`
  will appear to hang; that is correct behaviour, not a failure.

---

## What this demo does *not* do

- **No LLM-as-judge yet.** Beat 7's evaluation events (`gen_ai.evaluation.result` with
  `root_cause_correctness` and `remediation_safety`) are designed but not built, so slide
  7.3 shows the contract rather than a capture.
- **No span durations captured** for the beat-6 waterfall; the bars there show structure,
  not measured timings.
- **The kind/OpenSearch path is parked.** `scripts/setup-kind.sh` and
  `scripts/setup-opensearch.sh` work but are not on the talk's critical path.
