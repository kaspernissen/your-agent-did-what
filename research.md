# Research: Forensic Observability for Autonomous Agents

> **Research notes.** Background reading gathered before the demo existed. Still the sourcing behind several slides, but [`demos/ANALYSIS.md`](demos/ANALYSIS.md) is the measured record and wins wherever the two disagree.

Background research for the forensics half of *Your Agent Did What?* — what telemetry you actually need to reconstruct what an agent did when something goes wrong, and where today's GenAI observability stack falls short for post-incident forensics on non-deterministic systems.

Method: fan-out web search across five angles → 21 sources fetched → 100 claims extracted → 25 highest-value claims verified with 3-vote adversarial checking (a claim needs 2 of 3 votes to survive). 21 confirmed, 4 killed. Full source list and the verification caveat are at the bottom.

---

## The one-line finding

**The OTel GenAI conventions can already name what an agent did. They cannot, by default, tell you *what it did with what arguments, what came back, or why it chose to.* The structural spans exist; the forensic content is opt-in and off by default; and there is no schema slot at all for the decision itself.**

That is the forensic gap in one sentence, and it's the natural next slide after your pizza-shop trace ("the data being present is not the same as the data being legible"). The PlatformCon deck shows the signal is buried. This shows that for forensics, the signal you most need was often never recorded.

---

## What the conventions give you — and what they withhold

**The spans exist and are distinct from inference.** OTel GenAI defines `create_agent`, `invoke_agent`, `invoke_workflow`, and `execute_tool` as first-class spans, separate from the underlying model-inference span. So a conforming trace *does* show you the shape of the run: an agent was created, a workflow ran, a tool executed. (High confidence, 3-0. Source: OTel GenAI spans spec.)

**But the forensic payload is opt-in, off by default.** The content you need to reconstruct an incident — tool-call arguments, tool results, input/output messages, system instructions — is gated behind opt-in flags. The spec explicitly says instrumentation **SHOULD NOT** capture this by default (privacy and payload-size reasons). So the out-of-the-box trace tells you *a tool ran*. It does not tell you it ran `DROP TABLE`, what the database returned, what prompt led there, or what the agent was asked. (High confidence, 3-0.)

> Talk framing: this is the "your agent deleted a database" moment. With default instrumentation you can prove the `execute_tool` span fired. You cannot prove what it executed. The footprint exists; the footprint is empty.

**There is no decision-provenance primitive at all.** Across OTel GenAI *and* the rest of the ecosystem (LangSmith, Langfuse, Datadog, LangGraph), there is no schema-level attribute for *why* the agent chose what it chose. The closest thing is a reasoning-*token-count* — a number, not the reasoning. Span message "parts" are typed only as text or tool_call; there is no provenance part. And every GenAI attribute is still **Development-stage** — subject to breaking change. (High confidence, 3-0. Sources: OTel attribute registry; arXiv 2603.21692.)

> This is your "Why did it do that?" property (PlatformCon slide 7, property 4) expressed as a concrete schema gap: there is nowhere in the standard to *put* the why, even if you captured it.

---

## Why you can't just replay it

**Faithful replay is fundamentally limited.** Two independent reasons:

1. **The assembled context window is not persisted.** The exact bytes the model saw — after retrieval, memory, tool results, and context assembly — are typically not stored. Without that input, you can't deterministically rerun the step.
2. **Non-determinism diverges the trace anyway.** Sampling, context-assembly order, and timing mean a rerun produces a *different* trace, not the same one.

The consequence is the load-bearing point for the talk: **reasoning provenance cannot, in general, be reconstructed after the fact — it has to be captured at execution time.** If you didn't record *why* when it happened, re-running won't recover it. (Confirmed 3-0; medium confidence — rests substantially on a single recent preprint, 2603.21692, plus the OpenClaw paper.)

> This is the evidence behind "Reconstructing *why* is the new MTTR — you're interrogating a system you can't replay." The research says: you literally cannot replay it, so the only forensic strategy is capture-at-runtime. That reframes instrumentation from "nice to have" to "the only chance you get."

---

## What the research community is building (the shape of an answer)

Three primary sources converge on the same structural move: **separate the thought from the action, and link them with provenance edges.**

- **AgentSec dataset** models incidents as `decision_traces` (with `selected_option` and `resulting_actions`) kept *distinct* from `tool_call_event` objects, joined by a `triggered` edge in a provenance graph (`used_by` / `triggered` / `derived_from` / `caused`). It explicitly captures the point that, unlike rule-based software, an agent's tool choice is LLM/context/environment-driven. (High confidence, 3-0.)
- **OpenClaw** proposes a five-plane forensic taxonomy — Brain / DNA / Memory / Ears-Mouth / Hands — that separates reasoning from action, and pairs each `toolCall` (name, id, args) with a `toolResult` (toolCallId, isError, timestamp) in session logs. The paper states plainly that **systematic agentic forensics is largely unexplored**. (High confidence, 3-0.)
- **AgentRR** (record-and-replay) logs *actions plus environment state at every step*, at the GUI or API layer, and uses an "experience abstraction" to decouple intelligence from execution — isolating creative LLM output to designated decision nodes. (High confidence, 3-0.)

> The common thread — decision record + action record + an edge between them — is exactly what the OTel GenAI conventions don't yet have a place for. That's the gap to point the SIG at, and it complements your genainormalizer story: normalizing names is necessary but not sufficient if the thing you most need (the decision) has no field.

---

## What did *not* hold up (intellectual honesty for the stage)

Four claims were killed under adversarial verification. Worth knowing so you don't repeat them:

- **"Reasoning-effort token count is the only reasoning signal."** (1-2) Overstated as phrased — the broader point survives in the confirmed findings, but the narrow claim got refuted.
- **"You can recover decision provenance from the model's chain-of-thought / 'thinking' blocks."** (1-2) **Killed — and this one matters.** Don't claim you can reconstruct *why* from the model's self-narrated reasoning. Thinking blocks are not a reliable provenance record; treat them as output, not audit trail.
- **"Agent-mediated execution / the extra abstraction layer is *the* core obstacle to forensics."** (1-2) Refuted as overstated — non-determinism and missing capture matter more than the abstraction layer per se.
- **"You need a three-layer independent interception harness (MCP stdio proxy + shell DEBUG trap + filesystem watcher) to reconcile reported vs. actual actions."** (1-2) Interesting and intuitively right (the agent may report one action and perform another), but it rests on a single preprint and was refuted as a general requirement. Use as a "some researchers propose…", not a claim.

> The second one is a useful slide on its own: the obvious answer — "just log the chain-of-thought" — does not actually give you forensics. That's a satisfying myth to puncture.

---

## How this maps onto the talk

| PlatformCon thread | What this research adds |
|---|---|
| Pizza-shop trace: signal buried in 290 spans | …and the forensic signal is often *not captured at all* — args/results/prompt are off by default |
| "Reconstructing *why* is the new MTTR" | You can't replay it; provenance must be captured at runtime or it's gone |
| Property 4: "Why did it do that?" | No schema primitive exists for the decision — it's a standards gap, not just a tooling gap |
| genainormalizer normalizes names at the edge | Necessary but insufficient: normalizing names doesn't create the missing decision field |
| Five competing conventions | All five share the same blind spot on decision provenance — fragmentation isn't the only problem |

---

## Sources

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

## Caveat — verify before you cite on stage

This report was synthesized from automated search + adversarial verification, which reduces but does not eliminate two risks:

1. **Recency / single-source weakness.** Several load-bearing claims (replay impossibility, five-plane taxonomy, decision-provenance gap) rest on very recent arXiv preprints (2603.21692, 2604.05589, 2505.17716) — sometimes a single one. Preprints aren't peer-reviewed. **Open the arXiv papers yourself and confirm the specific claims before putting them on a slide**, especially the "replay is fundamentally impossible" framing.
2. **The OTel spec claims are the safest.** The "forensic content is opt-in / SHOULD NOT capture by default" and "no decision-provenance primitive / Development-stage" findings are checkable directly against the spec pages above, and they're the strongest material for the talk. Lead with those; treat the academic framing as supporting color.
