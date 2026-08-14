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

The capybara customer database has five rows. A neighbouring team's service —
authenticating as the Postgres role `kangaroo` — connects **directly to the database**,
bypassing both agents, and deletes every free-plan capybara.

```
cappuccino  pro     ← survives
biscuit     free    ← deleted by kangaroo-service
nibbles     free    ← deleted by kangaroo-service
mochi       pro     ← survives
pepper      free    ← deleted by kangaroo-service
```

Then you ask an agent: *"Customers are reporting missing accounts. Investigate."*

**The root cause is a grant, not a bug.** `kangaroo` can do this because it was given
`DELETE` on a table it has no business deleting from — see
[`infrastructure/postgres/init.sql`](infrastructure/postgres/init.sql). A good diagnosis
names that, not just "rows are missing".

### How it is discoverable

An `AFTER` trigger records every change, with two different qualities of evidence:

| column | source | trustworthy? |
|---|---|---|
| `client` | `application_name` | **No.** Self-reported; any connection can claim anything. |
| `db_user` | `session_user` | **Yes.** The authenticated role. The client cannot lie about it. |

Two details worth pointing at on stage:

- The trigger is `SECURITY DEFINER`, so `kangaroo` can cause rows in the trail but
  **cannot delete them**. Try it: `permission denied for table audit_log`.
- It records `session_user`, not `current_user`. Under `SECURITY DEFINER` the latter
  becomes the function owner, which would make every deletion look like it came from the
  application.

Records are **UUIDs**, deliberately. With sequential ids an investigating agent solves the
case by pattern-matching gaps — and gets it wrong: it reads a roster starting at id 26 as
evidence that ids 1–25 were deleted. UUIDs remove the shortcut, so the audit trail is the
only place an answer can come from.

---

## The two agents

Same database, same incident, same question, same collector. They differ in platform.

| | **Capybara SRE** | **Beaver SRE** |
|---|---|---|
| platform | Java · Quarkus + LangChain4j | Python · Anthropic SDK |
| tools | over MCP, to a separate service | plain functions, same process |
| data | PostgreSQL, as `capybara_app` | the same PostgreSQL, as `capybara_app` |
| emits | `gen_ai.*` from the framework | `openinference.*` / `llm.*` — no OTel at all |
| arrives as | unchanged | `gen_ai.*`, via `gen_ai_normalizer` |
| judged | LLM-as-judge → `gen_ai.evaluation.result` | not judged |

Both are reachable from the one console: pick the agent in the top bar. Beaver runs in its
own pod and the Java app proxies to it, because the browser cannot see cluster-internal
services.

---

## Layout

```
00_run.sh              build and deploy everything
01_start-demo.sh       open the port-forwards, wait for them  (--status to just check)
02_cleanup.sh          delete the cluster

agents/
  capybara-sre/        the Java agent, and the console it serves at /
  capybara-db-mcp/     the MCP server it calls
  capybara-db-core/    shared database access, plain JDBC, no framework
  beaver-sre/          the Python agent
  k8s/                 their deployments
  deploy.sh            build all three images, load into kind, roll out

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

A second MCP server, `prod-db-mcp`, runs the *same image* as `capybara-db-mcp` but is handed the
`kangaroo` role's credentials and `application_name=goose`. Same server code, different grants,
which is the real failure: the MCP server is fine, the credentials it was given are not.

Point a coding agent at it and the deletion happens for the ordinary reason. A developer asks for
a tidy-up, the agent does what it was asked, and it succeeds because the credentials permit it.

```bash
brew install block-goose-cli        # v1.46.0 or newer; earlier releases emit no gen_ai.*
ollama pull qwen3.6:35b-a3b-q4_K_M  # keep Ollama on the host: Docker cannot pass the GPU on a Mac
agents/goose/run-recipe.sh
```

What the audit trail then records, and why it is better than the button:

```
DELETE  biscuit  client=goose  role=kangaroo
```

`client` names the agent and is self-reported. `db_user` names the human's credentials and is
authenticated. One row, two questions, and only one of the answers can be forged.

The agent's own telemetry lands in the same collector as everything else, so its
`gen_ai.tool.call.arguments` and `gen_ai.tool.call.result` sit beside Capybara's investigation.
See [`ANALYSIS.md`](ANALYSIS.md) for what that comparison shows.

**The kangaroo button still works and is still the reliable trigger.** This runs alongside it,
not instead of it: it depends on a local model behaving, which a button does not.

## On stage

**1 · Reset, and show the table.** Five capybaras, three on the free plan.

**2 · Unleash the kangaroos.** Three rows gone. Nothing either agent did caused this.

**3 · Watch the metric.** In Prometheus, `capybara_records` steps from 5 to 2, and
`capybara_records_deleted_total` broken down by `capybara_actor_db_user` says who — the same
distinction the audit trail makes, one signal earlier. The gauge is observable, so it reads
the table when the SDK collects and cannot drift from reality even when something deletes
rows without telling us. Export interval is 15s: press the button and keep talking.

**4 · Ask Capybara.** It calls `list_records`, sees two rows, calls `audit_log`, and
reports that an external role did it — explicitly not this application.

**5 · Read the judge.** `root_cause_correctness` and `remediation_safety`, each with the
judge's reasoning naming the evidence that decided it.

**6 · Ask Beaver the same question,** and open its trace. The `messages.create` span
carries `llm.*` **and** `gen_ai.*` at once: what the library emitted, and what the
collector made of it.

**7 · Then the forensic gap.** `kubectl set env deployment/capybara-sre CAPYBARA_TOOLS=local`,
re-run, and diff the tool spans. Same binary, same prompt, same database — only the
registration differs. Re-run `./01_start-demo.sh` afterwards; changing env rolls the pod
and takes the port-forward with it.

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
| a schema change seems not to apply | `init.sql` only runs on an empty data directory. `infrastructure/deploy.sh` stamps its hash on the pod template so a change recreates the pod |
