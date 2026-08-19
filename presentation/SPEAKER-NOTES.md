# Your Agent Did What? — speaker notes

**Aligned to the Google Slides deck** (`Your Agent Did WHAT_ (2).pdf`, 46 slides).
One section per slide, in deck order.

## How this maps to the HTML deck

The Slides deck is the HTML deck’s spoken flow with **one slide removed**: *“One question,
one loop”*, the four-process sequence diagram between “The demo setup” and the demo divider.
Everything else is 1:1 and in the same order, so section numbering 01–07 is unchanged and
every “beat N” reference below still points where it says.

Nothing is lost: the part of that slide that carries the argument is folded into **slide 27**
and marked there.

Five notes pointed at appendix slides. This deck has no appendix, so they now say to open the
HTML deck instead — that material is still there, slides 48–72.

**One typo to fix on slide 44:** the title reads “The agent worth watching first **it** the one
on your laptop”. Should be *is*.

---

## 01 · Your Agent Did WHAT?

<sub>HTML deck: “Cover” · slide 1</sub>

Good morning. This is “Your Agent Did What?” — the subtitle is doing a lot of work, so it can stay on screen rather than be read out.

There are two of us up here because we hit this problem separately, on different stacks, and arrived at the same uncomfortable place.

QRs in the corners if you want to find us afterwards.

⚑ Hold here while the room settles.

---

## 02 · Who?

Twenty seconds each, and the slide has the credentials so they don't need reading out.

The part that matters later: we're both CNCF ambassadors, and both AI-agent ambassadors for the AAIF. That second one comes back at the end, when we talk about the agent you're already running and probably not watching.

⚑ If anyone asks about the capybara: one of us genuinely loves them, which is why the demo agent is called Capybara and why there's one asleep in the footer of every slide.

---

## 03 · We keep changing what we have to understand

Some context for why this is hard, and it is not because agents are magic.

We keep changing the shape of what we have to understand. Monolith to microservices to event-driven to LLM applications. Each step solved a real problem and moved complexity somewhere else.

Building got steadily easier every time. Understanding got harder every time.

We are four architectures deep and still reaching for tools designed for the first one.

⚑ Adriana's framing: the fourth era is LLM applications rather than agents, because the scope is broader than the agent sitting inside one.

---

## 04 · Agents aren’t request/response  <sub>section 01</sub>

<sub>HTML deck: “Divider — 01” · slide 4</sub>

First, why this is a different problem rather than a harder version of the old one.

---

## 05 · An agent is one part of an LLM application

<sub>HTML deck: “What an LLM application is” · slide 5</sub>

Before we get specific, one level up.

When people say "we shipped an LLM feature", this is usually what they mean. There is orchestration that builds the prompts and keeps the state. A model, hosted or called over an API. Retrieval, so the answers are grounded in your data. Tools and agents, which take actions. And underneath it all, ordinary application scaffolding.

Most of this you already know how to operate. The database, the HTTP calls, the auth, the storage. Your existing instrumentation covers it.

It is the box on the right that is new, because it is the only one that decides what to do while it is running. That is the part this talk is about.

⚑ Do not linger. This exists so nobody is lost when we say "agent" for the next thirty minutes, and so the room sees that the agent is a component rather than the whole system.

⚑ Lead-in that used to be printed: most of this you already know how to observe.

---

## 06 · Five words we will use for the next half hour

<sub>HTML deck: “Terminology” · slide 6</sub>

Five words, quickly, so nobody is decoding vocabulary while we talk.

Provider is whoever hosts the model. Model is the thing that generates. MCP is how an agent gets handed tools it did not ship with, an API designed for models rather than people.

An agent is a model, some instructions, some tools, and a loop: observe, reason, act, evaluate, and round again until it decides it is done.

And a harness is what runs the agent. Memory, lifecycle, observability. goose, Claude Code and Copilot are all three of those at once, which is why they are both the thing you observe and the thing doing the observing.

⚑ Do not lecture, most of the room knows some of these. The one to land is the loop: everything difficult later comes from a decision that repeats and that you did not write.

---

## 07 · An agent is a loop around a model that can call your tools

<sub>HTML deck: “What an agent is made of” · slide 7</sub>

An agent is a loop.

There's a model, and there's a list of tools you handed it. The model doesn't run anything — it picks the next step. Something else executes that step, feeds the result back, and the loop goes round again until the model says it's finished. MCP is just how it gets handed tools it didn't ship with. Tokens are the billing unit, and usually the only cost signal you get.

Two things here are yours: the prompt, and the tool list. That's it.

How many model calls, which tools, in what order — decided at runtime, every time. Which means you cannot read the path off the code. You have to observe it.

⚑ This diagram is the demo, made abstract. When Capybara turns up later, it is this.

⚑ The line that used to sit at the bottom of this slide, and it is the one to say out loud: you cannot read the path off the code. You have to observe it.

⚑ The rest of that line, spoken: how many model calls, which tools, in what order — all decided at runtime.

---

## 08 · Four properties we’ve never operated before

So what is actually different about operating this.

Four things, and the first three are uncomfortable rather than novel. It is non-deterministic, so re-running it does not reproduce the bug. The call graph is generated at runtime, so it is not declared anywhere you can read. And the cost model is tokens, not requests per second, so your capacity intuition does not transfer.

The fourth is the one this talk is about. When it does something, there is no stack trace for why it chose that.

⚑ Do not oversell the first three, most of the room has met them. Slow down on the fourth; everything after this beat is an attempt to close that gap with the tools we already have.

---

## 09 · Nobody builds an agent to do something destructive

<sub>HTML deck: “Why should we care” · slide 9</sub>

Worth being clear about the stakes, because this is not a talk about malicious AI.

Nobody builds an agent to do something destructive. They build it to be useful, they give it tools, and they point it at real systems. And without guardrails, useful and destructive are the same capability pointed at different rows.

So when one does something you did not expect, the questions are always the same three. What did it decide. Which tools did it use. And why.

You cannot mitigate what you cannot reconstruct. The rest of this talk is whether your telemetry can answer those three, and we will find that it answers two of them.

⚑ Land the last line deliberately. It sets up beat 5, where the third question turns out to have no field in any convention.

---

## 10 · You either build one, or you run someone else’s

<sub>HTML deck: “Two ways you meet an agent” · slide 10</sub>

And there are two ways you meet one of these, which is worth separating because the problems are different.

Either you build it, with LangChain, LangGraph, Spring AI, LangChain4j. Then you chose the framework, so you chose what it emits, and your problem is which convention and what it leaves out.

Or you run somebody else's. kagent, HolmesGPT, k8sgpt, the copilots already in your tooling. You did not choose the instrumentation.

That second case has two problems rather than one. It reads your telemetry, so it is only as good as what it reads. And it acts on your systems, so you need its telemetry too.

Most of us are both. The conventions are what make the second case survivable, which is why the first case matters even if you never build an agent.

⚑ The rest of that closing line, now spoken: the conventions are what make the second case survivable, which is why the first case matters even if you never build an agent yourself.

⚑ The marks on the left are two different kinds of thing on purpose, and it is worth naming that as you point at them: LangChain is the framework, OpenInference and OpenLLMetry are instrumentation libraries you wrap around it. Both are choices you make when you build, which is the column's point. The distinction between those two kinds gets its own slide shortly, so do not blur it here — say "framework and instrumentation", not "frameworks".

---

## 11 · Every familiar signal has a new equivalent

And the useful way to think about it is not that our practice is wrong. It is that it is incomplete.

Everything we rely on has an equivalent on the other side. A stack trace becomes a reasoning chain. A status code becomes a quality signal, because a run can succeed and still be wrong. Requests per second becomes tokens, cost and blast radius. A static call graph becomes tool invocations decided at runtime. And a replayable request becomes a run you cannot replay.

None of those equivalents exist by default. We have to build them, and the rest of this talk is about how far the conventions get you.

⚑ This is the slide to point back to in beat 6. The judge is the quality signal in that right-hand column, made real.

---

## 12 · Five conventions, one span  <sub>section 02</sub>

<sub>HTML deck: “Divider — 02” · slide 12</sub>

So we observe it. And immediately there's a problem: nobody agrees on what to call any of it.

---

## 13 · One model call. Five names for the model.

<sub>HTML deck: “One model call, five names” · slide 13</sub>

One HTTP call to one model. Five different names for the model.

OpenTelemetry says gen_ai.request.model. OpenInference says llm.model_name. OpenLLMetry has its own. So does LangSmith. So does Langfuse.

None of these people were being difficult. Each convention was built for a real job: tracing, evaluation, prompt management. Each optimised for that job.

But the consequence is yours to carry. Your dashboard, your alert, your query works on one vendor's spans and silently returns nothing on another's.

Remember OpenInference, the thick branch. We come back to it later and rewrite it in flight.

⚑ Don't name the second agent yet, it hasn't been introduced. And don't say "the amber one": name the convention, or the room has to decode the colour scheme to follow you. Correction worth carrying, measured 2026-08-17: OpenLLMetry 0.62.3 no longer emits its own names. Its Anthropic instrumentation sets GEN_AI_REQUEST_MODEL, GEN_AI_INPUT_MESSAGES and GEN_AI_OUTPUT_MESSAGES, which is the current convention including the new message shape. So of the five branches, one has already converged, and it did it on the newest revision rather than the one our own Java stack is on.

⚑ Two things that were printed on this slide and are now yours to say. First, the converging is not hypothetical: OpenLLMetry already emits gen_ai.* as of 0.62.3, measured this week. Second, keep an eye on OpenInference, because we come back to that one when we normalize.

---

## 14 · Instrumenting the agent is not instrumenting the SDK

<sub>HTML deck: “Two kinds of instrumentation” · slide 14</sub>

A distinction that took us a while to see, and it changes what you get.

There are two completely different places this telemetry can come from.

The agent can instrument itself. It knows the loop, the tools and the session, because it is the thing running them. Claude Code does this on the OTel Node SDK, goose on the Rust one, LangChain with its own, currently on an older revision of the conventions.

Or something wraps the provider SDK from the outside. OpenLLMetry, OpenInference, the OTel GenAI instrumentation. Those see the calls, but not the intent behind them.

It matters which one you have. Only the first can tell you why a tool was called, because only the first was there when it was decided.

⚑ Also worth saying: provider coverage differs between these libraries, and so do the attribute names. Two products doing the same job disagree about what to call the model, which is what the five-names slide just showed.

---

## 15 · Four teams, four problems, and no standard to adopt

<sub>HTML deck: “Four problems, no standard” · slide 15</sub>

So why are there five of these, if nobody was being difficult?

Because every one of them shipped before there was anything to adopt. Four teams, four real problems, four vocabularies that each made sense for the problem in front of them.

OpenInference came out of evaluation. If your job is scoring and comparing runs, the prompt and the completion are the data, so they go on the span as first-class fields. OpenLLMetry came out of tracing, OTel-native from the start, wrapping the provider SDKs so nobody had to change an application. LangSmith came out of debugging chains, and it is modelled on LangChain's own runs and chains, which is not a span and never was. Langfuse is a product, so it has its own trace and observation model and its own names to match it.

Every one of those is a reasonable answer. They are just answers to different questions.

Then the turn, and it is the reason the next section exists. Divergence costs you nothing while you are the one choosing the stack: you pick one, you learn its names, you move on. It starts costing you the moment you are running agents you did not choose — the coding agent in your editor, the copilots already in your tooling, kagent, HolmesGPT. You cannot pick their vocabulary. So the join has to happen in the data, and a shared vocabulary is the only thing that makes that join possible.

⚑ One honest caveat if pressed: both LangSmith and Langfuse can ingest OTLP today. This slide is about the names they emit natively, not about whether they can accept yours.

⚑ Do not spend long on the four cards. The room does not need the history; it needs to stop reading the fragmentation as carelessness, because that is what makes the convergence in the next section believable.

---

## 16 · Why OpenTelemetry should be the standard  <sub>section 03</sub>

<sub>HTML deck: “Divider — 03” · slide 16</sub>

Which raises the obvious question: why pick OpenTelemetry, rather than the one your framework already emits?

---

## 17 · A toolkit and a specification

<sub>HTML deck: “What OpenTelemetry is” · slide 17</sub>

Thirty seconds on what OpenTelemetry actually is, because it is easy to hear "OTel" and think "a collector" or "an agent you install".

It is a toolkit and a specification. On the left, what it is: data models, API specifications, semantic conventions, library implementations in a lot of languages, and a pile of utilities. On the right, what it is not, and this list matters just as much: it is not proprietary, it is not an all-in-one observability tool, it is not storage or dashboards, it is not a query language, and it is not feature complete.

Three goals: unified telemetry, vendor neutrality, cross platform. Vendor neutrality is the one doing the work in this talk.

And the line to land: of everything on the left, the item this talk turns on is semantic conventions. Names for things. A vendor's names arrive with a vendor's roadmap and a vendor's commercial interest; a specification nobody owns does not.

⚑ If the room needs the adoption number: the CNCF annual survey has 49% running OpenTelemetry in production and 26% evaluating it. Do not put it on the slide, it is a warm-up statistic and this audience already believes it.

⚑ The transition into the demo, if you want one sentence: an agent incident is a systems incident with a model in front of it. When rows go missing the next span you need is not a GenAI span, it is the SQL, the pod restart, the deploy that changed a grant — and those are already in OpenTelemetry.

---

## 18 · They already agree more than they admit

<sub>HTML deck: “Everyone is aiming at the same target” · slide 18</sub>

Remember the fan two beats ago — one model call, five different names for the model. This is that picture turned the other way up.

Same five conventions. And they are not drifting apart, they are converging, on the one target none of them owns. Read how each one gets there, because the four routes are different and the differences are the interesting part.

OpenLLMetry is already there. Its current release emits gen_ai names natively — we measured it this week, and it needs nothing from us. OpenInference gets there at the collector, which is the processor on the last slide, and that is a config block rather than a code change. LangSmith has a proprietary protocol, so it needs a bridge before it can join at all. And Langfuse still uses its own names.

The point of the arrows: nobody is proposing a fifth convention. Every one of these projects treats the OpenTelemetry conventions as the destination, and the only question left is how each one travels.

Then land the line. This is the one vocabulary nobody owns. Adopt a vendor's names and you inherit their roadmap and their commercial interest along with them.

⚑ This replaced a slide that put OpenLLMetry, Spring AI and the collector processor side by side as "three independent stacks that agree". The measurement was real — all three do land on gen_ai names for the model, the provider and the token counts — but they are three different kinds of thing, and the slide read as a list of unrelated projects. Keep the measurement in your pocket for the floor; the picture makes the argument better than the list did.

⚑ Do not overstate Langfuse or LangSmith. Both are moving; what is on the slide is where they were when we checked. If pressed, the honest version is that the direction is settled and the timelines are not.

---

## 19 · The code is converging. The vocabulary is not, yet.

<sub>HTML deck: “The code converges, the vocabulary does not” · slide 19</sub>

One more thing about where this is going, and it is more interesting than "everyone is converging".

Both of these vendors offered their instrumentation to OpenTelemetry.

Traceloop offered OpenLLMetry in February 2025. Over forty instrumentations. It sat, and it was closed sixteen months later having never landed.

Arize offered OpenInference in May 2026, and the governance committee accepted it in June.

The two lines at the bottom used to be on this slide and are now yours to say. Read what was actually donated. It is a code grant: the instrumentations, not the project, and the OpenInference specification and semantic conventions are explicitly out of scope. OpenTelemetry keeps its own.

So the instrumentation consolidates and the attribute names do not. Not by this route. Which is why the thing in the middle of your pipeline still has work to do.

⚑ Dates and outcomes checked against the issues on 2026-08-17: #2571 opened 2025-02-13, closed 2026-06-16 unlanded, with "we would love to work with you in the GenAI SIG". #3467 opened 2026-05-23, GC voted to accept 2026-06-16. If asked what this means practically: your llm.model_name does not become gen_ai.request.model because of the donation. And here is the twist worth landing: Traceloop's code donation never landed, and they converged the vocabulary anyway. OpenLLMetry 0.62.3 emits gen_ai.* natively, on the current revision. So convergence happened without the donation, which is the opposite of what the issue timeline would lead you to expect. The slide title is still right, just not for the reason you would guess: the code consolidated by grant, and the vocabulary consolidated by someone deciding to.

---

## 20 · A collector processor that renames as it passes

<sub>HTML deck: “The gen_ai_normalizer” · slide 20</sub>

So if the vocabularies differ and OTel is the target, something has to translate. This is that something, and it is worth introducing properly because it does a lot of work in the rest of the talk.

It is a processor in the OpenTelemetry Collector — contrib, and it is in the build we run, 0.158.0. It reads spans as they pass through and rewrites vendor attribute names into the GenAI conventions. llm.model_name becomes gen_ai.request.model. llm.token_count.prompt becomes gen_ai.usage.input_tokens.

Three things about it. It ships with sources for OpenInference and OpenLLMetry, and you can define your own, so a framework nobody has heard of is a config block rather than a fork. It needs no application change and does not care what language you wrote in, because it acts on telemetry rather than on code. And it is alpha and traces only: metrics and logs pass through untouched, which matters because our evaluation events are logs.

The reason this matters beyond convenience: it makes a wrong convention a configuration change rather than a rewrite. The next three slides do exactly that: where you can put it, what it looks like on a real span, and the half of the job it cannot do.

⚑ Version: introduced in contrib 0.153.0, and 0.158.0 is what our collector image actually is. If you quote a version, quote the one you ran.

⚑ That is the real config, copied out of observability/collector/values.yaml, so it is the thing that produced every measurement in this talk. Two details in it worth a sentence each if anyone asks. remove_originals is false deliberately: with it true the processor deletes each attribute it managed to map, so the span that arrives shows only the leftovers it could not translate, which reads like the library emitted an odd subset. False means one span carries both vocabularies side by side, which is what makes the before-and-after slide possible. And it is enabled on every pipeline, including traffic that does not need it, because a span already in gen_ai.* passes through untouched — so one collector serves all three agents with no per-service routing.

---

## 21 · Downstream in the pipeline, or upstream in the SDK

<sub>HTML deck: “Two places to fix it” · slide 21</sub>

There are two places to fix a vocabulary problem, and they're both legitimate.

Downstream, in the collector: you don't touch the applications, it works for any language, and the policy lives in one place your platform team already runs.

Or upstream, in the SDK: cleaner data at the source, but per-framework, and today largely Java-only.

Both target OpenTelemetry's names. Platforms will mostly want the collector.

⚑ Arconia is the upstream example — Thomas Vitale's work. One property, and Spring AI re-emits under a different convention with no code change.

---

## 22 · The wrong vocabulary, fixed in flight

<sub>HTML deck: “Before / after” · slide 22</sub>

So here is the collector doing it, on a real span.

This is a Python agent instrumented by OpenInference — you will meet it properly in the demo, as beaver-sre. It emits no OpenTelemetry vocabulary whatsoever. llm.provider, llm.model_name, llm.token_count, and its own idea of what kind of span this is.

One processor in the pipeline, and the names change in flight. Thirty-nine source attributes come in; seven gen_ai.* attributes get written.

We deliberately keep the originals, so you can see both. Turn that off and it deletes whatever it managed to map — which leaves only the leftovers on the span, and reads like the library emitted an odd subset.

One rides straight through: llm.system. It's simply not in the mapping table.

⚑ Alpha, traces only, no auto-detection — but the OpenTelemetry Demo runs this processor too. The span is still named messages.create: the operation name is an attribute, not the span name.

⚑ The measurement, off the slide: 39 source attributes in, 7 gen_ai.* written, originals kept on purpose. remove_originals: true deletes whatever it managed to map and leaves the leftovers on the span, which is worse than either extreme.

⚑ And the caveat: llm.system rides through either way because it is not in the mapping table. The processor is alpha and traces only. If that makes the room nervous, the OpenTelemetry Demo runs it too.

---

## 23 · It converts the attributes, not the result.

<sub>HTML deck: “The half it cannot carry” · slide 23</sub>

And it converts more than you'd expect. Not just the model call — the whole shape. Its agent span becomes invoke_agent. Its tool spans become execute_tool. The tool name, the call id, the arguments all come across.

Then look at what doesn't.

The tool's result travels in a key called output.value, and there is no entry for it in the mapping table. So the arguments convert and the result doesn't.

Hold that thought, because beat 5 arrives at the same missing half by a completely different road — the MCP path. A normalizer answers vocabulary drift. It does not answer forensic content.

⚑ Read at contrib 0.158.0. We haven't filed it — fair thing for someone in the room to pick up.

⚑ Off the slide, and this is the sentence that matters: the tool's result travels in output.value and mappings.go has no entry for it. Same missing half beat 4 found by a different road. A normalizer answers vocabulary drift; it does not answer forensic content.

---

## 24 · This much arrives without you doing anything

<sub>HTML deck: “What a conforming run gives you” · slide 24</sub>

Before the incident, the baseline: this is what a conforming instrumentation gives you for nothing.

This arrives without you writing a line of instrumentation. The operation, the provider, the model, the token counts in and out, the finish reason. Plus the structural spans: invoke_agent, chat, execute_tool.

That's a conforming stack doing its job. Captured verbatim from a real run — nothing on this slide was hand-written.

If you're starting from nothing, this is a lot of value for one dependency.

⚑ 983 input tokens reproduces — it's the deterministic first call. The output count and the response id change every run, which is beat 1's non-determinism turning up in our own slide.

⚑ Provenance, if challenged, and worth having ready: this is captured verbatim from a capybara run on quarkus-langchain4j 1.12.2, plus the structural spans invoke_agent, chat and execute_tool. Nothing was hand-written — it is what the extension emits on its own.

⚑ The callout absorbs two slides that used to follow this one and broke the flow: the conventions moved house in June into semantic-conventions-genai, which still has no release, and not one GenAI attribute is marked Stable. Say both as an aside here rather than stopping for them. Detail is on the HTML deck’s appendix (`presentation/index.html`, slides 48–72) — not in this deck, so open that if the floor pushes cards if the floor wants it: 188 stability markers in the model, all Development, and a README whose schema URL still reads TODO.

---

## 25 · Rows went missing  <sub>section 04</sub>

<sub>HTML deck: “Divider — 04” · slide 25</sub>

Beat four, and this is where the talk turns. Everything so far has been how agents are built and how they describe themselves. Now something breaks and we find out what that description is worth.

The setup is deliberately small, and this is the paragraph that used to be printed here: five customer records in a Postgres table, three agents that can read it built on three different stacks, and one coding agent that deleted three of those records. Nothing in the telemetry says so yet.

All three investigators hold the same four tools, and they are on the slide because they matter later. Three of them read. One of them deletes. The one in navy is audit_log, and that is the tool that answers who.

Watch for the moment where all three agents agree on what the data looks like now, and not one of them can tell you how it got that way.

⚑ This was two slides until we noticed they were both numbered 04 and both doing the same job. If asked why the agents are capybara, beaver and otter: because they are the same experiment three times with one variable changed, and naming them after the variable would have been unmemorable.

---

## 26 · It deleted the rows. The incident is over. Now prove why.

<sub>HTML deck: “The morning after” · slide 26</sub>

Here's the situation this talk is about.

Rows are gone. The incident is over — nobody's asking you to stop it. They're asking you to explain it. Why did this happen, and can you prove it.

And you go looking. The logs say the call succeeded. The trace says it took four seconds. Neither of them says what it was thinking, or what it actually touched.

That gap — between “something happened” and “here is why” — is the whole talk. Everything else is us trying to close it with the tools we already have.

⚑ Don't name a culprit here. The reveal later is that no agent did this, and saying otherwise now contradicts that in twenty minutes.

---

## 27 · Something deleted production data. No agent admits to it.

<sub>HTML deck: “The demo setup” · slide 27</sub>

Spend a moment here, because every later trace comes back to this picture.

Bottom row, three investigators. capybara-sre is Java on quarkus-langchain4j and gets scored by a second model. beaver-sre is Python instrumented by OpenInference, normalized at the edge by the collector. otter-sre is the same Python agent instrumented by OpenLLMetry, which as of this week already emits the conventions. Same prompt, same tools, three vocabularies.

The bar above them is what makes that a fair comparison. All three call the same four tools on the same MCP server, so the tool body runs in the same other process for all of them and the only thing that differs is what writes the telemetry. That was not true a day ago, and fixing it changed the result, which we come to shortly.

Middle, one Postgres table with an audit trail recording the client name and the database role.

Top, the one way the rows disappeared. A developer asked their own coding agent to tidy up the free plan, and it did, through an MCP server holding deploy_svc credentials. Nobody gave the agent anything. The credential was already in a .env file or a password manager, it carries DELETE because a deployment account needs DELETE, and the tool inherited every bit of that.

Right rail, one collector, the normalizer, the backends. Every box on the left exports there, which is why we can compare them at all.

⚑ Stage direction, and the only one in this deck that matters under pressure. The deletion is a real goose run against a local model, so it is the step that can fail on the day: ollama not running, the model not loaded, or the model simply never calling the tool. Do not debug it in front of the room. curl -X POST localhost:8088/incident/rehearse-deletion puts the database in exactly the same state with the same deploy_svc credentials, and everything after this slide works unchanged. What you lose is goose's own telemetry, so skip "What the coding agent recorded" and say you are showing the investigation side. Full detail in demos/README.md, under The extra door.

---

⚑ **Absorbed from a slide this deck no longer has** — “One question, one loop”, the four-process sequence diagram that used to sit here. Say it over this slide, because nothing else carries it:

> Four processes: the agent, the model over HTTPS, the MCP server, Postgres. The model never runs anything — it answers with a request, *call audit_log with a limit of twenty*. The agent makes that call over MCP, and the trace context rides inside the request’s `_meta`, which is how four processes end up in one trace. Two things to take away. The agent never sees the database, the credentials or the SQL — it asks for a tool by name and gets text back. And the only moment the answer to *who deleted the rows* exists is inside the MCP server, for a few milliseconds, in a process that is not the agent.

That second point is what beat 05 pays off, so it is worth thirty seconds here.

---

## 28 · It’s demo time! — the cast

<sub>HTML deck: “Divider — Demo” · slide 29</sub>

Slides down, terminal up. This is the demo.

The cast, left to right. capybara-sre, Java on quarkus-langchain4j, and the only one with a judge. beaver-sre, Python instrumented by OpenInference. otter-sre, the same Python agent instrumented by OpenLLMetry. All three hold the same four tools on the same MCP server, so the only difference between them is what writes the telemetry. And goose, on the right, which is the one that did it.

What to run: the deletion, then the same question to each investigator, then the traces side by side.

Tell the room what to watch for before you start, because it is easy to miss while three consoles are moving. All three investigators will agree on what the table looks like now. Ask them how it got that way and the answers stop matching. Everything after the demo is us catching up on why.

⚑ If goose or ollama misbehaves, the extra door is curl -X POST localhost:8088/incident/rehearse-deletion. It leaves the database in the same state and costs you the coding-agent telemetry, nothing else.

⚑ Say this while the joined trace is on screen, because it replaces two slides that used to carry it. The trace only crosses the MCP boundary because context propagates, and that is not free: traceparent rides in the request's _meta, and quarkus-mcp-server reads it for the MCP span and then drops it before the tool body runs. Which means the SQL that touched the rows started its own trace until we extracted traceparent from _meta ourselves and re-parented it — twenty lines, no fork, and the protocol was already carrying what we needed. If you want the gap live, CAPYBARA_MCP_PROPAGATE_CONTEXT=false. Two slides in the HTML deck’s appendix have the code and the before-and-after span counts.

---

## 29 · Three agents, three vocabularies

<sub>HTML deck: “What each agent emits” · slide 30</sub>

These are the attribute counts from the run you just watched, and the three agents are comparable: all of them now call the same four tools on the same MCP server, in the same other process. The only thing that differs is what writes the telemetry.

Model call, left to right. Our Java stack: twelve gen_ai attributes, and the two carrying the conversation are gen_ai.prompt and gen_ai.completion, which no longer exist in the conventions. Beaver on OpenInference: sixty-seven attributes, because the originals are still there beside the seven the collector wrote. Otter on OpenLLMetry: fifteen, natively, with the current message shape.

Now the tool span, which is the row that matters. Capybara's names the tool and stops. Beaver's carries the arguments but not the result, because the mapping has no entry for the result. Otter's carries both.

And then the strip along the bottom, which is the same in all three runs. The MCP server's own span for that tool call has twelve attributes, two of them gen_ai, and neither is the arguments or the result. Count the MCP implementations in this picture: the Java client, the Python SDK client, and the Java server. Three, by three different vendors, and not one records what the tool was given or what it gave back. The convention defines both attributes, for exactly these spans, and marks them opt-in. Everybody took the opt-out.

So the only telemetry here that can answer what the agent actually did is the telemetry we wrote by hand. That is the talk in one slide.

⚑ If asked why the counts are not round: the Python agents' tool spans are ours, hand-written, because nothing auto-instruments a loop somebody wrote. That is the point rather than a caveat, and it is why the vocabulary differs between beaver and otter while the loop is byte-identical.

⚑ Precision if anyone asks whether OpenLLMetry is *fully* compliant, because the honest answer is no and it is a better answer. Measured on 0.62.3: every attribute is gen_ai-prefixed and there is no llm.* or traceloop.* anywhere in the package, so there is genuinely nothing to translate. But fourteen of its fifteen gen_ai keys are in the registry, not fifteen — gen_ai.usage.total_tokens is absent from the specification entirely, and it is the sum of two attributes that are defined. Its span is named anthropic.chat, where the convention and the Anthropic-specific page both say {gen_ai.operation.name} {gen_ai.request.model}, so it should read chat claude-sonnet-4-6. And its event emitter still writes gen_ai.user.message and gen_ai.choice, event names from the superseded 2024 revision, on a path this demo never enables. So: right vocabulary, not yet right in every detail.

⚑ And one scope correction that matters if someone knows this library. Traceloop's shared conventions package is installed and defines sixteen traceloop.* attributes — entity name, entity input and output, association properties, the prompt-management keys. We do not see any of them because we drive AnthropicInstrumentor directly and never install traceloop-sdk, which is the component that writes them. Adopt OpenLLMetry the normal way, through the SDK, and traceloop.* is what you get on top. So "nothing to translate" is true of the configuration we run, and we chose that configuration deliberately to isolate the vocabulary. The instrumentation itself references exactly four constants from that package and all four resolve to gen_ai names: is_streaming, request.structured_output_schema, response.finish_reason and usage.total_tokens. Three of those four are not in the OTel registry, and the fourth is singular where the registry says finish_reasons.

---

## 30 · One column needs translating. The other two do not.

<sub>HTML deck: “Seven facts, three sets of names” · slide 31</sub>

Before we fix anything, here is the problem stated as plainly as it gets.

Seven facts about one model call. The model, the provider, what went in, what came back, the token counts both ways, and the tools it was offered. Every one of the three agents recorded all seven. Nobody is missing information here.

Now read across. capybara on the left and otter on the right already agree, almost character for character, because both are on gen_ai names. The middle column is OpenInference, and it is different every single row. llm.model_name for the model. llm.token_count.prompt for the input tokens. llm.tools, numbered, for the tool definitions.

That is the whole difficulty and also the whole opportunity, because look at what kind of difference it is. It is not a missing fact or a different meaning. It is a rename. Seven renames. Which is exactly the kind of work you can do somewhere in the middle rather than asking forty vendors to agree.

⚑ Two honest caveats if pressed. capybara's row for what went in says gen_ai.prompt, which is a gen_ai name and also the wrong one, since the spec removed it — agreeing on a prefix is not the same as agreeing on a key. And the starred rows are families rather than single attributes: OpenInference writes one attribute per message and per tool, so llm.input_messages.* was 32 attributes on the run you just saw.

⚑ Spoken rather than printed: seven facts, every one of them recorded by all three. Which is why this is a job for something in the middle of the pipeline rather than a request to forty vendors.

⚑ Stage direction, if the demo is running well and you have thirty seconds. The middle column is the one the normalizer rewrites, and beat 3 showed that as a mapping table — here you can show it on the real thing. Open beaver-sre's chat span in Jaeger and both vocabularies are on it side by side, llm.model_name next to gen_ai.request.model, llm.token_count.prompt next to gen_ai.usage.input_tokens, because remove_originals is false.

⚑ While you are in that span, the limit is visible too and it is worth pointing at: the tool span's output.value has no gen_ai name to be renamed into, so it stays as it was. Seven renames and one thing with nowhere to go, which is where beat 5 lands.

---

## 31 · What did it actually do?  <sub>section 05</sub>

<sub>HTML deck: “Divider — 05” · slide 32</sub>

Which brings us to the question the incident actually needs answered.

---

## 32 · invoke_agent: 19.05s, 21 spans, and the answer is in 63 milliseconds of it

<sub>HTML deck: “The capybara incident, as a trace” · slide 33</sub>

This is the investigation, as a trace. Nineteen seconds, twenty-one spans.

The two thin bars are the tool calls. Fifty-five milliseconds and eight milliseconds — sixty-three between them. Nought point three percent of the trace, and the only part that answers the question.

Everything wide is the model thinking, or the judge judging.

That's the shape of an agent trace: almost entirely waiting, with the decisive part too small to see.

And the SELECTs those two tool calls ran? They're not in this trace at all. Hold that thought.

⚑ All measured off one run — don't promise the numbers reproduce. The widest bar is usually the HTTP POST under the model call: free from your existing instrumentation, and carrying no GenAI meaning. Here that's 2.35 of the 2.51 seconds.

⚑ The numbers, now spoken rather than printed: two tool calls, 63 milliseconds together, 0.3% of the trace — and the only part that answers the question. Everything wide is the model thinking or the judge judging.

---

## 33 · The answer is in the result, not the arguments

<sub>HTML deck: “The two attributes that answer it” · slide 34</sub>

So what would have answered the question?

Two attributes. And notice which one carries the weight here: the arguments are trivial — a limit of twenty. It's the result that holds the entire case, because the result is the audit rows, naming a database role that is not this application.

Which is the awkward part of this whole talk. The half you'd least want to log by default is exactly the half that identifies the culprit.

Our MCP run emits neither. Same binary with local tools, and both are there.

⚑ Precision if challenged on the requirement level: both attributes are marked Opt-In, the lowest level the spec has, and carry a warning that they may contain sensitive information. The flat “instrumentations SHOULD NOT capture this by default” sentence exists too, but it is written about instructions, input messages and output messages, not about these two. Same practical outcome, off unless you ask, but do not quote the stronger sentence about this pair.

⚑ Two lines that used to have slides of their own. With default instrumentation you can prove the span fired; you cannot prove what it executed. And if anyone offers the model's output as a rescue: gen_ai.output.messages carries the tool call and its arguments, but it's what the model asked for rather than what ran. The outcome arrives one turn later, in the next call's input messages.

⚑ One more thing now true that was not: the context workaround in the HTML deck’s appendix (`presentation/index.html`, slides 48–72) — not in this deck, so open that if the floor pushes gives the MCP server its own execute_tool span, which is exactly the right place to hang these two attributes. So the server side now has somewhere to put the evidence. We have not built that — say so if asked, because it is the obvious next step and pretending otherwise is the kind of thing this talk is against.

---

## 34 · The agent that did it wrote down what it deleted

<sub>HTML deck: “What the coding agent recorded” · slide 35</sub>

Now the other side of the incident. Everything so far has been our own agents investigating. This is the telemetry from the agent that actually did the deleting, and it is a coding agent on a laptop talking to a local model.

Seven spans for one run. reply at the top, reply_stream under it, then the model calls and the tool calls interleaved, because that is what an agent loop looks like from the inside. And the second dispatch_tool_call is the one that matters.

Look at what it recorded. Operation name execute_tool, tool name production_db__delete_records, the arguments, plan equals free. And then the result: DeleteResult, deleted three, remaining two. That is the confession, written down by the agent that did it, with no configuration from us beyond turning content capture on.

Hold that against the last three slides. Our platform framework, over the same protocol, calling a tool on the same kind of server, records the tool's name and stops. A coding agent from a different company, in Rust, records what went in and what came back. The gap is not the protocol and not the language. Somebody decided to write it down.

Two catches, because this is not a sales pitch. Its MCP server's spans landed in six separate single-span traces: goose does not propagate trace context over MCP, so the client half and the server half never meet. The Python SDK does that correctly, and this one does not. And the token totals appear three times in the same trace, on the two parent spans and again as the sum of the children, so anyone summing naively triples the cost.

So the scoreboard for the whole talk is this: the coding agent has the content and not the correlation, our framework has the correlation and not the content, and nobody has both.

⚑ Numbers are from a real run, 2026-08-17: 6261 input tokens, 339 output, three provider calls, two tool calls. The audit trail for the same moment reads client=goose, db_user=deploy_svc.

⚑ This is the slide to skip if the goose run did not happen and you used the rehearsal endpoint instead. There is no telemetry to show, and inventing some is the one thing this talk cannot do.

⚑ Say the comparison: both attributes, on the span that ran the tool. Our own framework, over the same protocol, records neither.

⚑ Both catches were a band on this slide and are now yours to say; both re-measured 2026-08-17 after Kasper challenged them, and the first one was stated loosely. It is not "six traces" — that was one window. Across three runs prod-db-mcp produced sixteen traces and every single one is one span with no parent: initialize, notifications/initialized, tools/list, both tools/call spans, and the SQL. What matters is that tools/call delete_records is itself a ROOT on the server side, which is the proof rather than an inference: the server had no incoming context to parent to, so goose sent none.

And there are two separate failures stacked on this path, worth separating if asked. Goose does not propagate into MCP at all, so the server's tools/call span is orphaned from the agent. And then the server loses context again into the tool body — quarkus-mcp-server #789, still open — so the SQL is orphaned from the tools/call span too. Our own Java agent only suffered the second one, and we closed it by reading traceparent out of _meta ourselves — there are two slides in the HTML deck’s appendix on that if it comes up. Goose's half is not ours to fix: it sends no context at all, so there is nothing on the wire to recover.

On the tokens: 1867 plus 2137 plus 2257 is 6261, which is exactly what reply_stream reports and exactly what reply reports. So the same total is on both parents and in the children. Say "summing across spans counts it three times" rather than "triples your bill" — a tool that reads the root span, or metrics, gets it right.

---

## 35 · It records what it concluded, and what it did next

<sub>HTML deck: “What the model asked for” · slide 36</sub>

One more place to look before we admit what is missing: the model's own output, which is where its reasoning lives.

gen_ai.output.messages is the attribute that replaced gen_ai.prompt and gen_ai.completion, and it is structured. Parts. Here a reasoning part, two rows left, check who removed the rest. Then a tool_call part, audit_log with a limit of twenty. And a finish reason that says the model stopped because it wanted a tool.

So this is the agent's perspective on its own investigation: what it concluded so far, and what it decided to do next. It is the closest thing in the conventions to why.

And notice it carries the tool name and the arguments, which is content the execute_tool span did not have. That looks like a rescue, and it is not, twice over. It is what the model asked for rather than what ran, and the outcome is one turn later. Given the last two slides, that second point is the one that bites, because the evidence was in the result.

⚑ A reasoning part only appears when the model emits thinking. Our run carried text and tool_call, so do not imply it is always there.

And that is the handover into the last part. We can now read what the agent concluded and what it chose to do about it. Nothing we have looked at tells us whether either was any good — whether the diagnosis was right, or whether taking no action was the correct call. That is a different question from what happened, and it needs a different mechanism.

⚑ Say it rather than read it: that tool_call part carries the name and the arguments, which is content the execute_tool span did not have. It still is not a rescue, because it is what the model asked for rather than what ran, and the result only turns up in the next call's messages.

---

## 36 · No convention has a field of why

<sub>HTML deck: “Three things you still cannot get” · slide 37</sub>

Before we ask whether the agent did a good job, here are the limits of what we have just shown you, because two of them are permanent.

The convention has a field for the tool name, the arguments and the result. It has no field for why that call was made. That one is a gap in the specification, and it is fixable — the SIG is explicitly asking for feedback on agentic scenarios, so it is the most useful thing you could take from this talk and act on.

The other two nobody can fix. You cannot replay the context window: it is not persisted, and the model is not deterministic, so re-running it does not reproduce the decision. And chain-of-thought is output, not an audit trail. It is a narration the model produced alongside the decision, not a record of how the decision was made, and treating it as evidence is a category error that will eventually embarrass somebody in a post-mortem.

The bottom row is what changed while we were building this. There is now a plan span, for the phase where an agent decides what to do before doing it. So the spec has grown somewhere to put the decision. It still has nothing that records the reason, and only two libraries emit the span at all.

⚑ Do not lead with "normalizing cannot create a field that does not exist" — it is true and the room will find it obvious. The weight is on the two you cannot recover.

⚑ OTel can carry narrated reasoning: there is a ReasoningPart in the message schema, on input and output both. What it cannot carry is why. Keep that distinction crisp; it is the difference between a real gap and a misreading.

---

## 37 · Was it any good?  <sub>section 06</sub>

<sub>HTML deck: “Divider — 06” · slide 38</sub>

One question left. The agent gave an answer — was it any good?

---

## 38 · LLM as a judge is just another model call

<sub>HTML deck: “What an LLM judge is” · slide 39</sub>

LLM-as-a-judge sounds like a technique. It's a second model call.

You take what the agent did — the prompt, the tool calls, the answer — and you hand it to a model with a rubric. Score this. Did it find the root cause. Was the remediation safe.

That's it. No framework required.

And yes, this runs in our demo. There's a judge that reads the completed investigation and returns two scores, and those become the evaluation events we're about to look at.

⚑ The judge is given ground truth in its rubric — it knows the deploy_svc role did it. Without that it would be grading plausibility rather than correctness, which is a different and much weaker claim.

⚑ Yes, this runs in the demo — CapybaraJudge — and what it returns becomes the gen_ai.evaluation.result events on the next slide.

---

## 39 · gen_ai.evaluation.result

OpenTelemetry already has a shape for this, and it surprised us.

gen_ai.evaluation.result. A name, a numeric score or a label, and an explanation.

Here's the part most implementations get wrong, us included until recently: this is an Event in the logs data model. A log record. Not a span event.

It should be parented to the operation it's judging, or carry the response id if you don't have the span.

And there's still no standard span for “an evaluation happened”. There's an open proposal.

⚑ Three different things get called events around here: the spec's log records, span events, and the tab Jaeger labels “Logs” — which shows span events. That naming is exactly why the wrong shape looks right. Callback to Stable: zero — error.type is the only Stable attribute near this event, and only because it's a general OTel one.

⚑ Callback worth making if the room remembers "Stable: zero": error.type is the only Stable attribute anywhere near this event, and only because it is a general OTel attribute rather than a GenAI one.

⚑ Four bullets came off this slide when the attributes moved into the code block with their explanations, because the block now says all of it. Spoken, they are: four gen_ai.evaluation.* attributes plus two general ones, response.id and error.type. It is an Event in the logs data model — a log record, not a span event. It SHOULD be parented to the span being evaluated, or carry gen_ai.response.id when there is no span id to hand. And there is no standard span for an evaluation having happened, which is what PR #185 proposes.

---

## 40 · A number you improve, and a gate you don’t cross

<sub>HTML deck: “Two judgements on one span” · slide 41</sub>

Two judgements, on one run.

One is a number you improve: did it find the root cause. The other is a gate you don't cross: was the remediation safe. A score and a label, and they're doing different jobs.

Both correlate back to the agent's span by trace and span id.

Two things conformance cost us, and they're the interesting part. Without an explicit timestamp the record lands at epoch zero — one backend fell back gracefully and hid it from us.

And because these are logs, they don't appear in Jaeger at all. We wrote the shape the convention asks for, and no trace viewer renders it.

⚑ Measured repeatedly at 1.0 and pass on the investigation: it finds the role in the audit trail and takes no destructive action. Don't promise a specific pair of numbers — under an earlier scenario the same rubric gave 0.7 then 0.6 on consecutive runs.

⚑ Measured repeatedly on the investigation: it finds the role in the audit trail and takes no destructive action. Two things conformance cost us, both worth admitting if asked. Without an explicit timestamp the record lands at epoch 0. And because these are logs they do not appear in Jaeger at all — we bought a shape no trace viewer renders.

---

## 41 · The further from the decision, the less it can see

<sub>HTML deck: “Where the judge sits” · slide 42</sub>

One thing to be clear about before we finish, because our demo shows one option and it is not the only one, or even the usual one.

In our demo the judge is a second model call inside the agent's own run. That is the left column. It can see everything, because it is in the same process as the decision: the prompt, the tool arguments, the results, all of it, whether or not any of that reached a span. It costs the agent's latency and tokens, and it only ever judges that one agent.

Second option: put it in the collector. A processor reading GenAI telemetry as it passes. Now you get one evaluation policy across every agent in the estate, which is the platform team's dream. And notice what it can see: only what was emitted. Which means everything in the first half of this talk decides what is judgeable at all. If the tool result never made it onto a span, no collector-side judge can score whether the tool did the right thing.

Third: in the backend, as a job over stored traces. That one can do what neither of the others can, which is look backwards — re-score last month against a new rubric, compare across releases. It can never block anything, and it is furthest from the decision.

The gradient is the point. The closer to the decision, the more it sees and the narrower its reach. The further away, the broader its reach and the more it depends on your conventions being right.

⚑ There is a second axis, and do not conflate them: this slide is about *where* the judge runs, and there is also *when* — offline before deploy, online and sampled, or inline gating the response. The appendix has a slide on that if it comes up.

⚑ Ours is the in-process one, which is the least realistic of the three and buys us an advantage — admitted in the guardrail below rather than on a slide of its own.

⚑ This absorbs the slide that used to follow, and it is the honesty pass — say it here rather than showing a list. Ours is not a reference architecture, in five specific ways. We judge in-process and synchronously, where real setups evaluate offline against stored traces. Because it is in-process the judge sees tool arguments and results our own spans never carried, which is an advantage it loses the moment you move it. All three agents call the same tools over MCP now, but their tool spans are hand-written, so that comparison is partly of our code rather than their libraries. The judge is biased — position, verbosity and self-enhancement are all documented. And the mitigation is a human-labelled gold set with Cohen's kappa rather than raw agreement.

⚑ The line worth landing whichever way you tell it: "good enough" is a risk-calibrated product decision, not a number the tooling hands you.

---

## 42 · Wrapping up  <sub>section 07</sub>

<sub>HTML deck: “Divider — 07” · slide 43</sub>

That is the whole argument. What is left is what to do about it.

Three things: an order of operations that does not start where you would expect, the cheapest experiment in the talk, and one sentence to take away.

---

## 43 · A realistic path, in the order that actually works

So what do you actually do on Monday.

Step one is the counterintuitive one: don't start by rewriting instrumentation. Start by collecting what you already emit, in whatever vocabulary it arrives in.

Then normalize in the collector, because that's one config change instead of forty pull requests.

Then — and this is the step that bit us — turn the tool content on, and verify it fired. Those are different jobs. We had a flag set for weeks that wasn't doing anything.

Evaluation comes last. It's the newest shape here and the one most likely to change.

⚑ If asked where evaluation should run: inline adds latency to every request, online adds production cost so sample it, offline is where a gold set belongs. Our two dimensions are one of each shape.

⚑ Two asides that were printed and should be spoken. Step 1 is the counterintuitive one: do not start by rewriting instrumentation. Step 3 is the one that bit us: turning it on and verifying it are different jobs.

⚑ Checked against everything we measured, and all five steps still hold. One caveat to have ready on step four, because "no new pipeline" is true of emitting and not of reading: gen_ai.evaluation.result is a log record, so it attaches to the span by trace and span id but a trace viewer will not draw it. Jaeger shows nothing. You need a backend that correlates logs to spans, or you query the logs directly. Conformance bought a shape that is correct and invisible.

⚑ And on step three, from a measurement this week: the tool result is recoverable from the next model call's messages even when the tool span does not carry it, so "verify it fired" means checking the span you intend to query, not just that the data exists somewhere in the trace.

---

## 44 · The agent worth watching first it the one on your laptop

<sub>HTML deck: “Watch your own coding agent” · slide 45</sub>

One last thing, and it's the cheapest experiment in this talk.

The agent worth instrumenting first isn't in production. It's the one on your laptop, editing your repository, running your commands. Claude Code, Copilot, Cursor — they take an OTLP endpoint, and they'll tell you token spend, tool calls, session length.

Point it at the collector you already run. It costs about ten minutes.

And it's the same forensic question as everything else today, one layer closer to home: your coding agent changed something. Can you prove what?

⚑ This is the AAIF ambassador tie-back from the intro. Ten minutes is honest — it's an env var and an endpoint.

⚑ Corrected 2026-08-13 against Goose's own docs. GOOSE_TELEMETRY_ENABLED is anonymous usage analytics, a different thing, and off by default. OTel export needs no Goose-specific flag: set OTEL_EXPORTER_OTLP_ENDPOINT and it exports, with OTEL_{SIGNAL}_EXPORTER for per-signal control. That is a better story than a vendor flag, so say it that way. And a detail worth having ready, because it dates well: goose emitted no gen_ai.* attributes at all until two PRs merged four hours after 1.45.0 was cut. Both shipped in v1.46.0 on 2026-08-12, verified against the tag, so a plain brew install now gives you sixteen gen_ai.* attributes including tool call arguments and results, behind the convention's own opt-in variable OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT. Which sets up an awkward comparison worth making out loud: the coding agent on your laptop is more conformant than the framework in beat 4.

⚑ There is no Claude Code mark in assets/ yet, so that card is typographic while goose has its mascot. Drop a logo into assets/ and the card takes it the same way.

⚑ The line that used to be printed here, and it is the one to say: one environment variable each. The agent editing your code lands in the collector you already run — same spans, same conventions, same pipeline as everything else in this talk.

---

## 45 · Build the footprints before you need them.

<sub>HTML deck: “Close” · slide 46</sub>

Build the footprints before you need them.

Everything we showed you today was reconstructing an incident with telemetry that was already there, or discovering it wasn't. The flags, the conventions, the evaluation events — all of it is cheaper to turn on now than to wish for at two in the morning.

The conventions are Development. They'll move. Turn them on anyway.

Thank you.

⚑ QRs and links on screen. Everything measured today is in the repo, with dates and versions.

⚑ The links and the QR codes used to be on this slide and are now on the thank-you after it, so there is one slide people photograph rather than two. If someone asks for the repos before you get there: github.com/open-telemetry/semantic-conventions-genai for the conventions, and the opentelemetry-demo for an agentic stack wired end to end.

---

## 46 · Thank you.

Thank you. Both of us are here for the rest of the day.

The QR codes are how to find us — Adriana's goes to her socials, mine to LinkedIn. The repository has the slides, the whole demo, and an ANALYSIS file with every measurement in this talk, dated, including the ones that contradicted what we expected.

If you take one thing away, take the last slide's line. And if you take two, the second is that the conventions need people who actually run this stuff to tell the SIG what is missing.

⚑ Do not read the QR labels aloud. Leave this slide up for questions; it is the one people photograph.

---
