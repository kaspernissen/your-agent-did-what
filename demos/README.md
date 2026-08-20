# The demo

**One incident. Two SRE agents on different platforms. One collector.** Everything the
talk claims is measured here rather than asserted — the measurements, with dates, are in
[`ANALYSIS.md`](ANALYSIS.md).

```bash
cp .env.template .env      # then set ANTHROPIC_API_KEY
./00_run.sh                # cluster, database, both agents  (~5 min cold)
./01_start-demo.sh         # port-forwards, waits until they answer
./02_cleanup.sh            # delete the cluster
```

Then open **<http://localhost:8088>**.

---

## The incident

The capybara customer database has five rows. A developer asks their own coding agent to
tidy up the free plan. It does: goose calls `delete_records` on `prod-db-mcp`, and that
server is holding `deploy_svc` credentials, which carry `DELETE`.

```
cappuccino  pro     ← survives
biscuit     free    ← deleted, client=goose, db_user=deploy_svc
nibbles     free    ← deleted, client=goose, db_user=deploy_svc
mochi       pro     ← survives
pepper      free    ← deleted, client=goose, db_user=deploy_svc
```

Then you ask the investigating agents: *"Customers are reporting missing accounts.
Investigate."*

**The root cause is a grant, not a bug.** `deploy_svc` can do this because it was given
`DELETE` on a table it has no business deleting from — see
[`infrastructure/postgres/init.sql`](infrastructure/postgres/init.sql). A good diagnosis
names that, not just "rows are missing".

**And nobody granted the agent anything.** The credential belongs to a deployment service
account, the kind that legitimately sits in a `.env` file, and it carries `DELETE` because
deployments need `DELETE`. The agent never saw a password. It asked for a tool by name and
inherited the authority behind it.

### How it is discoverable

An `AFTER` trigger records every change, with two different qualities of evidence:

| column | source | trustworthy? |
|---|---|---|
| `client` | `application_name` | **No.** Self-reported; any connection can claim anything. |
| `db_user` | `session_user` | **Yes.** The authenticated role. The client cannot lie about it. |

Two details worth pointing at on stage:

- The trigger is `SECURITY DEFINER`, so `deploy_svc` can cause rows in the trail but
  **cannot delete them**. Try it: `permission denied for table audit_log`.
- It records `session_user`, not `current_user`. Under `SECURITY DEFINER` the latter
  becomes the function owner, which would make every deletion look like it came from the
  application.

Records are **UUIDs**, deliberately. With sequential ids an investigating agent solves the
case by pattern-matching gaps — and gets it wrong: it reads a roster starting at id 26 as
evidence that ids 1–25 were deleted. UUIDs remove the shortcut, so the audit trail is the
only place an answer can come from.

---

## The three agents

Same database, same incident, same question, same tools, same MCP server, same collector. The
only thing that differs is what writes the telemetry — which is the point, and it took work to
make true. The Python agents used to call their tools in-process, so any comparison of their
*tool* spans measured the topology instead of the libraries. They now go through
`customer-db-mcp` like the Java one does; see `agents/beaver-sre/mcp_db.py`.

| | **Capybara SRE** | **Beaver SRE** | **Otter SRE** |
|---|---|---|---|
| platform | Java · Quarkus + LangChain4j | Python · Anthropic SDK | Python · Anthropic SDK |
| instrumented by | the framework | OpenInference | OpenLLMetry |
| tools | over MCP, to `customer-db-mcp` | the same, over MCP | the same, over MCP |
| data | PostgreSQL, as `app_svc` | via the MCP server | via the MCP server |
| model call emits | `gen_ai.prompt` / `gen_ai.completion`, both removed from the spec | `llm.*` / `openinference.*` | `gen_ai.*`, already current |
| arrives as | unchanged | `gen_ai.*`, via `gen_ai_normalizer` | unchanged, nothing to convert |
| tool span | the framework's, 6 attributes | hand-written, arguments only | hand-written, arguments and result |
| judged | LLM-as-judge → `gen_ai.evaluation.result` | not judged | not judged |

The two Python agents are separate directories and separate images — `agents/beaver-sre` and
`agents/otter-sre` — so each is readable end to end as an example of instrumenting an agent under
one convention. They are complete copies of each other apart from which library instruments the
model call, and `agents/check-agents-agree.sh` fails the build if the files that are meant to be
identical have drifted; `deploy.sh` runs it. Their tool spans are hand-written, because nothing
auto-instruments a loop somebody wrote by hand — which is why that row still says as much about
our code as about their libraries.

All three are reachable from the one console: pick the agent in the top bar. The Java app serves
that console and proxies to the Python pods, because the browser cannot see cluster-internal
services. Keeping the console inside `capybara-sre` is a deliberate choice rather than an
oversight: splitting it out would need its own image and a proxy for CORS, and it buys no
telemetry improvement — the proxy's HTTP client is uninstrumented, so the Python agents' traces
are already clean single-service roots. Goose is not in the console at all, by design: it runs in
a terminal, which is where a developer would actually meet it.

---

## Layout

```
00_run.sh              build and deploy everything
01_start-demo.sh       open the port-forwards, wait for them  (--status to just check)
02_cleanup.sh          delete the cluster

agents/
  capybara-sre/        the Java agent, and the console it serves at /
  customer-db-mcp/     the MCP server it calls
  customer-db-core/    shared database access, plain JDBC, no framework
  beaver-sre/          the Python agent, instrumented by OpenInference
  otter-sre/           the same agent, instrumented by OpenLLMetry — a separate complete copy,
                       so each reads on its own; the only difference is telemetry.py and the
                       vocabulary agent.py writes. db.py reads Postgres directly, mcp_db.py
                       goes through the MCP server
  goose/               the recipe and runner for the developer-with-an-agent path
  k8s/                 their deployments
  check-agents-agree.sh fails if beaver and otter drift apart in anything but the library
  deploy.sh            build every image, load into kind, roll out

infrastructure/
  postgres/init.sql    the schema, the trigger, the roles, the seed
  k8s/                 the database deployment
  deploy.sh            builds the ConfigMap from init.sql — one definition, no drift

observability/
  collector/           values.yaml, and values.dash0.yaml layered on when a token is set
  jaeger/  prometheus/ helm values

cluster/setup.sh       kind, secrets, and the three observability charts
scripts/               verify-telemetry.py
```

---

## The developer with an agent (optional, alongside)

A second MCP server, `prod-db-mcp`, runs the *same image* as `customer-db-mcp` but is handed the
`deploy_svc` role's credentials and `application_name=goose`. Same server code, different grants,
which is the real failure: the MCP server is fine, the credentials it was given are not.

Point a coding agent at it and the deletion happens for the ordinary reason. A developer asks for
a tidy-up, the agent does what it was asked, and it succeeds because the credentials permit it.

```bash
brew install block-goose-cli        # v1.46.0 or newer; earlier releases emit no gen_ai.*
ollama pull qwen3.6:35b-a3b-q4_K_M  # host only: Docker cannot pass the GPU through on a Mac
agents/goose/run-recipe.sh
```

`run-recipe.sh` picks its provider rather than asking you to remember which machine you are on:

| Where | Provider | Model | Why |
|---|---|---|---|
| **Host** | `ollama` | `qwen3.6:35b-a3b-q4_K_M` | The path the slides show — a local model on the presenter's own laptop, on the GPU. |
| **Devcontainer** | `anthropic` | `claude-sonnet-5` | No GPU passthrough there, and a CPU-sized model cannot be relied on to call `delete_records` — which is the only thing this run has to do. |

Force either with `GOOSE_PROVIDER=ollama|anthropic`. Both were measured on 2026-08-19 and the
telemetry is the same shape — 7 spans, one root, `gen_ai.tool.call.arguments` and
`.result` both present. Only `gen_ai.request.model` differs, so a container run will not match
the model name on the slides. Present from the host.

What the audit trail then records, and why it is better than the button:

```
DELETE  biscuit  client=goose  db_user=deploy_svc
```

`client` names the tool and is self-reported. `db_user` names the credential it borrowed and is
authenticated. One row, two questions, and only one of the answers can be forged.

The agent's own telemetry lands in the same collector as everything else, so its
`gen_ai.tool.call.arguments` and `gen_ai.tool.call.result` sit beside Capybara's investigation.
See [`ANALYSIS.md`](ANALYSIS.md) for what that comparison shows.

### The extra door

`POST /incident/rehearse-deletion` reproduces this incident without goose, ollama or a model. It
connects with the same `deploy_svc` credentials and issues the same `DELETE`, so the database, the
audit trail, the metric and every investigation built on top of them behave identically.

```sh
curl -X POST http://localhost:8088/incident/rehearse-deletion
# {"deleted":3,"remaining":2,"by":"goose (db role: deploy_svc)"}
```

It exists because this is the one step in the demo that depends on a laptop cooperating, and a
conference is a poor place to find out that it will not. Use it to rehearse, and keep it in reach
on stage.

Two things it does not do, both deliberate. It produces **no agent telemetry**, so nothing in any
trace explains *why* the rows went — which is precisely the evidence this talk is about, so the
coding-agent slides have nothing to show if you use it. And it reports `client=goose` through
`ApplicationName` even though no goose ran, which is honest in a way worth noticing: `client` is
self-reported, so a connection claiming to be goose is exactly what the forgeable column looks
like. `db_user` still says `deploy_svc`, because that one Postgres vouches for.

It is not in the console, so nobody clicks it by accident while the room is watching.

## On stage

**1 · Reset, and show the table.** Five customers, three on the free plan.

**2 · Run the coding agent.** `agents/goose/run-recipe.sh`. A developer asks for a tidy-up,
goose calls `delete_records`, three rows gone. Nothing the investigating agents did caused it.

> **The extra door.** This step is the one that depends on things outside the cluster: ollama
> running, the model loaded, a laptop that has not decided to throttle. If it stalls, or the
> model wanders off and never calls the tool, do not debug it on stage:
>
> ```sh
> curl -X POST http://localhost:8088/incident/rehearse-deletion
> ```
>
> Same `deploy_svc` credentials, same `DELETE`, same audit trail — the database lands exactly
> where a real run leaves it, so steps 3 to 7 all work unchanged. What you lose is goose's own
> telemetry, so skip the coding-agent trace and say you are showing the investigation side. It
> is a deliberate escape hatch, not a cheat, but it is worth saying out loud if the room can see
> the terminal.

**3 · Watch the metric.** In Prometheus, `capybara_records` steps from 5 to 2, and
`capybara_records_deleted_total` broken down by `capybara_actor_db_user` says who — the same
distinction the audit trail makes, one signal earlier. The gauge is observable, so it reads
the table when the SDK collects and cannot drift from reality even when something deletes
rows without telling us. Export interval is 15s: start the run and keep talking.

**4 · Ask Capybara.** It calls `list_records`, sees two rows, calls `audit_log`, and reports
that `deploy_svc` did it, with `client=goose` beside it — explicitly not this application.

**5 · Read the judge.** `root_cause_correctness` and `remediation_safety`, each with the
judge's reasoning naming the evidence that decided it.

**6 · Ask Beaver the same question,** and open its trace. The `messages.create` span
carries `llm.*` **and** `gen_ai.*` at once: what the library emitted, and what the
collector made of it.

**7 · Then the forensic gap.** `kubectl set env deployment/capybara-sre AGENT_TOOLS=local`,
re-run, and diff the tool spans. Same binary, same prompt, same database — only the
registration differs. Re-run `./01_start-demo.sh` afterwards; changing env rolls the pod
and takes the port-forward with it.

**8 · And the context gap, with the fix in your hand.** The tool body's SQL joins the agent's trace
because `CustomerDbTools` reads `traceparent` out of the MCP request's `_meta` itself. To show the gap
as quarkus-mcp-server leaves it:

```sh
kubectl set env deployment/customer-db-mcp MCP_PROPAGATE_CONTEXT=false
kubectl rollout restart deployment/capybara-sre   # or its MCP session dies with the server
./01_start-demo.sh
```

21 spans and the `SELECT` in a trace of its own. Set it back to `true` for 27 spans and one trace. See
[`ANALYSIS.md`](ANALYSIS.md) for the measurement and why `@WithSpan` alone does not work.

---

## What is measured, not asserted

All of it is in [`ANALYSIS.md`](ANALYSIS.md) with dates. The headlines:

- **The MCP path loses the tool call's content.** 4 span attributes versus 6 on the local
  path; `gen_ai.tool.call.arguments` and `.result` absent. It is a *framework* gap, not an
  MCP gap — say "in this framework", never "with MCP".
- **The MCP path loses the trace at one specific hop.** With
  `quarkus.mcp.server.tracing.enabled=true` (off by default, and it needs
  quarkus-mcp-server 1.13.1) the server's `tools/call` spans sit correctly inside the
  agent's trace. The tool *body* still does not: each SQL query is its own root, because
  the extension runs the tool on a new duplicated Vert.x context —
  [#789](https://github.com/quarkiverse/quarkus-mcp-server/issues/789), open, "No ETA".
  Streamable HTTP was tried and is worse, so the transport is not the variable.
- **The normalizer is partial, and asymmetric.** It converts the whole structure —
  AGENT→`invoke_agent`, TOOL→`execute_tool`, LLM→`chat` — and the tool call's *arguments*,
  but there is no mapping for the *result*. Two roads to the same missing half.
- **Evaluations are log records, not span events**, which is what the convention asks for
  and what most implementations get wrong. They do not appear in Jaeger; Jaeger takes spans.

---

## Configuration

`demos/.env`, copied from `.env.template`:

| | |
|---|---|
| `ANTHROPIC_API_KEY` | required |
| `DASH0_AUTH_TOKEN` | optional. Set it and the collector also exports to Dash0; leave it and everything stays local. |
| `CAPYBARA_CLUSTER` | kind cluster name, default `capybara` |

---

## When something breaks

| symptom | cause |
|---|---|
| the console stops answering | a pod was replaced and took the port-forward with it. `./01_start-demo.sh` |
| `HTTP 000` from curl | same thing. Check with `./01_start-demo.sh --status` |
| Jaeger's dropdown lists services that no longer exist | its store is in memory and keeps old traces. `kubectl rollout restart deployment/jaeger` clears it — and clears your traces, so do it before a rehearsal, not during |
| the judge panel is empty | the judge's JSON was truncated. `max-tokens` is set to 4096; the raw reply is logged on failure |
| no SQL spans anywhere | `quarkus.datasource.jdbc.telemetry=true` is opt-in. Worth knowing: "we use OTel" does not mean every layer is instrumented |
| the agent boots with no tools | it resolves its tool list at startup and the MCP server was not up. `agents/deploy.sh` orders this correctly |
| the tool body's SQL is in its own trace | `MCP_PROPAGATE_CONTEXT` is `false`, which is the gap mode. `true` restores it. If it is already `true`, restart `capybara-sre` — a stale MCP session survives the server restart |
| a schema change seems not to apply | `init.sql` only runs on an empty data directory. `infrastructure/deploy.sh` stamps its hash on the pod template so a change recreates the pod |
| goose stalls, or the model never calls the tool | do not debug it live. `curl -X POST http://localhost:8088/incident/rehearse-deletion` puts the database in the same state with the same `deploy_svc` credentials. You lose the coding agent's telemetry and nothing else |
| the local model is not installed at all | same door. The investigation half of the demo needs no model beyond the agents' own |
