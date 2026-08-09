# Arconia Convention-Switching Demo

> **Not on the talk's critical path.** Arconia is a **shout-out** in the talk (beat 5), not
> a demo we run — it is how the Spring community reaches the same target the collector
> processor reaches downstream, by [Thomas Vitale](https://github.com/ThomasVitale). This
> directory is kept because its captured flavor-diff data is real and referenced in
> `demos/ANALYSIS.md`, but nothing in the 30-minute talk depends on running it and it is
> not maintained to the standard of Demos 1 and 2.

Demonstrates how Arconia + Spring AI can re-emit GenAI spans under different
observability conventions by flipping a single application property — no code change required.

Based on [salaboy/observing-ai](https://github.com/salaboy/observing-ai) by Thomas Vitale.

## Exact versions used

| Component         | Version    |
|-------------------|------------|
| Spring Boot       | 4.0.5      |
| Spring AI         | 2.0.0-M5   |
| Arconia           | 0.27.1     |
| Java              | 21         |

## Prerequisites

- **JDK 21** (required; the `./mvnw` wrapper downloads Maven automatically)
- Docker (for the local OTLP debug collector)
- An Anthropic API key

## The ONE-property flip

Edit `src/main/resources/application.properties`:

```properties
arconia.observations.conventions.opentelemetry.ai.flavor=opentelemetry
```

Valid values (all require **`arconia-opentelemetry-ai-semantic-conventions`** on the
classpath — note the `-ai-`; the OTel-only `arconia-opentelemetry-semantic-conventions`
artifact does NOT switch flavors):

| Value           | Convention emitted                                         |
|-----------------|------------------------------------------------------------|
| `opentelemetry` | OTel GenAI semconv — `gen_ai.*` + `gen_ai.provider.name`   |
| `openlit`       | OpenLIT — `gen_ai.*` + `gen_ai.system`, `gen_ai.request.is_stream` |
| `openllmetry`   | OpenLLMetry — `gen_ai.*` + `gen_ai.system` + `traceloop.*` on workflow spans |
| `langsmith`     | LangSmith convention                                       |

> The `-ai-` artifact makes `capture-content` an **enum**, not a boolean — use
> `arconia.observations.conventions.opentelemetry.ai.capture-content=SPAN_ATTRIBUTES`
> (values: `NONE` / `SPAN_ATTRIBUTES` / `SPAN_EVENTS`), otherwise the app fails to start.
> Verified live: flipping the property changes the emitted attribute keys (see `../ANALYSIS.md`).

**OpenInference** is a dependency swap, not a property flip: replace
`arconia-opentelemetry-ai-semantic-conventions` with
`arconia-openinference-ai-semantic-conventions` in `pom.xml`.

## Property names (verified against cloned source)

The flavor property name used here is the **real** name from the upstream module:

```
arconia.observations.conventions.opentelemetry.ai.flavor
```

The OTLP trace endpoint is set via the Spring Boot native property:

```
management.opentelemetry.tracing.export.otlp.endpoint=http://localhost:4318/v1/traces
```

Note: `arconia.otel.exporter.otlp.endpoint` does **not** exist in Arconia 0.27.x.
The collector receives traces at the standard `/v1/traces` path.

## Controller endpoint

```
POST /api/chat?prompt=<your question>
```

Returns JSON: `{"response": "<model reply>"}`

Example:
```bash
curl -X POST "http://localhost:8080/api/chat?prompt=Hello%2C+what+can+you+help+with%3F"
```

## Running locally

### 1. Start the debug OTLP collector

```bash
docker run --rm -p 4318:4318 \
  -v "$PWD/collector-config.yaml:/etc/otelcol/config.yaml:ro" \
  otel/opentelemetry-collector:0.114.0 \
  --config /etc/otelcol/config.yaml
```

The collector prints every received span to stdout with all attribute names visible.

### 2. Start the application

```bash
export ANTHROPIC_API_KEY=sk-ant-...
./mvnw spring-boot:run
```

### 3. Send a request

```bash
curl -X POST "http://localhost:8080/api/chat?prompt=List+a+few+Spring+projects"
```

### 4. Read the span attributes

In the collector's stdout you will see `gen_ai.*` attributes (with the default
`opentelemetry` flavor). Change the flavor property and restart to observe how
the attribute names change.

### 5. Switch convention

Edit `src/main/resources/application.properties`, change the flavor value
(e.g. to `openllmetry`), restart the app, send another request, and compare
the attribute names in the collector output.

## Build only (no API key needed)

```bash
./mvnw -q -DskipTests package
```

Produces `target/arconia-anthropic-demo-0.0.1-SNAPSHOT.jar`.
