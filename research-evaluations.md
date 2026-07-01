# Research: Evaluations for Autonomous Agents

Background research for the **evaluations** thread of *Your Agent Did What?* — how you
know whether an agent's output was any good, how that becomes telemetry, and whether an
eval is a gate or a background quality metric. Companion to `research.md` (forensics) and
`notes.md` (the open questions this answers).

> Method: fan-out research across five angles, primary sources verified directly (GitHub
> via `gh`, arXiv, vendor source code), adversarially cross-checked. Compiled 2026-07-01.
> Single-source and derived claims are flagged inline. This is the durable record behind
> the talk's evaluation claims.

---

## The one-line finding

**OpenTelemetry can already carry an evaluation result — as a log *event*, not a span or
metric — but only four Development-stage attributes, and there is still no standard span
or operation name for "an evaluation happened." The ecosystem all stores the same shape
(a named numeric score, usually a label and a rationale) in incompatible containers, which
is exactly what a normalizer bridges. And the honest hard part isn't the schema — it's
deciding what "good enough" means and trusting the judge.**

---

## 1. The OTel GenAI evaluation convention — it's an *event*

The convention lives inside the GenAI **events** doc, not a standalone page. As of today the
GenAI conventions have **moved out** of the main `open-telemetry/semantic-conventions` repo
into a dedicated repo, `open-telemetry/semantic-conventions-genai`; the old
opentelemetry.io pages and `docs/gen-ai/*.md` are now "moved" stubs (treat the exact
redirect wording as lightly sourced).

**Signal type: a log-based event.** Verbatim from the spec: *"The event name MUST be
`gen_ai.evaluation.result` … SHOULD be parented to [the] GenAI operation span being
evaluated when possible or set `gen_ai.response.id` when span id is not available."*

```
Event: gen_ai.evaluation.result
gen_ai.evaluation.name           string   Required                 Development   e.g. "Relevance", "IntentResolution"
gen_ai.evaluation.score.value    double   Conditionally Required   Development   e.g. 4.0
gen_ai.evaluation.score.label    string   Conditionally Required   Development   e.g. relevant/not_relevant/correct/incorrect/pass/fail
gen_ai.evaluation.explanation    string   Recommended              Development   free-form judge rationale
gen_ai.response.id               string   Recommended              Development   correlation when no span id
error.type                       string   Conditionally Required   Stable        set if the eval operation errored
```

**Verified negatives — do not use:**
- `gen_ai.evaluation.score.units` — not in the registry.
- `gen_ai.evaluation.outcome` — proposed (PRs #3297/#3336) but closed **without merge**.

**Maturity:** every `gen_ai.evaluation.*` attribute is **Development** (only `error.type` is
Stable). Events are noted as not yet available in all language SDKs.

**Provenance & trajectory:**
- Origin: PR #2563 "Gen AI Evaluation Result", merged 2025-08-26; first shipped ~semconv
  **v1.38.0** *(derived from merge-vs-release dates; some blogs say v1.39.0 — not label-confirmed)*.
- **Open, not merged (watch this space):**
  - **PR #185** — adds an evaluation **span** and a well-known `gen_ai.operation.name` value
    for evaluation. Its rationale explicitly cites **ecosystem fragmentation** — e.g.
    OpenSearch's GenAI-observability SDK already invents `gen_ai.operation.name: "evaluation"`.
  - **PR #262** — a `gen_ai.run_guardrail` convention (verdict + enforced action) for the
    inline/guardrail category (§5).

> Talk beat: the *only* merged, standardized eval signal today is the
> `gen_ai.evaluation.result` event, at Development maturity. The eval-**span** and the
> **guardrail** conventions are in-flight — and PR #185 names the exact fragmentation this
> talk is about.

---

## 2. LLM-as-judge — the concept, and why to distrust it

**What it is.** Use a strong LLM to grade another model's or agent's output on open-ended
tasks — a scalable, explainable proxy for human preference. Founding paper: Zheng et al.,
*Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena*, NeurIPS 2023. Three modes:
pairwise, pointwise (score 1–N), reference-guided. Reported agreement with humans:
**"over 80%"** (abstract, canonical-confirmed).

**For agents, judge the trajectory.** Separate judge prompts for (a) final-response quality,
(b) trajectory correctness (the tool-call sequence + outcome), (c) individual-step quality.
Langfuse recommends step-level as the default; G-Eval (Liu et al. 2023) adds chain-of-thought
rubric scoring (Spearman ~0.514 on summarization).

**Known biases** (three names canonical from the paper; exact percentages below are from the
ar5iv mirror — spot-check before quoting digits):
- **Position bias** — favors the first answer (GPT-4 only ~65% consistent under swap).
- **Verbosity bias** — a repetitive-list attack fooled weaker judges ~91% vs ~9% for GPT-4.
- **Self-enhancement bias** — models over-score their own outputs (~10% GPT-4, ~25% Claude-v1).
- **Self-preference (2024, Wataoka et al.)** — judges score *lower-perplexity/more familiar*
  text higher regardless of author; the bias is rooted in familiarity, not self-recognition.

**Building trust.** Validate against a **human-labeled gold set**; report **Cohen's κ**
(corrects for chance) and Spearman, not raw agreement. Mitigate position bias by running each
pairwise comparison **in both orderings and only calling a winner if consistent**. Calibrate
the rubric against human annotations iteratively.

---

## 3. How the ecosystem represents evals — convergent shape, divergent containers

Everyone stores a **numeric score + a name**, and near-universally a **label/category** and a
**free-text rationale**. The divergence is the container — which is the normalizer thesis.

| Product | Container | Score | Label/category | Rationale | Name mechanism |
|---|---|---|---|---|---|
| OpenInference core | span kind `EVALUATOR` | none standardized | none | none | n/a |
| Phoenix (client) | `SpanEvaluations` etc. | `score` | `label` | `explanation` | `eval.<name>.<col>` |
| Langfuse | `Score` entity | `value`/`stringValue` | via `dataType` | `comment` | `name`+`dataType`+`source` |
| OpenLIT | result object | `score` 0..1 | `classification`+`verdict` | `explanation` | eval-type name |
| Braintrust | `scores` map | number 0..1 | (named score) | (reason/metadata) | map key |
| **OTel** | `gen_ai.evaluation.result` event | `.score.value` | `.score.label` | `.explanation` | `.name` |

**Two corrections to common assumptions:**
- OpenInference **core** does *not* define generic `eval.<name>.label/score/explanation`
  span attributes. It defines the span **kind** `openinference.span.kind = "EVALUATOR"`. The
  `eval.<name>.*` naming is a **Phoenix client serialization** convention.
- OpenLIT does **not** (as of the current SDK) emit `gen_ai.eval.*` OTel attributes — negative
  result; its evals live in a result object (`score`/`verdict`/`classification`/`explanation`).

A normalizer's job is to map all of these onto the OTel `gen_ai.evaluation.*` set (name → `.name`,
numeric → `.score.value`, label → `.score.label`, rationale → `.explanation`).

---

## 4. opensearch-project/agent-health — the platform we use

Verified from the repo (`main`, last pushed 2026-06-27; Apache-2.0; ~23★; **Experimental**).

- **What it is:** an open-source AI-agent **evaluation + observability** framework built on
  OpenSearch, explicitly targeting ops/RCA agents among others.
- **How it evaluates:** an LLM judge does **"Golden Path" trajectory comparison** — it scores
  the agent's *actual* trajectory (tool calls + reasoning + final answer) against
  **`expectedOutcomes`** (semantic, not a strict diff), producing `accuracy` (primary,
  drives pass/fail) plus `faithfulness` / `latency_score` / `trajectory_alignment_score`.
  Thresholds live on an evaluator's `ScoringConfig.passThreshold` (0–100).
- **Telemetry in:** consumes OTel GenAI traces (OTLP → Collector → Data Prepper → OpenSearch)
  when the agent config sets `useTraces: true`. Expects root `invoke_agent`, `chat`, and
  `execute_tool` spans with standard `gen_ai.*` attributes — **directly compatible with the
  Quarkus + LangChain4j output** the capybara demo emits.
- **Telemetry out:** emits the **standard** `gen_ai.evaluation.result` event
  (`gen_ai.evaluation.name/score.value/score.label/explanation`) under a `test_suite_run`
  span whose `gen_ai.operation.name = "evaluation"` — i.e. it *is* the PR #185 pattern in the
  wild — plus `test.*` semconv and a few proprietary `agent_health.*` extensions.
- **Integration:** connectors, not an in-process SDK. Our Java agent plugs in over HTTP via
  the **`rest`** connector: agent-health POSTs `{prompt, context, model, tools}` and parses
  `{thinking?, toolCalls:[{name,args,result}], response, runId}`; it injects a W3C
  `traceparent` so the eval and the agent share a trace.
- **Judge without AWS:** the judge router has no native-Anthropic branch, but supports
  `openai-compatible`/`litellm` — so front Anthropic with a **LiteLLM proxy** (or use the
  zero-credential **Demo Judge** for a dry run). Bedrock is only the default, not required.
- **Run locally:** `docker compose up -d` (OpenSearch + Collector :4317/:4318 + Data Prepper),
  `npx @opensearch-project/agent-health` (UI :4001). Needs Docker ≥ 4 GB.

---

## 5. How fast / is it a gate — the practical taxonomy

Three placements, three roles:

| Type | Runs | Blocking? | Role | Typical checks |
|---|---|---|---|---|
| **Offline** | pre-deploy vs curated datasets (CI) | **gate on the DEPLOY** | regression prevention | quality vs reference outputs |
| **Online** | live traffic, async, sampled | **non-blocking** | background quality metric / drift | quality/drift on real traffic |
| **Inline / guardrail** | synchronously in the request path | **gate on the RESPONSE** | real-time enforcement | PII, injection, toxicity, invalid format |

- **Offline (CI gate):** block the release when scores regress below a per-metric `threshold`
  (Braintrust, Langfuse CI/CD experiments, DeepEval `assert_test`).
- **Online (background metric):** continuous, non-blocking, alert on drift; findings feed back
  into the offline datasets — a loop, not independent.
- **Inline / guardrail (response gate):** in-path; a tripped guardrail halts execution and the
  response is never returned (OpenAI Agents SDK tripwires, NeMo Guardrails). For clear-cut,
  high-impact failures — not nuanced quality.

**Latency / cost.** Inline guardrails add latency to *every* request — keep them lightweight;
run in parallel to hide latency, or blocking-first to save cost (prevent the expensive model
from running). Online evals add production cost — **sample**, don't score everything. Offline
is batch, no production overhead.

**"Good" vs "good enough."** A **risk-calibrated product decision**: pass rate need not be 100%
(Hamel Husain); thresholds per use case (Eugene Yan warns generic judges "barely correlate"
with app-specific performance — validate against human ground truth). Operationalized as a
per-metric `threshold` that gates the build.

> Talk framing for the capybara demo: **remediation_safety** is a *gate* (a destructive
> `delete_records` = `fail`), while **root_cause_correctness** is a *background quality metric*
> you improve over time. Same run, two different eval philosophies — that's the trade-off, live.

---

## How this maps onto the talk

| Talk thread | What this research adds |
|---|---|
| Fragmentation → normalize at the edge | Evals converge on *score+name+label+rationale* but in 6 incompatible containers; OTel's is the `gen_ai.evaluation.result` event |
| "Conforms to OTel GenAI" is necessary but not sufficient | Eval is only an *event* today; the eval-span/operation-name (PR #185) and guardrail (PR #262) are unmerged |
| Agents observing agents (kagent, HolmesGPT) | agent-health is one: it reads `gen_ai.*` traces and emits `gen_ai.evaluation.result` back |
| "Why did it do that?" (forensics) | An eval answers "was it *good*?"; forensics answers "*why* did it act?" — different, complementary signals |

---

## Uncertainty & single-source flags

1. **semconv v1.38.0** as first release with `gen_ai.evaluation.result` is derived (merge-vs-release), not label-confirmed.
2. The **"moved to semantic-conventions-genai"** reorg is confirmed by repo structure + a docs banner; exact redirect wording is lightly sourced.
3. **LLM-judge bias percentages** are from the ar5iv mirror; the "over 80%" and the three bias *names* are canonical.
4. **agent-health native-Anthropic judge** does not exist; the confirmed-working no-AWS path is LiteLLM (or Demo Judge). Direct `/v1/messages` use is unconfirmed.
5. **Human-alignment κ ranges** and **guardrail latency budgets** cited are secondary/indicative.

---

## Sources

**OTel semconv (primary):**
- Events + eval convention — https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-events.md
- Attribute registry — https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/registry/attributes/gen-ai.md
- Origin PR #2563 — https://github.com/open-telemetry/semantic-conventions/pull/2563
- PR #185 (eval span/operation) — https://github.com/open-telemetry/semantic-conventions-genai/pull/185
- PR #262 (guardrail/security finding) — https://github.com/open-telemetry/semantic-conventions-genai/pull/262

**LLM-as-judge:**
- Zheng et al. 2023 — https://arxiv.org/abs/2306.05685
- G-Eval (Liu et al. 2023) — https://arxiv.org/abs/2303.16634
- Self-preference bias (Wataoka et al. 2024) — https://arxiv.org/abs/2410.21819

**Ecosystem data models:**
- OpenInference spec — https://github.com/Arize-ai/openinference/blob/main/spec/semantic_conventions.md
- Phoenix `span_evaluations.py` — https://github.com/Arize-ai/phoenix/blob/main/src/phoenix/trace/span_evaluations.py
- Langfuse scores — https://langfuse.com/docs/evaluation/scores/data-model
- OpenLIT evals — https://github.com/openlit/openlit/blob/main/sdk/python/src/openlit/evals/offline.py
- Braintrust logs/scores — https://www.braintrust.dev/docs/reference/api/Logs

**agent-health:**
- https://github.com/opensearch-project/agent-health

**Taxonomy / gates / thresholds:**
- Langfuse — https://langfuse.com/docs/evaluation/overview · CI/CD — https://langfuse.com/docs/evaluation/experiments/experiments-ci-cd
- Braintrust — https://www.braintrust.dev/articles/llm-evaluation-guide
- OpenAI Agents guardrails — https://openai.github.io/openai-agents-python/guardrails/
- NeMo Guardrails — https://docs.nvidia.com/nemo/guardrails/latest/getting-started/4-input-rails/README.html
- Hamel Husain — https://hamel.dev/blog/posts/evals/ · Eugene Yan — https://eugeneyan.com/writing/evals/

**Quarkus + LangChain4j GenAI semconv (for the demo):**
- Quarkus LangChain4j observability — https://docs.quarkiverse.io/quarkus-langchain4j/dev/observability.html
- `SpanChatModelListener.java` — https://github.com/quarkiverse/quarkus-langchain4j/blob/main/core/runtime/src/main/java/io/quarkiverse/langchain4j/runtime/listeners/SpanChatModelListener.java
