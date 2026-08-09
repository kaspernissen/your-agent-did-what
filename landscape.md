# The Visualization & Normalization Landscape

Talk content for the "where do GenAI traces actually go, and how do you stop the fragmentation" portion. Companion to `resources.md` (links), `research.md` (forensics), and the runnable `demos/` harness. Findings here are from primary-source research on 2026-06-07; verify versions before they age.

---

## 1. The backend spectrum — same trace, very different views

Once you have GenAI traces flowing, "observability" splits along two axes. Where a tool sits decides what it can show you.

**Axis A — generic vs. GenAI-native:**
- **Generic trace viewers** (Jaeger, Grafana/Tempo) show spans as plumbing. A `chat` span is just a span; `execute_tool` is just a span. No token/cost/model panels, no prompt/completion rendering. This is the "164 spans named POST" experience from the PlatformCon deck, live.
- **GenAI-native UIs** (Phoenix, OpenLIT, Langfuse, OpenSearch Agent Traces) understand LLM semantics — they classify spans as LLM/tool/agent/retrieval, render messages, sum tokens and cost.

**Axis B — which convention the GenAI-native UI is native to:**
- **OTel-semconv-native** (OpenLIT, OpenSearch Agent Traces, Dash0; Langfuse maps it): light up on `gen_ai.*`.
- **OpenInference-native** (Arize Phoenix): lights up on OpenInference attributes. Feed it OTel `gen_ai.*` and it *accepts and stores* the spans but renders them as **plain spans** — no LLM views. Source: Phoenix "Translating Conventions" docs.

**The teachable moment:** instrument one app once with OTel GenAI semconv, fan it out, and the differences you see are about the *viewer*, not the data. Phoenix looking bland on a `gen_ai.*` trace is not a bug — it's the fragmentation tax, visible on stage. (The `demos/backends` harness does exactly this.)

### Backend cheat-sheet (verified 2026-06-07)

| Tool | Kind | Native convention | Ingest | Weight |
|---|---|---|---|---|
| Jaeger v2 | generic viewer | n/a (OTLP) | OTLP native (4317/4318) | light (1 container) |
| Arize Phoenix | GenAI-native | OpenInference | OTLP (UI+HTTP on 6006, gRPC 4317) | light |
| OpenLIT | GenAI-native | OTel semconv | OTLP (bundled collector → ClickHouse) | medium (+ClickHouse) |
| Langfuse v3 | LLM platform | maps OTel/OpenInference/OpenLLMetry | OTLP **HTTP only**, `/api/public/otel`, Basic auth | heavy (PG+CH+Redis+MinIO+web+worker) |
| OpenSearch Agent Traces | GenAI-native | OTel semconv (`gen_ai.*`) | OTel Collector → **Data Prepper** → OpenSearch (no direct OTLP) | heavy (+Data Prepper, ~4GB, UI RFC-stage in OSS) |
| Dash0 | vendor | OTel semconv | OTLP exporter | n/a (SaaS) |

---

## 2. Normalizing at the edge — two answers to "five conventions, one span"

The fragmentation is real and not going away (OTel, OpenInference, OpenLLMetry, LangSmith, Langfuse all optimize for different things — Salaboy's point: legitimate differences, not naming preferences). Two places to fix it:

### At the collector — `gen_ai_normalizer` processor
- Canonicalizes **OpenInference** and **OpenLLMetry** span attributes → official OTel GenAI semconv (pins schema v1.40.0 on output).
- Config key `gen_ai_normalizer`; **traces only**; **no auto-detection** (you list `openinference`/`openllmetry` explicitly, in order); per-source `remove_originals` / `overwrite`; supports custom `mappings` + `value_mappings`.
- Example renames: `llm.model_name → gen_ai.request.model`, `llm.token_count.prompt → gen_ai.usage.input_tokens`, `openinference.span.kind`/`traceloop.span.kind → gen_ai.operation.name`. ~34 mappings across the two built-in profiles.
- **Status:** merged into collector-contrib, **alpha**, sponsor @TylerHelmuth, code owners @kylehounslow / @vamsimanohar / @ps48. **It ships in the released contrib image** — verified running on `0.158.0` (2026-08-09), so no `ocb` build is needed. The donation issue #46069 was accepted and closed **1 June 2026**.
- **The pitch:** developers instrument with whatever their framework emits; the *platform* normalizes centrally in the pipeline. This is the literal fix for "Phoenix-native app, OTel-native backend" mismatch — and the thing being donated to contrib right now (issue #46069), so a talk raises it at the right moment.

### At the SDK — Arconia (Spring AI / Java)
- Decouples Spring AI's *instrumentation* from the *schema*. Flip one property:
  `arconia.observations.conventions.opentelemetry.ai.flavor = opentelemetry | openlit | openllmetry | langsmith`
  and the same instrumented spans re-emit under that vendor's attribute names. OpenInference is selected by swapping the dependency (`arconia-openinference-ai-semantic-conventions`), no flavor line.
- Companion knobs: `...ai.capture-content` (`none`/`span-events`/`span-attributes`/`true`), `...ai.include-tool-definitions`, `...ai.include-tool-call-content` — i.e. the opt-in forensic content is a config switch, which ties straight to `research.md`.
- Stack: Java 21, Spring Boot 4.0.5, Spring AI 2.0.0-M5, Arconia 0.27.1. By Thomas Vitale. Base: `salaboy/observing-ai`.
- **The contrast worth drawing:** normalizer fixes it *downstream* (you don't touch apps, works for any language, central policy); Arconia fixes it *upstream* (clean data at the source, but per-framework and Java-only today). Both land on OTel semconv as the target. Platforms will likely want the collector approach; greenfield Spring shops get it for free with Arconia.

---

## 3. Jaeger roadmap — "OTel is the substrate," proven by the oldest tracer

The single strongest external proof point for the talk's thesis.

**Concrete, shipped facts:**
- **Jaeger v2 is built on the OpenTelemetry Collector.** Verbatim (CNCF, "Jaeger at 10," Shkuro & Kowall, 2025-09-01): *"Jaeger v2 is built on the OpenTelemetry Collector, leveraging its flexible, extensible pipeline,"* and *"natively understands OTLP end to end, eliminating the need for translation layers."* The canonical, CNCF-graduated tracing project didn't bolt on OTLP — it re-platformed its entire backend onto the Collector.
- **Jaeger v1 reached EOL 2025-12-31.** No new v1 releases in 2026; the project says migrate to v2.
- Storage is moving to a **V2 Storage API** that "natively supports the OpenTelemetry data model (OTLP)," plus first-class ClickHouse support.

**Open roadmap epics (directional, not shipped — say so on stage):**
- **"GenAI Observability" (#8416, opened 2026-04-21):** position Jaeger as "the observability backbone for GenAI applications." Sub-items: PII sanitization and payload **retention tiering implemented as hooks in the *collector pipeline***; an ingestion endpoint for third-party **eval scores** linked to traces; **prompt/model version as first-class queryable tags**; **agentic DAG visualization** for cyclic/self-correcting patterns; **A/B trace comparison**.
- **"GenAI Integration" (#7827, opened 2026-01-02, in progress):** an LLM **trace-investigation agent** in the UI — four levels from "free-form question about a single trace" to "free-form investigation," via a Jaeger **MCP server**.

**Talk-ready framings:**
1. *Even a 10-year-old tracing tool now treats the OTel Collector as its foundation.* GenAI features (PII redaction, payload tiering) are being designed as collector-pipeline hooks — not a Jaeger-specific layer. The substrate is the Collector.
2. *The tracing backend itself is going agentic:* Jaeger's roadmap includes an agent that forensically investigates other agents' traces. Agent observability and agentic observability converging.
3. **Honesty caveat:** the GenAI epics are open proposals from early-to-mid 2026 with no milestones — concrete *direction*, not concrete *features*. Don't overstate. (And: neither epic yet commits to consuming the OTel `gen_ai.*` semantic conventions *by name* — treat "Jaeger renders GenAI semconv" as forward-looking.)

---

## 4. How this maps to the talk

- The **backend spectrum** is the payoff of the demos: instrument once, see five renderings.
- **Normalization** (genai_normalizer + Arconia) is the platform answer to fragmentation — and both are live, donate-able, demo-able *now*.
- **Jaeger's roadmap** is the third-party validation of "OTel is the substrate" — and a bridge into the forensics/agentic-observability close.
