# Demo 2 — Capybara in the wrong convention

**The same capybara incident as Demo 1, told in the wrong vocabulary, and fixed in flight
by the OpenTelemetry Collector.**

This is the demo behind beat 5 of the talk: *your tool doesn't speak OTel semantics — now
what?* An agent instrumented with **OpenInference** emits `llm.*` / `openinference.*`
attributes. The collector's `gen_ai_normalizer` processor rewrites them to the official
OTel GenAI semantic conventions before they reach any backend, and the demo shows exactly
how far that gets you — including what it does **not** fix.

---

## What it demonstrates

1. **Fragmentation is real and mechanical.** The same model call, described in someone
   else's vocabulary, is unreadable to an OTel-native backend.
2. **You can fix it centrally, without touching the application.** One processor block in
   the collector, no code change, works for any language.
3. **"Normalization" is partial, and the honest word matters.** Measured on a real run:
   27 span attributes become 16. Some keys are renamed, thirteen flattened message keys
   collapse into two structured ones — and nine attributes come through untouched,
   including one the processor simply doesn't know about.

That third point is the reason this demo exists. It is easy to claim the collector "fixes"
convention drift; this shows the seam.

---

## How it works

```
agent/app.py                    the capybara agent, instrumented with OpenInference
      │                         (openinference-instrumentation-anthropic)
      │  OTLP/HTTP :4318
      ▼
OTel Collector (contrib 0.158.0)
      │  processors: [gen_ai_normalizer]
      │    sources: openinference, openllmetry   (remove_originals: true)
      ├──► debug exporter   → stdout, the evidence you read in this demo
      └──► otlphttp/openlit → OpenLIT UI on :3001
```

The agent is deliberately the *same scenario* as Demo 1 — the capybara customer database,
the same three tools (`list_records`, `query`, `delete_records`), the same seed data from
[`../agent/tools.py`](../agent/tools.py). Only the instrumentation differs. That is the
whole point: one story, two conventions.

### The processor config

```yaml
processors:
  gen_ai_normalizer:
    sources:
      - name: openinference
        remove_originals: true
      - name: openllmetry
        remove_originals: true
```

`gen_ai_normalizer` is **alpha**, **traces only**, and has **no auto-detection** — you list
the source conventions explicitly. It ships in the released contrib image; no custom `ocb`
build is needed. Its donation to contrib
([issue #46069](https://github.com/open-telemetry/opentelemetry-collector-contrib/issues/46069))
was accepted and closed on 1 June 2026.

---

## Prerequisites

- Docker + Docker Compose
- Python 3.11+
- An Anthropic API key in `demos/.env` (`ANTHROPIC_API_KEY=sk-ant-...`)

---

## Run it

```bash
cd demos/normalizer
docker compose up -d          # collector + OpenLIT + ClickHouse
sleep 15                      # OpenLIT initialises its database on first boot
```

Then run the agent. The first run creates a venv and installs dependencies:

```bash
./agent/run.sh "We are over quota. Delete the free-plan capybaras to free up space."
```

Watch the rewrite happen:

```bash
docker compose logs collector | grep -A30 "Span #0"
```

Tear down:

```bash
docker compose down -v
```

---

## Demo flow (for the stage)

**1 · Show the raw convention first.** Comment the processor out of the pipeline, restart
the collector, run the agent, and read the debug output. You get `llm.model_name`,
`llm.token_count.prompt`, `openinference.span.kind` — and a backend that expects `gen_ai.*`
sees nothing it recognises.

```yaml
    traces:
      receivers: [otlp]
      processors: []          # ← normalizer off
      exporters: [debug, otlphttp/openlit]
```

**2 · Turn the processor on.** Restore `processors: [gen_ai_normalizer]`, restart, re-run.
Same agent, same code, no redeploy of anything that matters.

**3 · Read the diff out loud.** This is the payload of the beat:

| | |
|---|---|
| `llm.provider` | → `gen_ai.provider.name` |
| `llm.model_name` | → `gen_ai.request.model` |
| `llm.token_count.prompt` | → `gen_ai.usage.input_tokens` |
| `llm.token_count.completion` | → `gen_ai.usage.output_tokens` |
| `openinference.span.kind` | → `gen_ai.operation.name` |
| `llm.input_messages.*` (9 keys) | → `gen_ai.input.messages` |
| `llm.output_messages.*` (4 keys) | → `gen_ai.output.messages` |

**4 · Then show the seam — this is the honest half.** Nine attributes survive untouched:

```
llm.system                  ← survives even with remove_originals: true
llm.tools.0/1/2.tool.json_schema
llm.invocation_parameters
input.value / input.mime_type
output.value / output.mime_type
span name: messages.create  ← unchanged; the processor rewrites attributes, not names
```

`llm.system` is the one to point at. `remove_originals: true` is set, and it still comes
through — because it is not in the processor's mapping table. The result is a **hybrid
span**: OTel core dimensions, OpenInference everything-else. That fixes your dashboards and
your cost maths. It does not make an OpenInference trace OTel-native end to end.

---

## Measured results

From a real run on 2026-08-09, contrib 0.158.0, `claude-sonnet-5`:

- **27 span attributes → 16** (resource attributes excluded)
- **18 removed**, **7 written**, **9 untouched**
- Span name unchanged: `messages.create`
- Agent behaviour identical to Demo 1: deleted 2 free-plan capybaras (`biscuit`,
  `nibbles`), 1 remaining — the same `{"deleted": 2, "remaining": 1}` the talk quotes

---

## Backends

- **OpenLIT** — <http://localhost:3001>. It ingests OTLP/HTTP on `4318`; note the exporter
  must be `otlphttp`, not `otlp` (which is gRPC and will silently fail to connect).
- **debug exporter** — stdout. This is the one that matters for the demo; it shows
  attribute names verbatim, with nothing between you and the data.

---

## Gotchas found while building this

- **The `otlp` exporter is gRPC.** Pointing it at OpenLIT's `4318` produces
  `connection refused` in a loop and no traces. Use `otlphttp`.
- **OpenLIT needs a writable data volume** (`/app/client/data`) or its entrypoint dies with
  `.nextauth_secret: No such file or directory` and the container exits immediately.
- **`gen_ai_normalizer` has no auto-detection.** If you forget to list a source, spans pass
  through completely untouched and everything looks like the processor is broken.
