# Research — Your Agent Did What?

Everything the talk is sourced from, in one file: the forensics research, the evaluations
research, the backend and normalization landscape, the state of the standards as we last
checked them, and the link list.

> **Precedence.** Where this document and [`demos/ANALYSIS.md`](demos/ANALYSIS.md) disagree,
> **ANALYSIS.md wins.** It is the measured record — spans captured from real runs of the
> demo. This file is research and reading, some of it gathered before the demo existed.

> **Dates matter here.** Every claim about a version, a release or a repository is true as of
> the date attached to it. This is a fast-moving area and several of these facts have already
> changed once during the writing of the talk.

## Contents

1. [Forensics — what telemetry can and cannot reconstruct](#forensics--what-telemetry-can-and-cannot-reconstruct)
2. [Evaluations — judging a run you cannot replay](#evaluations--judging-a-run-you-cannot-replay)
3. [The visualization and normalization landscape](#the-visualization-and-normalization-landscape)
4. [Standards and stacks, as last checked](#standards-and-stacks-as-last-checked)
5. [Resources](#resources)

---

## Forensics — what telemetry can and cannot reconstruct

> **Research notes.** Background reading gathered before the demo existed. Still the sourcing behind several slides, but [`demos/ANALYSIS.md`](demos/ANALYSIS.md) is the measured record and wins wherever the two disagree.

Background research for the forensics half of *Your Agent Did What?* — what telemetry you actually need to reconstruct what an agent did when something goes wrong, and where today's GenAI observability stack falls short for post-incident forensics on non-deterministic systems.

Method: fan-out web search across five angles → 21 sources fetched → 100 claims extracted → 25 highest-value claims verified with 3-vote adversarial checking (a claim needs 2 of 3 votes to survive). 21 confirmed, 4 killed. Full source list and the verification caveat are at the bottom.

---

### The one-line finding

**The OTel GenAI conventions can already name what an agent did. They cannot, by default, tell you *what it did with what arguments, what came back, or why it chose to.* The structural spans exist; the forensic content is opt-in and off by default; and there is no schema slot at all for the decision itself.**

That is the forensic gap in one sentence, and it's the natural next slide after your pizza-shop trace ("the data being present is not the same as the data being legible"). The PlatformCon deck shows the signal is buried. This shows that for forensics, the signal you most need was often never recorded.

---

### What the conventions give you — and what they withhold

**The spans exist and are distinct from inference.** OTel GenAI defines `create_agent`, `invoke_agent`, `invoke_workflow`, and `execute_tool` as first-class spans, separate from the underlying model-inference span. So a conforming trace *does* show you the shape of the run: an agent was created, a workflow ran, a tool executed. (High confidence, 3-0. Source: OTel GenAI spans spec.)

**But the forensic payload is opt-in, off by default.** The content you need to reconstruct an incident — tool-call arguments, tool results, input/output messages, system instructions — is gated behind opt-in flags. The spec explicitly says instrumentation **SHOULD NOT** capture this by default (privacy and payload-size reasons). So the out-of-the-box trace tells you *a tool ran*. It does not tell you it ran `DROP TABLE`, what the database returned, what prompt led there, or what the agent was asked. (High confidence, 3-0.)

> Talk framing: this is the "your agent deleted a database" moment. With default instrumentation you can prove the `execute_tool` span fired. You cannot prove what it executed. The footprint exists; the footprint is empty.

**There is no decision-provenance primitive at all.** Across OTel GenAI *and* the rest of the ecosystem (LangSmith, Langfuse, Datadog, LangGraph), there is no schema-level attribute for *why* the agent chose what it chose. The closest thing is a reasoning-*token-count* — a number, not the reasoning. Span message "parts" are typed only as text or tool_call; there is no provenance part. And every GenAI attribute is still **Development-stage** — subject to breaking change. (High confidence, 3-0. Sources: OTel attribute registry; arXiv 2603.21692.)

> This is your "Why did it do that?" property (PlatformCon slide 7, property 4) expressed as a concrete schema gap: there is nowhere in the standard to *put* the why, even if you captured it.

---

### Why you can't just replay it

**Faithful replay is fundamentally limited.** Two independent reasons:

1. **The assembled context window is not persisted.** The exact bytes the model saw — after retrieval, memory, tool results, and context assembly — are typically not stored. Without that input, you can't deterministically rerun the step.
2. **Non-determinism diverges the trace anyway.** Sampling, context-assembly order, and timing mean a rerun produces a *different* trace, not the same one.

The consequence is the load-bearing point for the talk: **reasoning provenance cannot, in general, be reconstructed after the fact — it has to be captured at execution time.** If you didn't record *why* when it happened, re-running won't recover it. (Confirmed 3-0; medium confidence — rests substantially on a single recent preprint, 2603.21692, plus the OpenClaw paper.)

> This is the evidence behind "Reconstructing *why* is the new MTTR — you're interrogating a system you can't replay." The research says: you literally cannot replay it, so the only forensic strategy is capture-at-runtime. That reframes instrumentation from "nice to have" to "the only chance you get."

---

### What the research community is building (the shape of an answer)

Three primary sources converge on the same structural move: **separate the thought from the action, and link them with provenance edges.**

- **AgentSec dataset** models incidents as `decision_traces` (with `selected_option` and `resulting_actions`) kept *distinct* from `tool_call_event` objects, joined by a `triggered` edge in a provenance graph (`used_by` / `triggered` / `derived_from` / `caused`). It explicitly captures the point that, unlike rule-based software, an agent's tool choice is LLM/context/environment-driven. (High confidence, 3-0.)
- **OpenClaw** proposes a five-plane forensic taxonomy — Brain / DNA / Memory / Ears-Mouth / Hands — that separates reasoning from action, and pairs each `toolCall` (name, id, args) with a `toolResult` (toolCallId, isError, timestamp) in session logs. The paper states plainly that **systematic agentic forensics is largely unexplored**. (High confidence, 3-0.)
- **AgentRR** (record-and-replay) logs *actions plus environment state at every step*, at the GUI or API layer, and uses an "experience abstraction" to decouple intelligence from execution — isolating creative LLM output to designated decision nodes. (High confidence, 3-0.)

> The common thread — decision record + action record + an edge between them — is exactly what the OTel GenAI conventions don't yet have a place for. That's the gap to point the SIG at, and it complements your genainormalizer story: normalizing names is necessary but not sufficient if the thing you most need (the decision) has no field.

---

### What did *not* hold up (intellectual honesty for the stage)

Four claims were killed under adversarial verification. Worth knowing so you don't repeat them:

- **"Reasoning-effort token count is the only reasoning signal."** (1-2) Overstated as phrased — the broader point survives in the confirmed findings, but the narrow claim got refuted.
- **"You can recover decision provenance from the model's chain-of-thought / 'thinking' blocks."** (1-2) **Killed — and this one matters.** Don't claim you can reconstruct *why* from the model's self-narrated reasoning. Thinking blocks are not a reliable provenance record; treat them as output, not audit trail.
- **"Agent-mediated execution / the extra abstraction layer is *the* core obstacle to forensics."** (1-2) Refuted as overstated — non-determinism and missing capture matter more than the abstraction layer per se.
- **"You need a three-layer independent interception harness (MCP stdio proxy + shell DEBUG trap + filesystem watcher) to reconcile reported vs. actual actions."** (1-2) Interesting and intuitively right (the agent may report one action and perform another), but it rests on a single preprint and was refuted as a general requirement. Use as a "some researchers propose…", not a claim.

> The second one is a useful slide on its own: the obvious answer — "just log the chain-of-thought" — does not actually give you forensics. That's a satisfying myth to puncture.

---

### How this maps onto the talk

| PlatformCon thread | What this research adds |
|---|---|
| Pizza-shop trace: signal buried in 290 spans | …and the forensic signal is often *not captured at all* — args/results/prompt are off by default |
| "Reconstructing *why* is the new MTTR" | You can't replay it; provenance must be captured at runtime or it's gone |
| Property 4: "Why did it do that?" | No schema primitive exists for the decision — it's a standards gap, not just a tooling gap |
| genainormalizer normalizes names at the edge | Necessary but insufficient: normalizing names doesn't create the missing decision field |
| Five competing conventions | All five share the same blind spot on decision provenance — fragmentation isn't the only problem |

---

### Sources

**Primary / standards (verify these directly before citing on stage — see caveat):**
- OTel GenAI agent spans — https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/
- OTel GenAI spans (opt-in content rule) — https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/
- OTel GenAI attribute registry (Development stage) — https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/
- AgentRR (record-and-replay), arXiv:2505.17716 — https://arxiv.org/html/2505.17716v1
- OpenClaw / five-plane forensic taxonomy, arXiv:2604.05589 — https://arxiv.org/html/2604.05589v1 · https://arxiv.org/abs/2604.05589
- Reasoning provenance for autonomous agents, arXiv:2603.21692 — https://arxiv.org/pdf/2603.21692
- AgentSec dataset — https://github.com/yasserhmimou9/AgentSec-Dataset
- MDPI Data, decided-vs-executed provenance — https://www.mdpi.com/2306-5729/11/4/66

**Practitioner / blog (context, lower weight):**
- OpenInference vs OTel agent tracing — https://niteagent.com/blog/2026-05-25-openinference-vs-otel-agent-tracing/
- Minimum viable audit trail (Armo) — https://www.armosec.io/blog/minimum-viable-audit-trail/
- AI agent audit trail + SIEM (Kiteworks) — https://www.kiteworks.com/regulatory-compliance/ai-agent-audit-trail-siem-integration/
- OTel GenAI semconv overview (Greptime) — https://greptime.com/blogs/2026-05-09-opentelemetry-genai-semantic-conventions
- "When AI lies to its own logs" (Fortuna) — https://andreafortuna.org/2026/05/04/when-ai-lies-to-its-own-logs-forensic-readiness/
- Missing primitives for trustworthy AI (Sakura Sky) — https://www.sakurasky.com/blog/missing-primitives-for-trustworthy-ai-part-8/
- Deterministic replay for non-deterministic agents (tianpan.co) — https://tianpan.co/blog/2026-04-12-deterministic-replay-debugging-non-deterministic-ai-agents
- Checkpoint-based state replay with LangGraph (dev.to) — https://dev.to/sreeni5018/debugging-non-deterministic-llm-agents-implementing-checkpoint-based-state-replay-with-langgraph-5171
- LLM observability for multi-agent systems (Medium) — https://medium.com/@arpitchaukiyal/llm-observability-for-multi-agent-systems-part-1-tracing-and-logging-what-actually-happened-c11170cd70f9
- Replaying agent decisions for forensics (LoginRadius) — https://www.loginradius.com/blog/engineering/replay-ai-agent-decisions-forensics
- Beyond logs: agent replay (HuggingFace) — https://huggingface.co/blog/Spectorfrost123/beyond-logs-agent-replay
- Production AI agent observability (Clype) — https://www.clype.io/blog/production-ai-agents-observability

---

### Caveat — verify before you cite on stage

This report was synthesized from automated search + adversarial verification, which reduces but does not eliminate two risks:

1. **Recency / single-source weakness.** Several load-bearing claims (replay impossibility, five-plane taxonomy, decision-provenance gap) rest on very recent arXiv preprints (2603.21692, 2604.05589, 2505.17716) — sometimes a single one. Preprints aren't peer-reviewed. **Open the arXiv papers yourself and confirm the specific claims before putting them on a slide**, especially the "replay is fundamentally impossible" framing.
2. **The OTel spec claims are the safest.** The "forensic content is opt-in / SHOULD NOT capture by default" and "no decision-provenance primitive / Development-stage" findings are checkable directly against the spec pages above, and they're the strongest material for the talk. Lead with those; treat the academic framing as supporting color.

---

## Evaluations — judging a run you cannot replay

> **Research notes.** Background reading gathered before the demo existed. Still the sourcing behind several slides, but [`demos/ANALYSIS.md`](demos/ANALYSIS.md) is the measured record and wins wherever the two disagree.

Background research for the **evaluations** thread of *Your Agent Did What?* — how you
know whether an agent's output was any good, how that becomes telemetry, and whether an
eval is a gate or a background quality metric. Companion to `research.md` (forensics) and
`notes.md` (the open questions this answers).

> Method: fan-out research across five angles, primary sources verified directly (GitHub
> via `gh`, arXiv, vendor source code), adversarially cross-checked. Compiled 2026-07-01.
> Single-source and derived claims are flagged inline. This is the durable record behind
> the talk's evaluation claims.

---

### The one-line finding

**OpenTelemetry can already carry an evaluation result — as a log *event*, not a span or
metric — but only four Development-stage attributes, and there is still no standard span
or operation name for "an evaluation happened." The ecosystem all stores the same shape
(a named numeric score, usually a label and a rationale) in incompatible containers, which
is exactly what a normalizer bridges. And the honest hard part isn't the schema — it's
deciding what "good enough" means and trusting the judge.**

---

### 1. The OTel GenAI evaluation convention — it's an *event*

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

### 2. LLM-as-judge — the concept, and why to distrust it

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

### 3. How the ecosystem represents evals — convergent shape, divergent containers

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

### 4. opensearch-project/agent-health — the platform we use

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

### 5. How fast / is it a gate — the practical taxonomy

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

### How this maps onto the talk

| Talk thread | What this research adds |
|---|---|
| Fragmentation → normalize at the edge | Evals converge on *score+name+label+rationale* but in 6 incompatible containers; OTel's is the `gen_ai.evaluation.result` event |
| "Conforms to OTel GenAI" is necessary but not sufficient | Eval is only an *event* today; the eval-span/operation-name (PR #185) and guardrail (PR #262) are unmerged |
| Agents observing agents (kagent, HolmesGPT) | agent-health is one: it reads `gen_ai.*` traces and emits `gen_ai.evaluation.result` back |
| "Why did it do that?" (forensics) | An eval answers "was it *good*?"; forensics answers "*why* did it act?" — different, complementary signals |

---

### Uncertainty & single-source flags

1. **semconv v1.38.0** as first release with `gen_ai.evaluation.result` is derived (merge-vs-release), not label-confirmed.
2. The **"moved to semantic-conventions-genai"** reorg is confirmed by repo structure + a docs banner; exact redirect wording is lightly sourced.
3. **LLM-judge bias percentages** are from the ar5iv mirror; the "over 80%" and the three bias *names* are canonical.
4. **agent-health native-Anthropic judge** does not exist; the confirmed-working no-AWS path is LiteLLM (or Demo Judge). Direct `/v1/messages` use is unconfirmed.
5. **Human-alignment κ ranges** and **guardrail latency budgets** cited are secondary/indicative.

---

### Sources

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

---

## The visualization and normalization landscape

> **Research notes.** Background reading gathered before the demo existed. Still the sourcing behind several slides, but [`demos/ANALYSIS.md`](demos/ANALYSIS.md) is the measured record and wins wherever the two disagree.

Talk content for the "where do GenAI traces actually go, and how do you stop the fragmentation" portion. Companion to `resources.md` (links), `research.md` (forensics), and the runnable `demos/` harness. Findings here are from primary-source research on 2026-06-07; verify versions before they age.

---

### 1. The backend spectrum — same trace, very different views

Once you have GenAI traces flowing, "observability" splits along two axes. Where a tool sits decides what it can show you.

**Axis A — generic vs. GenAI-native:**
- **Generic trace viewers** (Jaeger, Grafana/Tempo) show spans as plumbing. A `chat` span is just a span; `execute_tool` is just a span. No token/cost/model panels, no prompt/completion rendering. This is the "164 spans named POST" experience from the PlatformCon deck, live.
- **GenAI-native UIs** (Phoenix, OpenLIT, Langfuse, OpenSearch Agent Traces) understand LLM semantics — they classify spans as LLM/tool/agent/retrieval, render messages, sum tokens and cost.

**Axis B — which convention the GenAI-native UI is native to:**
- **OTel-semconv-native** (OpenLIT, OpenSearch Agent Traces, Dash0; Langfuse maps it): light up on `gen_ai.*`.
- **OpenInference-native** (Arize Phoenix): lights up on OpenInference attributes. Feed it OTel `gen_ai.*` and it *accepts and stores* the spans but renders them as **plain spans** — no LLM views. Source: Phoenix "Translating Conventions" docs.

**The teachable moment:** instrument one app once with OTel GenAI semconv, fan it out, and the differences you see are about the *viewer*, not the data. Phoenix looking bland on a `gen_ai.*` trace is not a bug — it's the fragmentation tax, visible on stage. (A fan-out harness that did exactly this was removed on 2026-08-11; the capture it produced is in `demos/ANALYSIS.md` under *Superseded and historical*.)

#### Backend cheat-sheet (verified 2026-06-07)

| Tool | Kind | Native convention | Ingest | Weight |
|---|---|---|---|---|
| Jaeger v2 | generic viewer | n/a (OTLP) | OTLP native (4317/4318) | light (1 container) |
| Arize Phoenix | GenAI-native | OpenInference | OTLP (UI+HTTP on 6006, gRPC 4317) | light |
| OpenLIT | GenAI-native | OTel semconv | OTLP (bundled collector → ClickHouse) | medium (+ClickHouse) |
| Langfuse v3 | LLM platform | maps OTel/OpenInference/OpenLLMetry | OTLP **HTTP only**, `/api/public/otel`, Basic auth | heavy (PG+CH+Redis+MinIO+web+worker) |
| OpenSearch Agent Traces | GenAI-native | OTel semconv (`gen_ai.*`) | OTel Collector → **Data Prepper** → OpenSearch (no direct OTLP) | heavy (+Data Prepper, ~4GB, UI RFC-stage in OSS) |
| Dash0 | vendor | OTel semconv | OTLP exporter | n/a (SaaS) |

---

### 2. Normalizing at the edge — two answers to "five conventions, one span"

The fragmentation is real and not going away (OTel, OpenInference, OpenLLMetry, LangSmith, Langfuse all optimize for different things — Salaboy's point: legitimate differences, not naming preferences). Two places to fix it:

#### At the collector — `gen_ai_normalizer` processor
- Canonicalizes **OpenInference** and **OpenLLMetry** span attributes → official OTel GenAI semconv (pins schema v1.40.0 on output).
- Config key `gen_ai_normalizer`; **traces only**; **no auto-detection** (you list `openinference`/`openllmetry` explicitly, in order); per-source `remove_originals` / `overwrite`; supports custom `mappings` + `value_mappings`.
- Example renames: `llm.model_name → gen_ai.request.model`, `llm.token_count.prompt → gen_ai.usage.input_tokens`, `openinference.span.kind`/`traceloop.span.kind → gen_ai.operation.name`. ~34 mappings across the two built-in profiles.
- **Status:** merged into collector-contrib, **alpha**, sponsor @TylerHelmuth, code owners @kylehounslow / @vamsimanohar / @ps48. **It ships in the released contrib image** — verified running on `0.158.0` (2026-08-09), so no `ocb` build is needed. The donation issue #46069 was accepted and closed **1 June 2026**.
- **The pitch:** developers instrument with whatever their framework emits; the *platform* normalizes centrally in the pipeline. This is the literal fix for "Phoenix-native app, OTel-native backend" mismatch — and the thing being donated to contrib right now (issue #46069), so a talk raises it at the right moment.

#### At the SDK — Arconia (Spring AI / Java)
- Decouples Spring AI's *instrumentation* from the *schema*. Flip one property:
  `arconia.observations.conventions.opentelemetry.ai.flavor = opentelemetry | openlit | openllmetry | langsmith`
  and the same instrumented spans re-emit under that vendor's attribute names. OpenInference is selected by swapping the dependency (`arconia-openinference-ai-semantic-conventions`), no flavor line.
- Companion knobs: `...ai.capture-content` (`none`/`span-events`/`span-attributes`/`true`), `...ai.include-tool-definitions`, `...ai.include-tool-call-content` — i.e. the opt-in forensic content is a config switch, which ties straight to `research.md`.
- Stack: Java 21, Spring Boot 4.0.5, Spring AI 2.0.0-M5, Arconia 0.27.1. By Thomas Vitale. Base: `salaboy/observing-ai`.
- **The contrast worth drawing:** normalizer fixes it *downstream* (you don't touch apps, works for any language, central policy); Arconia fixes it *upstream* (clean data at the source, but per-framework and Java-only today). Both land on OTel semconv as the target. Platforms will likely want the collector approach; greenfield Spring shops get it for free with Arconia.

---

### 3. Jaeger roadmap — "OTel is the substrate," proven by the oldest tracer

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

### 4. How this maps to the talk

- The **backend spectrum** is the payoff of the demos: instrument once, see five renderings.
- **Normalization** (genai_normalizer + Arconia) is the platform answer to fragmentation — and both are live, donate-able, demo-able *now*.
- **Jaeger's roadmap** is the third-party validation of "OTel is the substrate" — and a bridge into the forensics/agentic-observability close.

---
## Standards and stacks, as last checked

Checked **2026-08-17/18** against the repositories and the running demo. This is the section
most likely to age; re-check before each delivery.

### The GenAI conventions moved house

- The GenAI semantic conventions were **split out of core semantic-conventions** into
  [`open-telemetry/semantic-conventions-genai`](https://github.com/open-telemetry/semantic-conventions-genai).
  The split landed with core semconv **v1.42.0** (12 June 2026), tracked in issue **#3696**.
- The new repository has **no releases yet**, and its README's schema URL still reads `TODO`.
- **188 of 188 stability markers in the GenAI model are `development`.** Not one GenAI
  attribute is marked Stable. Anything you build on them can break in a minor version.

> Talk framing: this is an aside, not a slide. It matters because it is the honest answer to
> "should we adopt this now" — yes, and know that the names can still move.

### Attributes that came and went

- `gen_ai.prompt` and `gen_ai.completion` are **absent from the current registry**. Our own
  Java stack still emits `gen_ai.prompt`, which is a gen_ai name and also the wrong one —
  agreeing on a prefix is not the same as agreeing on a key.
- `gen_ai.input.messages` and `gen_ai.output.messages` are the current shape, and carry
  structured message parts rather than a flattened string.
- `gen_ai.tool.call.arguments` and `gen_ai.tool.call.result` exist and are the two attributes
  the forensic argument turns on. Both are **Opt-In**.

### MCP has conventions now, and they solve the context problem

- MCP is specified in `docs/gen-ai/mcp.md` in the new repository.
- **Context propagation rides in the request's `params._meta`**, carrying unprefixed
  `traceparent`, `tracestate` and `baggage` keys reserved for this by MCP's **SEP-414**. Not a
  transport header — which is what makes it survive a transport that multiplexes several MCP
  messages onto one HTTP request.
- `gen_ai.tool.call.arguments` / `.result` are referenced on **both** the MCP client and
  server spans, at Opt-In, with an anti-duplication rule so one side records them.
- A litmus test the SIG applies, worth repeating on stage: **`execute_tool` is not
  instrumentable by a library that never sees the tool run.** That is why the tool span is the
  one everybody's instrumentation is weakest at.

### What the instrumentation SIG is actually shipping

- [`open-telemetry/opentelemetry-python-genai`](https://github.com/open-telemetry/opentelemetry-python-genai)
  holds **13 instrumentations** built on `opentelemetry-util-genai`.
- First-party **Anthropic instrumentation at 1.0b0**, and a `claude-agent-sdk` skeleton — so
  the SIG is instrumenting agent harnesses, not only provider SDKs.

### The three vocabularies, measured

- **OpenLLMetry 0.62.3 already emits `gen_ai.*` natively.** Its Anthropic instrumentation sets
  `GEN_AI_REQUEST_MODEL`, `GEN_AI_INPUT_MESSAGES` and `GEN_AI_OUTPUT_MESSAGES` — the current
  convention including the new message shape. Of the five branches in the fan-out slide, one
  has already converged, and on a newer revision than our own Java stack.
- **But the library still ships the old names.** `opentelemetry-semantic-conventions-ai 0.5.1`
  defines **16 `traceloop.*` attributes** and **22 `LLM_*` constants** that still resolve to
  `llm.*`. Our otter spans are clean only because we drive `AnthropicInstrumentor` directly
  and never install `traceloop-sdk`. Do not claim OpenLLMetry emits no proprietary attributes —
  claim that the path we use does.
- **OpenInference** needs the collector. `gen_ai_normalizer` (contrib **0.158.0**, alpha,
  traces only) rewrites it in flight — and converts the structure but not the result:
  `output.value` has no entry in the mapping table.

### The two code grants

| | Offered | Outcome |
|---|---|---|
| **OpenLLMetry · Traceloop** | February 2025, over forty instrumentations | closed sixteen months later, unlanded — [community#2571](https://github.com/open-telemetry/community/issues/2571) |
| **OpenInference · Arize** | May 2026 | accepted by the governance committee in June — a code grant of the instrumentations, not the project — [community#3467](https://github.com/open-telemetry/community/issues/3467) |

### Stack facts that cost us time

Each of these is a real defect we hit, and each is on a slide or in a note somewhere.

- **Quarkus ignores `OTEL_SERVICE_NAME`.** You must set `QUARKUS_OTEL_SERVICE_NAME`. With only
  the standard variable set, spans file themselves under the name baked into the image — which
  is how `prod-db-mcp`'s spans spent a week appearing as `capybara-db-mcp`.
- **`TextMapPropagator` is not injectable in Quarkus.** Use `OpenTelemetry.getPropagators()`.
- **quarkus-mcp-server [#789](https://github.com/quarkiverse/quarkus-mcp-server/issues/789)
  (open):** the tool body runs on a *fresh duplicated Vert.x context*, and Quarkus keeps the
  active OTel Context in that context's local storage — so the tool body starts a new trace.
  The SQL that touched the rows was in a different trace from the agent that asked for it.
  Closed from the tool side by extracting `traceparent` out of `_meta` and re-parenting:
  **21 spans → 27 spans**, with the `SELECT` inside the agent's trace. Toggle with
  `capybara.mcp.propagate-context` / `CAPYBARA_MCP_PROPAGATE_CONTEXT=false` to show the gap.
- **MCP Python SDK 2.0.0** ships its own OTel instrumentation (`mcp/shared/_otel.py`,
  `inject_trace_context`) and emits `MCP send <method>` spans. `streamable_http_client` yields
  a **2-tuple** and talks **httpx2**, so an httpx instrumentation never sees it — which costs
  nothing, because the SDK traces and propagates for itself.
- **goose needs v1.46.0 or newer.** Earlier releases emit **no `gen_ai.*` attributes at all**;
  the two PRs that added them merged four hours after 1.45.0 was cut. A pinned older goose
  produces a run that looks fine and records nothing.
- **goose sends no trace context over MCP.** Every span its MCP server produces is a root of
  its own, and its token totals appear three times in one trace, so summing across spans
  triples the count. Not ours to fix: there is nothing on the wire to recover.

### The finding the demo exists to produce

All three investigators call the same four tools on the same MCP server, so the only variable
is what writes the telemetry. With that variable isolated:

> **Three independent MCP implementations in one trace, and not one of them records the tool
> call's arguments or its result.** Only the spans we wrote by hand carry them.

The audit trail is what closes the gap, and it can only ever name the credential — Postgres
records `session_user` (the authenticated `deploy_svc` role) and `application_name` (the
client's self-reported name, `goose`). A `SECURITY DEFINER` trigger writes both. The database
cannot name the agent, because the agent never introduced itself.

---

## Resources

Reference material for *Your Agent Did What? Forensic Observability for Systems That Don't Leave Obvious Footprints*.

### The fragmentation problem

- [Five Semantic Conventions, One Config Property: Observing Spring AI with Arconia](https://www.salaboy.com/2026/05/27/five-semantic-conventions-one-config-property-observing-spring-ai-with-arconia/) — Salaboy's walkthrough of the GenAI semantic convention fragmentation problem. Covers five competing conventions (OpenTelemetry, OpenInference, OpenLLMetry, LangSmith, Langfuse) and how Arconia decouples instrumentation from the convention schema, letting you switch backends by setting a single config property instead of changing code. Good framing for "why is this a mess."

### OpenTelemetry GenAI

- [OTel GenAI Semantic Conventions (docs)](https://opentelemetry.io/docs/specs/semconv/gen-ai/) — the official spec for GenAI attributes, spans, metrics, and events.
- [OTel GenAI Semantic Conventions (GitHub source)](https://github.com/open-telemetry/semantic-conventions/tree/main/docs/gen-ai) — the raw source for the conventions, often easier to navigate and ahead of the rendered docs.

### Normalizing at the edge

Two answers to "five conventions for the same span" — one at the collector, one at the SDK.

- [genainormalizerprocessor (source)](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/processor/genainormalizerprocessor) — the collector processor that canonicalizes span attributes from **OpenInference** and **OpenLLMetry** into official OTel GenAI semconv (pins schema v1.40.0). Config key is `gen_ai_normalizer`; **traces only**; no auto-detection (you list the source conventions explicitly). Status: merged, **alpha**. It **ships in the released contrib image** — verified running on `0.158.0`, no `ocb` build needed. Donation [issue #46069](https://github.com/open-telemetry/opentelemetry-collector-contrib/issues/46069) was accepted and closed 1 June 2026. Example renames: `llm.model_name`→`gen_ai.request.model`, `llm.token_count.prompt`→`gen_ai.usage.input_tokens`, `openinference.span.kind`/`traceloop.span.kind`→`gen_ai.operation.name`.
- [Donation discussion (issue #46069)](https://github.com/open-telemetry/opentelemetry-collector-contrib/issues/46069) — the proposal to donate it to contrib. Code owners: @TylerHelmuth, @kylehounslow.
- [Arconia](https://arconia.io) ([GitHub](https://github.com/arconia-io), [docs](https://docs.arconia.io)) — a Java / Spring Boot toolkit that decouples Spring AI instrumentation from the convention schema. Flip `arconia.observations.conventions.opentelemetry.ai.flavor` between `opentelemetry` / `openlit` / `openllmetry` / `langsmith` (OpenInference via a dependency swap) and the *same* spans re-emit under that schema — no code change. By Thomas Vitale. Base demo to fork: [salaboy/observing-ai](https://github.com/salaboy/observing-ai) (sibling modules per convention). Pinned in the demo: Arconia 0.27.1, Spring AI 2.0.0-M5, Spring Boot 4.0.5, Java 21.

### Competing / framework conventions

- [OpenInference](https://github.com/Arize-ai/openinference) (Arize) — instrumentation conventions and SDKs for LLM/agent observability.
  - [OpenInference spec](https://arize-ai.github.io/openinference/spec/) — the attribute and span conventions in detail.
- [OpenLLMetry](https://github.com/traceloop/openllmetry) (Traceloop) — OpenTelemetry-based instrumentation for LLM apps with its own attribute conventions.
- [Langfuse](https://langfuse.com/) — open-source LLM engineering / observability platform.
  - [Langfuse (GitHub)](https://github.com/langfuse/langfuse) — source repo.
- [LangChain](https://www.langchain.com/) — the agent/LLM framework; relevant for framework-specific instrumentation and LangSmith conventions.

### Visualization & backends (where GenAI traces go)

The "what can I actually look at this in" layer — see `landscape.md` for the analysis and the `demos/` harness for a runnable comparison.

- [Jaeger](https://www.jaegertracing.io/) — generic OTLP-native trace viewer (CNCF, graduated). The baseline: a GenAI trace in a tool with *no* GenAI awareness. **v1 reached EOL 2025-12-31**; v2 is rebuilt on the OTel Collector. See its [roadmap](https://www.jaegertracing.io/roadmap/) and the GenAI epics ([#7827](https://github.com/jaegertracing/jaeger/issues/7827), [#8416](https://github.com/jaegertracing/jaeger/issues/8416)).
- [Arize Phoenix](https://github.com/Arize-ai/phoenix) — OSS, GenAI-native, **OpenInference-native**. Renders OTel-GenAI-semconv (`gen_ai.*`) spans as plain spans — fragmentation made visible. ([Translating conventions](https://arize.com/docs/phoenix/tracing/concepts-tracing/translating-conventions).)
- [OpenLIT](https://docs.openlit.io/) — OSS, OTel-semconv-native GenAI dashboard *and* an instrumentation SDK (`openlit.init()`) that auto-instruments the Anthropic SDK and emits `gen_ai.*`.
- [OpenSearch Agent Traces](https://docs.opensearch.org/latest/observing-your-data/agent-traces/agent-tracing/) — OTel-GenAI-semconv-native agent-trace UI (categorizes spans by `gen_ai.operation.name`). Ingests via OTel Collector → **Data Prepper** → OpenSearch (no direct OTLP). UI is RFC-stage in OSS OpenSearch ([#11345](https://github.com/opensearch-project/OpenSearch-Dashboards/issues/11345)), live on AWS.
- [Dash0](https://www.dash0.com/) — the vendor path in the demos (OTLP exporter from the collector).

### Evaluation tooling

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
  flag you throw" shape as `include-tool-arguments` in `capybara-sre`, one layer closer to home.

### CNCF agent tooling (reference)

- [kagent](https://github.com/kagent-dev/kagent) — agents as first-class Kubernetes workloads; agent lifecycle as a custom resource (CNCF Sandbox).
- [HolmesGPT](https://github.com/robusta-dev/holmesgpt) — agentic SRE troubleshooter that reads OTel data, calls observability tools over MCP, escalates to humans.
- [agentgateway](https://agentgateway.dev/) — the tool-call data plane between agents and tools; a natural enforcement + observability point.