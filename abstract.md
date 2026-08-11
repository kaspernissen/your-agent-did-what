# Your Agent Did What? Forensic Observability for Systems That Don't Leave Obvious Footprints

## Abstract

The GenAI observability space is fragmented right now. OpenInference, OpenLLMetry, framework-specific conventions are all solving the same problems with incompatible attribute names. That made sense when OTel's GenAI support was thin. It makes less sense today — and we'll show you exactly what OTel covers now, measured from running agents rather than read off a roadmap.

OTel is where this converges. Getting there from where most teams actually are isn't obvious. Kasper and Adriana Villela cover the current landscape, how the genainormalizer processor bridges the gap at the collector layer, and a concrete path to OTel-native GenAI observability — including how far normalization actually gets you, and where it stops.

Then the harder question: your agent just deleted a database. What does your telemetry actually tell you? We run it, and the answer is uncomfortable — the span proves a tool called `delete_records` ran, and cannot tell you it deleted the free plan. Non-deterministic systems don't leave obvious footprints, and most teams discover that at the worst possible time.

Finally, the question after that one: was it any good? OTel already carries the answer as an event, and we'll show a judge scoring a real agent run — a quality metric you improve, and a safety gate you don't cross.

## Benefits to the Ecosystem

The OpenTelemetry GenAI SIG is doing important work, but adoption is slower than it should be because teams default to OpenInference or OpenLLMetry without understanding the tradeoffs. This talk helps fix that.

By mapping the current instrumentation landscape honestly, including coverage gaps, incompatible attribute names, and the open source tooling that bridges them, attendees leave with a clear picture of where OTel stands today and a concrete path toward OTel-native GenAI observability. That benefits the OTel project directly: more teams instrumented correctly means better feedback to the SIG, stronger real-world validation of the semantic conventions, and less ecosystem fragmentation over time.

The genainormalizer processor was donated to opentelemetry-collector-contrib and accepted in June 2026, and now ships in the released collector image — which means adopting it is a config change rather than a custom build. That is exactly the moment to raise its visibility: the barrier to adoption just dropped, the processor is still alpha, and it needs real-world usage and contributors to mature.

Everything we claim, we measured. The talk carries the numbers from two runnable demos — including the places our own stack failed to produce the telemetry the documentation promised. Where we're stating a position rather than a finding, we say so.

Beyond OTel, the forensics angle addresses a gap nobody is talking about seriously yet: what observability needs to look like for autonomous systems. There is currently no field anywhere in the GenAI conventions for *why* an agent chose what it chose — and naming that gap for the SIG is one of the concrete asks we leave the room with. Teams shipping agents to production need this now, not after something goes wrong.
