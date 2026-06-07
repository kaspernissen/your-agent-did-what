# Your Agent Did What? Forensic Observability for Systems That Don't Leave Obvious Footprints

## Abstract

The GenAI observability space is fragmented right now. OpenInference, OpenLLMetry, framework-specific conventions are all solving the same problems with incompatible attribute names. That made sense when OTel's GenAI support was thin. It makes less sense today.

OTel is where this converges. Getting there from where most teams actually are isn't obvious. Kasper and Adriana Villela cover the current landscape, how the genainormalizer processor bridges the gap at the collector layer, and what a realistic path to OTel-native GenAI observability looks like.

Then the harder question: your agent just deleted a database. What does your telemetry actually tell you? Non-deterministic systems don't leave obvious footprints, and most teams discover that at the worst possible time.

## Benefits to the Ecosystem

The OpenTelemetry GenAI SIG is doing important work, but adoption is slower than it should be because teams default to OpenInference or OpenLLMetry without understanding the tradeoffs. This talk helps fix that.

By mapping the current instrumentation landscape honestly, including coverage gaps, incompatible attribute names, and the open source tooling that bridges them, attendees leave with a clear picture of where OTel stands today and a concrete path toward OTel-native GenAI observability. That benefits the OTel project directly: more teams instrumented correctly means better feedback to the SIG, stronger real-world validation of the semantic conventions, and less ecosystem fragmentation over time.

The genainormalizer processor is currently working toward donation to opentelemetry-collector-contrib. A talk at OSS EU raises visibility for that effort and encourages community contribution at exactly the right moment.

Beyond OTel, the forensics angle addresses a gap nobody is talking about seriously yet: what observability needs to look like for autonomous systems. Teams shipping agents to production need this now, not after something goes wrong.
