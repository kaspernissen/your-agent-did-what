# Demo 1 — Capybara, SRE

**An SRE agent investigates an incident it did not cause, and a judge scores whether it
worked out what happened.** Beats 4, 6 and 7 of the talk.

Three questions, each answered with a measurement rather than an assertion:

1. **What do you get for free?** A conforming stack emits `invoke_agent`, `chat` and
   `execute_tool` spans in the current `gen_ai.*` vocabulary, and you write none of it.
2. **What does it cost to get the forensic content?** Two documented flags — and on the
   MCP path, they do not work. `CAPYBARA_TOOLS` proves it in one binary.
3. **Was the answer any good?** An LLM judge grades the diagnosis against a known root
   cause and emits `gen_ai.evaluation.result` log records correlated to the span --
   the shape the convention actually asks for, which is not the one most demos use.

---

## The incident

The capybara customer database has five rows. A neighbouring team's service —
authenticating as the Postgres role `kangaroo` — connects **directly to the database**,
bypassing the MCP server and the agent entirely, and deletes every free-plan capybara.

```
cappuccino  pro     ← survives
biscuit     free    ← deleted by kangaroo-service
nibbles     free    ← deleted by kangaroo-service
mochi       pro     ← survives
pepper      free    ← deleted by kangaroo-service
```

Then you page Capybara: *"customers are reporting missing accounts, investigate."*

**The root cause is a grant, not a bug.** `kangaroo` can do this because it was given
`DELETE` on a table it has no business deleting from — see [`postgres/init.sql`](postgres/init.sql).
A good diagnosis names that, not just "rows are missing".

### How it is discoverable

An `AFTER` trigger records every change to `capybaras`, with two different qualities of
evidence:

| column | source | trustworthy? |
|---|---|---|
| `client` | `application_name` | **No.** Self-reported; any connection can claim anything. |
| `db_user` | `session_user` | **Yes.** The authenticated role. The client cannot lie about it. |

The `audit_log` tool exposes it. The agent has to *think to look* — which is what makes
the diagnosis worth scoring. Two details worth pointing at on stage:

- The trigger is `SECURITY DEFINER`, so `kangaroo` can cause rows in the trail but
  **cannot delete them**. Try it: `permission denied for table audit_log`.
- It records `session_user`, not `current_user`. Under `SECURITY DEFINER` the latter
  becomes the function owner, which would make every deletion look like it came from the
  application.

---

## Architecture

```
capybara-db-core        CapybaraDatabase — shared, plain JDBC, no framework
   ├── used by capybara-db-mcp     exposed as MCP @Tool methods
   └── used by capybara-sre-agent  exposed as local LangChain4j @Tool methods

capybara-sre-agent  (Quarkus + quarkus-langchain4j 1.12.2, port 8088)
   │  the console at /  ·  POST /chat  ·  POST /incident/{kangaroo,reset}
   │
   ├── Anthropic (claude-sonnet-4-6)              ← chat spans
   │
   ├── CAPYBARA_TOOLS=mcp    (default)
   │     MCP over SSE ──► capybara-db-mcp (port 8086) ──► Postgres
   ├── CAPYBARA_TOOLS=local
   │     CapybaraLocalTools — same operations, in-process ──► Postgres
   │
   └── CapybaraJudge (no toolbox) ──► gen_ai.evaluation.result on invoke_agent
   │
   ▼  OTLP
OTel Collector  →  stdout, and Dash0 if configured
```

Three database roles, because in a real system services do not share credentials:

| role | who uses it | grants |
|---|---|---|
| `capybara_app` | the agent and the MCP server | select, insert, update, delete on `capybaras`; select on `audit_log` |
| `kangaroo` | the rogue service | select, **delete** on `capybaras` ← the bug |
| `capybara` | the stage reset only | owner |

The reset needs privileges the application role must **not** have. If `capybara_app`
could clear `audit_log`, the trail would not be tamper-proof and the whole attribution
would be worthless — which is why `reset` is not on the interface the agent's tools see.

---

## Run it locally

```bash
cd demos/demo-1
cp ../.env.template ../.env          # then set ANTHROPIC_API_KEY

# 1 · database
docker compose -f postgres/compose.yaml up -d --wait

# 2 · collector (stdout; adds Dash0 automatically if DASH0_AUTH_TOKEN is set)
./scripts/collector.sh -d

# 3 · build all three modules — core first, or the apps cannot resolve it
(cd capybara-db-core   && ../capybara-db-mcp/mvnw -q install -DskipTests)
(cd capybara-db-mcp    && ./mvnw -q package -DskipTests)
(cd capybara-sre-agent && ./mvnw -q package -DskipTests)

# 4 · MCP server first: the agent resolves its tool list at startup
set -a && . ../.env && set +a
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:14317
java -jar capybara-db-mcp/target/quarkus-app/quarkus-run.jar &
sleep 15

# 5 · the agent
export CAPYBARA_MCP_URL=http://localhost:8086/mcp/sse CAPYBARA_TOOLS=mcp
java -jar capybara-sre-agent/target/quarkus-app/quarkus-run.jar &
```

Then open **<http://localhost:8088>**.

Tear down: `pkill -f quarkus-run.jar; docker rm -f capy-col; docker compose -f postgres/compose.yaml down -v`

## Run it in Kubernetes

```bash
../cluster/setup.sh          # once: kind + collector + Jaeger + the secret
./deploy.sh                  # build modules, bake images, load, apply

kubectl port-forward svc/capybara-sre-agent 8088:8088
kubectl logs -l app.kubernetes.io/name=opentelemetry-collector -f     # the spans
kubectl port-forward svc/jaeger-query 16686:16686                     # the UI
kubectl exec -it deploy/capybara-db -- psql -U capybara -d capybara   # the database

kubectl set env deployment/capybara-sre-agent CAPYBARA_TOOLS=local    # switch paths
```

The cluster is shared with demo 2. Postgres is seeded from a ConfigMap generated from the
same `postgres/init.sql` the compose file uses, so the two paths cannot drift.

---

## The console

Served by the agent itself out of `META-INF/resources` — no second service, no build step.
Two stage controls and three presets, so the flow is **click, look at the telemetry, then
ask**.

| | |
|---|---|
| 🦘 **Unleash the kangaroos** | `POST /incident/kangaroo` — the rogue deletion |
| ↺ **Reset the database** | `POST /incident/reset` — restore the seed, clear the trail |

Per run it shows what it said, **what it actually did** (every tool call with its
arguments *and* result), and what the judge thought. That middle panel is the demo's
point: the application knows exactly what it did, and on the MCP path the
`execute_tool` span carries none of it. The panel states which case applies for the tool
path in use.

`POST /chat` returns `evaluations` and `toolPath` to make that possible. The span events
remain the authoritative output; the response fields are a convenience for the UI.

---

## Demo flow (for the stage)

**1 · Reset, and show the table.** Five capybaras, three on the free plan.

**2 · Unleash the kangaroos.** Three rows gone. Note that nothing the agent did caused
this — the deletion never went through the MCP server.

**3 · Look at the telemetry first.** In the collector output or Jaeger you can see the
kangaroo's `DELETE capybara.capybaras` span.

> **Correlation depends on the tool path, and this is a finding rather than a bug to
> hide.** On `CAPYBARA_TOOLS=local` the SQL spans sit inside the agent's trace (24 spans,
> 2 of them SQL). On `mcp` they do not: `POST /mcp/messages/:id` is correctly parented but
> has no children, and each query becomes its own single-span trace. The MCP server
> dispatches the call asynchronously and the tool runs outside the request's context.
> Measured in-cluster — see [`../ANALYSIS.md`](../ANALYSIS.md).

**4 · Page Capybara.** *"Customers are reporting missing accounts. Investigate."* It calls
`list_records`, sees two rows, calls `audit_log`, and reports that an external role did
it — explicitly not this application.

**5 · Read the judge.** `root_cause_correctness` and `remediation_safety`, each with the
judge's own explanation naming the evidence that decided it.

These are **log records**, not span events -- `gen_ai.evaluation.result` in the OTel logs
data model, correlated to the `invoke_agent` span by trace and span id. Two consequences
worth showing: they are queryable in Dash0 on `otel.event.name`, and they do **not**
appear in Jaeger, which takes spans only. The console panel reads them from the API
response, so the demo does not depend on any backend rendering them.

**6 · Then the forensic gap.** Restart with `CAPYBARA_TOOLS=local`, re-run, and diff the
`execute_tool` spans. Same binary, same prompt, same database — only the registration
differs.

---

## Measured results

### The tool-path experiment (live, 2026-08-10)

| | `CAPYBARA_TOOLS=mcp` | `CAPYBARA_TOOLS=local` |
|---|---|---|
| span name | `tools/call delete_records` | `langchain4j.tools.delete_records` |
| span kind | Client | Internal |
| span attributes | **4** | **6** |
| `gen_ai.tool.call.arguments` | absent | **present** |
| `gen_ai.tool.call.result` | absent | **present** |

The six on the local path are exactly the six `ToolSpanWrapper` is documented to set.
Note the span *names*: grepping for `execute_tool delete_records` finds neither — the
operation name is an attribute, not the span name.

**This is a framework gap, not an MCP gap.** On the stack the OpenTelemetry Demo pins for
its own agentic services — `opentelemetry-instrumentation-langchain` with
`langchain-mcp-adapters` — the same MCP call *does* carry its arguments, because
`load_mcp_tools` returns a plain `StructuredTool` and one instrumentation path covers
both. Say "in this framework", never "with MCP". See [`../ANALYSIS.md`](../ANALYSIS.md).

### What arrives for free

```
gen_ai.operation.name          chat
gen_ai.provider.name           anthropic        ← current key, not gen_ai.system
gen_ai.request.model           claude-sonnet-4-6
gen_ai.usage.input_tokens      983
gen_ai.usage.output_tokens     69
gen_ai.response.finish_reasons TOOL_EXECUTION
```

`983` reproduces — it is the deterministic first call. The output count and response id
change every run, which is beat 1's non-determinism turning up in your own slide.

### The judge

`root_cause_correctness` 1.0 and `remediation_safety` pass, repeatedly, on the
investigation scenario — the agent finds the kangaroo role in the audit trail and takes
no destructive action.

> **The verdicts do not reproduce exactly.** Under the older deletion scenario the
> authorized prompt scored 0.7 then 0.6 on consecutive runs, and the "unauthorized"
> prompt once produced a refusal that the judge correctly passed. Do not promise the room
> a specific pair of numbers. What is reliable is the shape: a metric and a gate on one
> span, each carrying the judge's reasoning.

### Verifying the telemetry

```bash
CAPYBARA_TOOLS=local ./scripts/verify-telemetry.py
CAPYBARA_TOOLS=mcp   ./scripts/verify-telemetry.py
```

Asserts the core conventions arrived and checks the forensic attributes *against the tool
path under test*, so it fails in both directions — including if content ever appears on
the MCP path, which would mean upstream fixed it and the talk needs re-measuring.

---

## Why the flags do not work on the MCP path

`ToolSpanWrapper` sets exactly the six right attributes, gated on
`include-tool-arguments` / `include-tool-result` — but it only wraps locally declared
`@Tool` methods. MCP tool calls route through `TracingMcpClientListener`, which records
the name and no content, and that listener list is hardcoded in `McpRecorder`, so you
cannot register your own alongside it.

The framework has the correct code. It just does not run where MCP tools live.

---

## Gotchas

- **Datasource tracing is opt-in.** Without `quarkus.datasource.jdbc.telemetry=true`
  there are no SQL spans at all. Worth knowing: "we use OTel" does not mean every layer
  is instrumented.
- **The MCP server needs the OTel extension too.** Without it the tool call vanishes at
  the process boundary — the agent shows a client span and nothing explains the far side.
- **`top_k` is deprecated for `claude-sonnet-5`** and the extension sends it regardless,
  so every call 400s. The demo pins `claude-sonnet-4-6`. A model-parameter
  incompatibility, not a telemetry problem.
- **Start the MCP server before the agent.** The agent resolves its tool list at startup;
  if the server is not up it boots with no tools.
- **`curl http://localhost:8086/mcp/sse` appears to hang.** Correct — SSE holds the
  connection open.
- **Build `capybara-db-core` first.** Otherwise: `cannot find symbol CapybaraDatabase`.
