# Your Agent Did What?

**Forensic Observability for Systems That Don't Leave Obvious Footprints**
Conference talk by **Kasper Borg Nissen** & **Adriana Villela** — on OpenTelemetry, GenAI
semantic conventions, and observing autonomous agents.

> The GenAI observability space is fragmented — OpenInference, OpenLLMetry,
> framework-specific conventions all naming the same things differently. OpenTelemetry is
> where it converges. This talk maps that landscape honestly, shows how to bridge the gap at
> the collector (`gen_ai_normalizer`), and then asks the harder question: something just
> deleted a database — what does your telemetry actually tell you?

First delivery **SREday London**; then **OSS Summit EU** (October).

---

## The cast

<table>
<tr>
<td width="150" align="center"><img src="mascots/capybara-investigating.png" width="120" alt="Capybara SRE"></td>
<td><strong>Capybara, SRE</strong> — <em>"Deploy Calmly"</em><br>
Java · Quarkus + LangChain4j · tools over MCP · PostgreSQL · judged by an LLM.<br>
Emits <code>gen_ai.*</code> from the framework, and loses the tool call's content on the MCP path.</td>
</tr>
<tr>
<td width="150" align="center"><img src="mascots/beaver-dashboard.png" width="120" alt="Beaver SRE"></td>
<td><strong>Beaver, SRE</strong> — another team, another platform<br>
Python · Anthropic SDK · instrumented by OpenInference · reads the same database.<br>
Emits no OTel vocabulary at all; the collector rewrites it in flight — most of it.</td>
</tr>
<tr>
<td width="150" align="center"><img src="mascots/otter-tablet.png" width="120" alt="Otter SRE"></td>
<td><strong>Otter, SRE</strong> — the same Python agent, a third vocabulary<br>
Python · Anthropic SDK · instrumented by OpenLLMetry · same tools, same MCP server.<br>
Emits <code>gen_ai.*</code> natively and needs no normalizing at all — the only one of the three
that records what a tool returned.</td>
</tr>
<tr>
<td width="150" align="center"><img src="mascots/goose-walking.png" width="120" alt="goose"></td>
<td><strong>goose</strong> — a developer's own coding agent, and the one that did it<br>
Asked to tidy up the free plan. It calls <code>delete_records</code> on an MCP server holding
<code>deploy_svc</code> credentials, which carry <code>DELETE</code>. Nobody granted the agent
anything; the root cause is a grant rather than a bug.</td>
</tr>
</table>

The three SRE agents are asked the same question about the same incident: *"Customers are
reporting missing accounts. Investigate."* Same tools, same MCP server, same database, same
collector — so anything that differs in the telemetry belongs to the platform, not to the story.
goose is not asked anything; goose is what happened.

The deletion is a real coding-agent run against a local model. When that is inconvenient —
no ollama, or a laptop having a bad day — `POST /incident/rehearse-deletion` reproduces the
database state with the same credentials, so the investigation half of the demo stands on its
own. See [`demos/README.md`](demos/README.md#the-extra-door) for what that door does and does
not give you.

---

## What's in here

| Path | What it is |
|---|---|
| **[`demos/`](demos/)** | **The demo.** Three SRE agents, one coding agent, one incident, one collector — in kind, three commands. Every captured attribute in the talk comes from here. |
| **[`demos/README.md`](demos/README.md)** | How to run it on stage: the flow, what to look at, and what breaks. |
| **[`demos/ANALYSIS.md`](demos/ANALYSIS.md)** | The measurements, with versions and dates. The talk's evidence base. |
| **[`outline.md`](outline.md)** | The talk, slide by slide, aligned to the 46-slide deck: sections, timing, and what each slide must land. |
| **[`abstract.md`](abstract.md)** | The submitted abstract and ecosystem benefits. |
| **[`research.md`](research.md)** | Everything the talk is sourced from: forensics, evaluations, the backend landscape, the state of the standards, and the link list. |
| **[`mascots/`](mascots/)** | 42 cut-out mascots, transparent — capybara, beaver, otter and goose. |

---

## Where the slides live

The talk is delivered from **Google Slides**. This repository holds
[`outline.md`](outline.md) — what each slide has to land, and in what order — and nothing
else about the deck.

Everything else lives **outside this repository**, at `~/Documents/your-agent-did-what/`:

| | |
|---|---|
| `SPEAKER-NOTES.md` | Speaker notes, one section per slide, aligned to the Slides deck. |
| `SLIDES-STYLE.md` | Type, colour and geometry — sizes in px *and* pt, the palette, the page-setup step. |
| `presentation/` | The HTML deck the Slides version was built from, its element exports (backgrounds, diagrams, icons, mascots, the animated normalizer GIF) and the tooling that generated them. |
| `docs/superpowers/` | The specs and plans this was built from. History, not live documentation. |

They are kept out of the public repo deliberately: 71 MB of rendered PNGs, the stage
directions, and a second copy of a deck that is now maintained in Slides.

If you need to regenerate an asset, that directory still works standalone — `python3
check-deck.py`, `./start.sh`, and the `export-*.py` scripts all run from there with no
dependency on this repository.

---

## Run the demo

```bash
cd demos
cp .env.template .env      # then set ANTHROPIC_API_KEY
./00_run.sh                # cluster, database, both agents  (~5 min cold)
./01_start-demo.sh         # port-forwards, waits until they answer
```

Then open **<http://localhost:8088>** and pick an agent. Start with
[`demos/README.md`](demos/README.md) if you are preparing to present.

**Prerequisites:** Docker, kind, kubectl, helm, JDK 21, Python 3.11+, and an Anthropic API
key. `demos/.env` is git-ignored; only `.env.template` is committed.

> Any deploy or `kubectl set env` replaces a pod and takes the port-forward with it, so the
> console appears to die. Re-run `./01_start-demo.sh`. This cost six debugging sessions
> before the script existed.

---

## Verifying the agents in Jaeger

`./01_start-demo.sh` port-forwards Jaeger to **<http://localhost:16686>**. This is where you
confirm the agents actually emitted what the talk says they emit — do it before every
rehearsal, because a silent instrumentation regression looks exactly like a working demo.

**1 · The services are reporting.** The *Service* dropdown should list `capybara-sre`,
`beaver-sre`, `otter-sre`, `capybara-db-mcp`, `prod-db-mcp`, and `goose` once you have run the
recipe. A missing service means that agent has not been asked anything yet, or its exporter
never connected.

> If the dropdown lists services that no longer exist, Jaeger's store is in memory and keeps
> old traces. `kubectl rollout restart deployment/jaeger` clears it — and clears your traces,
> so do that *before* a rehearsal, never during one.

**2 · One question produced one trace.** Ask an agent something, then search that service and
open the newest trace. You want a single trace whose root is `invoke_agent`, containing `chat`
spans and `execute_tool` spans — not a scatter of unparented spans.

**3 · The trace crosses into the MCP server.** Expand an `execute_tool` span: the MCP server's
spans should be *inside* the agent's trace, and the `SELECT` below them. That join only
happens because `traceparent` rides in the MCP request's `params._meta`. To see the failure
mode deliberately, redeploy with `CAPYBARA_MCP_PROPAGATE_CONTEXT=false` — the SQL then starts
a trace of its own and the tool span has nothing under it.

**4 · Each agent speaks the vocabulary it should.** Click a `chat` span and read the tags:

| Service | Expect | Because |
|---|---|---|
| `capybara-sre` | `gen_ai.*` from the framework | quarkus-langchain4j emits them directly |
| `otter-sre` | `gen_ai.*`, natively | OpenLLMetry 0.62.3 already emits the conventions |
| `beaver-sre` | **both** `llm.*` **and** `gen_ai.*` on the same span | the collector normalizes it, and `remove_originals: false` keeps the originals so you can see both |

Beaver carrying both vocabularies at once is the check that the `gen_ai_normalizer` processor
is actually in the pipeline. If you see only `llm.*`, the processor is not running; if you see
only `gen_ai.*`, someone set `remove_originals: true` and the before/after demo is gone.

**5 · The forensic attributes are where the talk says they are.** On a tool span, look for
`gen_ai.tool.call.arguments` and `gen_ai.tool.call.result`. The finding the talk turns on is
that the *libraries* do not write them — only the spans we wrote by hand do. If you suddenly
find them everywhere, an upstream release has changed the story and the slide needs revisiting.

**6 · What will not be in Jaeger, correctly.** The judge's `gen_ai.evaluation.result` is an
**event in the logs data model**, not a span — Jaeger takes spans, so its absence there is the
convention working as specified, not a broken demo. Read those from the collector instead:

```bash
kubectl logs -l app.kubernetes.io/name=opentelemetry-collector -f | grep -i evaluation
```

The same command with no filter is the fastest way to see raw spans arriving, which is what to
check first when Jaeger looks empty.

---

## What the demo demonstrates

Four findings, each measured rather than asserted — all in
[`demos/ANALYSIS.md`](demos/ANALYSIS.md) with dates:

- **The MCP path loses the tool call's content.** 4 span attributes against 6 on the local
  path; no arguments, no result. A *framework* gap, not an MCP gap — say "in this
  framework", never "with MCP".
- **The MCP path also loses the trace, at one named hop.** The tool body runs on a new
  duplicated Vert.x context, so the SQL it issues starts its own root trace.
  [quarkus-mcp-server#789](https://github.com/quarkiverse/quarkus-mcp-server/issues/789),
  open, no ETA. Streamable HTTP was tried and is worse.
- **The normalizer converts the structure, not the result.** AGENT→`invoke_agent`,
  TOOL→`execute_tool`, arguments carried across — and no mapping for the tool's result. The
  same missing half, reached by a different road.
- **Evaluations are log records, not span events.** Which is what the convention asks for,
  and what most implementations get wrong. They do not appear in Jaeger; Jaeger takes spans.

---

## Working in this repo

- Every claim on a slide is either measured in `demos/ANALYSIS.md` or flagged on the slide
  as a position. Change a claim, change the measurement or the flag with it.
- `ANALYSIS.md` records dates and versions and marks superseded captures rather than
  overwriting them. The talk says "we measured this", so the audit trail matters.
- The speaker notes carry the guardrails: which numbers are real, which are the spec's shape
  rather than our capture, and what not to overclaim.
- When a finding turns out to be wrong, the fix is a new measurement — not a softer
  sentence. Two claims in this deck were withdrawn that way.
