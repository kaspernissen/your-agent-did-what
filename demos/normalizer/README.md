# Demo: `gen_ai_normalizer` processor

This demo shows OpenInference-instrumented spans flowing through the OTel Collector's
`gen_ai_normalizer` processor, which rewrites vendor-specific LLM attributes to the
standardised [OTel GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/).

---

## What the processor does

| Source attribute (in) | Normalised attribute (out) |
|---|---|
| `llm.model_name` | `gen_ai.request.model` |
| `openinference.span.kind` | `gen_ai.operation.name` |
| `llm.token_count.prompt` | `gen_ai.usage.input_tokens` |
| `llm.token_count.completion` | `gen_ai.usage.output_tokens` |
| `llm.input_messages` | `gen_ai.prompt` |
| `llm.output_messages` | `gen_ai.completion` |

With `remove_originals: true` the source attributes are **dropped** from the span after
mapping — only the normalised `gen_ai.*` attributes are forwarded downstream.

Supported source conventions: `openinference`, `openllmetry`.

See the contrib tracking issue: <https://github.com/open-telemetry/opentelemetry-collector-contrib/issues/46069>

---

## Collector image / OCB status

**`otel/opentelemetry-collector-contrib:0.154.0` is NOT yet released** (confirmed at
demo-build time). The `gen_ai_normalizer` processor first shipped in contrib v0.154.0.

### Option A — wait for 0.154.0 (simplest)

Once the image is published on Docker Hub the `docker-compose.yml` works as-is:

```bash
docker compose up -d
```

### Option B — build a custom collector with OCB (available now)

Requirements: Go ≥ 1.21, `go.opentelemetry.io/collector/cmd/builder` (OCB).

```bash
# Install OCB
go install go.opentelemetry.io/collector/cmd/builder@v0.153.0

# Build the custom binary (output: ./otelcol-genai/otelcol-genai)
cd demos/normalizer
builder --config builder-config.yaml

# Run the collector directly (bypassing Docker for the collector service)
./otelcol-genai/otelcol-genai --config otel-collector-config.yaml
```

Then bring up the rest of the stack (ClickHouse + OpenLIT) separately:

```bash
docker compose up -d openlit-clickhouse openlit
```

The `builder-config.yaml` pins:
- `genainormalizerprocessor v0.153.0`
- `otlpreceiver v0.153.0`
- `debugexporter v0.153.0`
- `otlpexporter v0.153.0`

(Core modules resolve to `go.opentelemetry.io/collector/component v1.59.0` as required
by the processor's own `go.mod`.)

---

## Running the full demo

### 1. Prerequisites

- Docker + Docker Compose
- Python 3.11+
- `ANTHROPIC_API_KEY` set (or in `demos/.env`)

### 2. Start the stack

```bash
cd demos/normalizer
docker compose up -d
```

Wait ~10 s for ClickHouse and OpenLIT to initialise.

### 3. Run the agent

```bash
./agent/run.sh "Delete free-plan records."
```

The script creates a Python venv on first run and installs OpenInference + OTel SDK
automatically.

### 4. Observe the before/after rewrite

```bash
docker compose logs collector
```

In the `debug` exporter output you will see **only `gen_ai.*` attributes** — the original
`llm.*` / `openinference.*` attributes have been removed by `remove_originals: true`.

### 5. OpenLIT dashboard

Open <http://localhost:3001> (default credentials: `user@openlit.io` / `openlituser`).
Traces forwarded via `otlp/openlit` appear under the LLM Observability section.

---

## Architecture

```
agent/app.py  (OpenInference instrumentation)
      │  OTLP/HTTP :4318
      ▼
  OTel Collector
      │  gen_ai_normalizer processor
      │    openinference → gen_ai.*   (remove_originals: true)
      │    openllmetry   → gen_ai.*   (remove_originals: true)
      ├──► debug exporter  (stdout — shows normalised attrs only)
      └──► otlp/openlit   → OpenLIT :4318
                                │
                          ClickHouse DB
```
