# beaver-sre

The Python SRE agent, instrumented by **OpenInference**.

`../otter-sre` is the same agent instrumented by **OpenLLMetry**. The two directories are
deliberately **separate, complete copies**: same loop, same tools, same MCP server, same
database, same collector — and one instrumentation library different. That is what lets the
talk attribute a difference in the spans to the convention and nothing else, and it means each
directory can be read on its own as an example of instrumenting an agent under one convention.

## What emits what

| | |
|---|---|
| The model call | instrumented by OpenInference — emits `llm.*` and `openinference.*`, not the OTel names |
| The agent and tool spans | written by hand in `agent.py`, in OpenInference names |
| Downstream | the collector's `gen_ai_normalizer` rewrites this agent into `gen_ai.*`, keeping the originals — so one span carries both vocabularies and you can see what the translation does and does not cover |

Nothing auto-instruments a loop somebody wrote themselves, which is why the agent and tool
spans are hand-written. `gen_ai.tool.call.arguments` and its result are **opt-in** in the
conventions — the spec says instrumentation SHOULD NOT capture them by default — and this
agent writes them deliberately. That is the difference between a trace proving a tool ran and
one proving what it did.

## Files

```
agent.py        the loop, and the spans it writes by hand — this and telemetry.py are
                the two files that differ from ../otter-sre; ../check-agents-agree.sh
                holds the rest byte-identical
telemetry.py    installs OpenInference and the OTLP exporter
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

In the cluster it is deployed by `../deploy.sh` from `../k8s/beaver-sre.yaml`, as its own image.
