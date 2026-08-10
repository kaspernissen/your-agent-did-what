# Resources

Reference material for *Your Agent Did What? Forensic Observability for Systems That Don't Leave Obvious Footprints*.

## The fragmentation problem

- [Five Semantic Conventions, One Config Property: Observing Spring AI with Arconia](https://www.salaboy.com/2026/05/27/five-semantic-conventions-one-config-property-observing-spring-ai-with-arconia/) — Salaboy's walkthrough of the GenAI semantic convention fragmentation problem. Covers five competing conventions (OpenTelemetry, OpenInference, OpenLLMetry, LangSmith, Langfuse) and how Arconia decouples instrumentation from the convention schema, letting you switch backends by setting a single config property instead of changing code. Good framing for "why is this a mess."

## OpenTelemetry GenAI

- [OTel GenAI Semantic Conventions (docs)](https://opentelemetry.io/docs/specs/semconv/gen-ai/) — the official spec for GenAI attributes, spans, metrics, and events.
- [OTel GenAI Semantic Conventions (GitHub source)](https://github.com/open-telemetry/semantic-conventions/tree/main/docs/gen-ai) — the raw source for the conventions, often easier to navigate and ahead of the rendered docs.

## Normalizing at the edge

Two answers to "five conventions for the same span" — one at the collector, one at the SDK.

- [genainormalizerprocessor (source)](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/processor/genainormalizerprocessor) — the collector processor that canonicalizes span attributes from **OpenInference** and **OpenLLMetry** into official OTel GenAI semconv (pins schema v1.40.0). Config key is `gen_ai_normalizer`; **traces only**; no auto-detection (you list the source conventions explicitly). Status: merged, **alpha**. It **ships in the released contrib image** — verified running on `0.158.0`, no `ocb` build needed. Donation [issue #46069](https://github.com/open-telemetry/opentelemetry-collector-contrib/issues/46069) was accepted and closed 1 June 2026. Example renames: `llm.model_name`→`gen_ai.request.model`, `llm.token_count.prompt`→`gen_ai.usage.input_tokens`, `openinference.span.kind`/`traceloop.span.kind`→`gen_ai.operation.name`.
- [Donation discussion (issue #46069)](https://github.com/open-telemetry/opentelemetry-collector-contrib/issues/46069) — the proposal to donate it to contrib. Code owners: @TylerHelmuth, @kylehounslow.
- [Arconia](https://arconia.io) ([GitHub](https://github.com/arconia-io), [docs](https://docs.arconia.io)) — a Java / Spring Boot toolkit that decouples Spring AI instrumentation from the convention schema. Flip `arconia.observations.conventions.opentelemetry.ai.flavor` between `opentelemetry` / `openlit` / `openllmetry` / `langsmith` (OpenInference via a dependency swap) and the *same* spans re-emit under that schema — no code change. By Thomas Vitale. Base demo to fork: [salaboy/observing-ai](https://github.com/salaboy/observing-ai) (sibling modules per convention). Pinned in the demo: Arconia 0.27.1, Spring AI 2.0.0-M5, Spring Boot 4.0.5, Java 21.

## Competing / framework conventions

- [OpenInference](https://github.com/Arize-ai/openinference) (Arize) — instrumentation conventions and SDKs for LLM/agent observability.
  - [OpenInference spec](https://arize-ai.github.io/openinference/spec/) — the attribute and span conventions in detail.
- [OpenLLMetry](https://github.com/traceloop/openllmetry) (Traceloop) — OpenTelemetry-based instrumentation for LLM apps with its own attribute conventions.
- [Langfuse](https://langfuse.com/) — open-source LLM engineering / observability platform.
  - [Langfuse (GitHub)](https://github.com/langfuse/langfuse) — source repo.
- [LangChain](https://www.langchain.com/) — the agent/LLM framework; relevant for framework-specific instrumentation and LangSmith conventions.

## Visualization & backends (where GenAI traces go)

The "what can I actually look at this in" layer — see `landscape.md` for the analysis and the `demos/` harness for a runnable comparison.

- [Jaeger](https://www.jaegertracing.io/) — generic OTLP-native trace viewer (CNCF, graduated). The baseline: a GenAI trace in a tool with *no* GenAI awareness. **v1 reached EOL 2025-12-31**; v2 is rebuilt on the OTel Collector. See its [roadmap](https://www.jaegertracing.io/roadmap/) and the GenAI epics ([#7827](https://github.com/jaegertracing/jaeger/issues/7827), [#8416](https://github.com/jaegertracing/jaeger/issues/8416)).
- [Arize Phoenix](https://github.com/Arize-ai/phoenix) — OSS, GenAI-native, **OpenInference-native**. Renders OTel-GenAI-semconv (`gen_ai.*`) spans as plain spans — fragmentation made visible. ([Translating conventions](https://arize.com/docs/phoenix/tracing/concepts-tracing/translating-conventions).)
- [OpenLIT](https://docs.openlit.io/) — OSS, OTel-semconv-native GenAI dashboard *and* an instrumentation SDK (`openlit.init()`) that auto-instruments the Anthropic SDK and emits `gen_ai.*`.
- [OpenSearch Agent Traces](https://docs.opensearch.org/latest/observing-your-data/agent-traces/agent-tracing/) — OTel-GenAI-semconv-native agent-trace UI (categorizes spans by `gen_ai.operation.name`). Ingests via OTel Collector → **Data Prepper** → OpenSearch (no direct OTLP). UI is RFC-stage in OSS OpenSearch ([#11345](https://github.com/opensearch-project/OpenSearch-Dashboards/issues/11345)), live on AWS.
- [Dash0](https://www.dash0.com/) — the vendor path in the demos (OTLP exporter from the collector).

## Evaluation tooling

- [OpenSearch Agent Health](https://github.com/opensearch-project/agent-health) — OSS
  (Apache-2.0) agent **evaluation and observability** framework: an LLM judge scoring agent
  runs against a **"Golden Path" trajectory**, batch experiments, run-to-run comparison, and
  OTel traces stored locally or in OpenSearch. The closest thing to a shipped implementation
  of the gold-set mitigation the talk recommends for judge bias. v0.5.2, actively developed,
  SDK marked **Experimental**. Its
  [instrumentation guide](https://github.com/opensearch-project/agent-health/blob/main/docs/INSTRUMENT_WITH_OTEL.md)
  asks for the GenAI conventions — and is itself a live example of revision drift: it
  specifies **`gen_ai.system`**, which is not in the current registry (`gen_ai.provider.name`
  replaced it), and **`gen_ai.tool.call_id`**, where the registry defines
  `gen_ai.tool.call.id`. Checked 2026-08-10.
- Its [Claude Code telemetry guide](https://github.com/opensearch-project/agent-health/blob/main/docs/CLAUDE_CODE_TELEMETRY.md)
  documents the opt-in content switches for a coding agent — `OTEL_LOG_USER_PROMPTS`,
  `OTEL_LOG_TOOL_DETAILS`, `OTEL_LOG_TOOL_CONTENT` — the same "the forensic content is a
  flag you throw" shape as `include-tool-arguments` in Demo 1, one layer closer to home.

## CNCF agent tooling (reference)

- [kagent](https://github.com/kagent-dev/kagent) — agents as first-class Kubernetes workloads; agent lifecycle as a custom resource (CNCF Sandbox).
- [HolmesGPT](https://github.com/robusta-dev/holmesgpt) — agentic SRE troubleshooter that reads OTel data, calls observability tools over MCP, escalates to humans.
- [agentgateway](https://agentgateway.dev/) — the tool-call data plane between agents and tools; a natural enforcement + observability point.
