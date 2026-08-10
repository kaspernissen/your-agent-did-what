# Notes

## Evaluations? 
- Semantic Conventions has a concept of evaluations, but how do we use them? How do we actually know if the output of the message was successful or not? 
- ~~The opensearch project: github.com/opensearch-project/agent-health (need to check this out.~~
  **Checked 2026-08-10.** OSS agent evaluation + observability, LLM judge against a "Golden Path"
  trajectory — the gold-set mitigation, implemented. Not a slide; it is in `resources.md` and in the
  speaker notes for the Stable-zero slide (its instrumentation guide still specifies the deprecated
  `gen_ai.system`), the judge-caveats slide (gold set), and the coding-agents slide (its Claude Code
  guide documents the opt-in content flags).


LLM-as-judge? We need to explain the concept. How do you build trust and confidence in what your agents are doing? 

How fast do you need the evaluations? Is it a gate? Is it a quality metric you improve from time to time? What is good? What is good enough? What's the trade-offs?

---

## Answers (researched 2026-07-01 — full writeup in `research-evaluations.md`)

**Does OTel have an evaluations convention?** Yes — but it's a **log-based event**, not a span or metric. Event name `gen_ai.evaluation.result`, carrying four attributes (all *Development* stability):

- `gen_ai.evaluation.name` — e.g. `"Relevance"`, `"remediation_safety"`
- `gen_ai.evaluation.score.value` (double) — e.g. `4.0`, `0.9`
- `gen_ai.evaluation.score.label` — e.g. `pass` / `fail` / `relevant`
- `gen_ai.evaluation.explanation` — the judge's free-form rationale

Linked to the evaluated operation via `gen_ai.response.id` (or parented to its span). `gen_ai.evaluation.score.units` does **not** exist. The GenAI conventions moved to a dedicated repo, `open-telemetry/semantic-conventions-genai`. An eval-as-**span** + a `gen_ai.operation.name="evaluation"` value are still **open, unmerged** (PR #185, which cites OpenSearch's SDK inventing that value as the fragmentation it's fixing); a guardrail convention is PR #262.

**How do you know if the output was successful → LLM-as-judge.** Use a strong model to grade another model's output (Zheng et al. 2023: GPT-4 reaches "over 80% agreement" with humans). Known biases: **position, verbosity, self-enhancement** (mitigate with position-swapping, rubrics/CoT, and validation against a human gold set — report Cohen's κ, not raw agreement). For agents: judge the **trajectory** (tool-call sequence + outcome), not just the final answer.

**Is it a gate or a quality metric? (the trade-off)** Three placements:

| Type | Runs | Blocking? | Role |
|---|---|---|---|
| **Offline** | pre-deploy vs curated datasets (CI) | hard gate on the **deploy** | regression prevention |
| **Online** | live traffic, async, sampled | **non-blocking** | background quality metric / drift |
| **Inline / guardrail** | in the request path | hard gate on the **response** | PII / injection / toxicity tripwire |

Inline guardrails add latency to *every* request (keep them light; run in parallel, or blocking-first to save cost). "Good enough" is a **risk-calibrated product decision** — pass rate ≠ 100%; thresholds per use case; validate the judge against human ground truth (Hamel Husain, Eugene Yan).

**opensearch-project/agent-health** (checked ✅) — early/Experimental OpenSearch framework that ingests OTel GenAI traces and runs **LLM-as-judge "Golden Path" trajectory comparison** (pass rate / accuracy / cost). It **emits the standard `gen_ai.evaluation.result` event**. Usable locally via docker-compose with an **Anthropic key through a LiteLLM proxy** (no AWS needed). → this powers the capybara demo (see `docs/superpowers/specs/2026-07-01-capybara-sre-eval-demo-design.md`).

