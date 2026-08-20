# otter-sre

The Python SRE agent, instrumented by **OpenLLMetry**.

`../beaver-sre` is the same agent instrumented by **OpenInference**. The two directories are
deliberately **separate, complete copies**: same loop, same tools, same MCP server, same
database, same collector — and one instrumentation library different. That is what lets the
talk attribute a difference in the spans to the convention and nothing else, and it means each
directory can be read on its own as an example of instrumenting an agent under one convention.

## What emits what

| | |
|---|---|
| The model call | instrumented by OpenLLMetry — as of 0.62.3 it already emits `gen_ai.*`, including the new message shape |
| The agent and tool spans | written by hand in `agent.py`, in OTel GenAI names |
| Downstream | nothing. This agent needs no normalizing — it is the branch of the fan-out that has already converged |

Nothing auto-instruments a loop somebody wrote themselves, which is why the agent and tool
spans are hand-written. `gen_ai.tool.call.arguments` and its result are **opt-in** in the
conventions — the spec says instrumentation SHOULD NOT capture them by default — and this
agent writes them deliberately. That is the difference between a trace proving a tool ran and
one proving what it did.

## Files

```
agent.py        the loop, and the spans it writes by hand — this and telemetry.py are
                the two files that differ from ../beaver-sre; ../check-agents-agree.sh
                holds the rest byte-identical
telemetry.py    installs OpenLLMetry and the OTLP exporter
tools.py        the four tools the model is offered
db.py           PostgreSQL access
mcp_db.py       the same four tools over MCP, which is what the cluster uses
service.py      the HTTP service the capybara-sre console calls
app.py          one-shot CLI
tests/          21 tests, including one asserting this agent's vocabulary
```

## Run it

```bash
./run.sh "Customers are reporting missing accounts. Investigate."   # local, needs demos/.env
./.venv/bin/python -m pytest tests -q                               # tests
```

In the cluster it is deployed by `../deploy.sh` from `../k8s/otter-sre.yaml`, as its own image.
