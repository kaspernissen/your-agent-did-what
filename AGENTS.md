# Working in this repo

A conference talk: a slide deck, and a runnable demo that every factual claim in the deck
comes from. The unusual constraint is that **the demo is the evidence**. A slide that says
"we measured this" has to be backed by a measurement in `demos/ANALYSIS.md`, so changing a
number in one place without the other is the main way to do damage here.

## Layout

```
demos/            the demo — three agents, one incident, one collector, in kind
  agents/         capybara-sre (Java) · capybara-db-mcp · prod-db-mcp · beaver-sre · otter-sre · goose
  infrastructure/ postgres: the schema, the trigger, the roles, the seed
  observability/  collector, jaeger and prometheus values
  cluster/        kind, secrets, helm installs
  ANALYSIS.md     the measurements, with dates and versions
outline.md        the talk slide by slide, aligned to the 46-slide Google Slides deck
SPEAKER-NOTES.md  speaker notes, one section per slide, aligned to the same deck
SLIDES-STYLE.md   type, colour and geometry spec for editing the Slides deck
research.md       everything the talk is sourced from
mascots/          42 transparent cut-outs, used by the README
docs/superpowers/ the original specs and plans — history, not live documentation
```


## The rules that matter

**Measure, do not reason.** Every number in the deck came off a live run. If you are about to
write a plausible number, run it instead — several confident claims in this repo turned out
to be wrong when finally measured, and one had to be withdrawn from the deck. `ANALYSIS.md`
records dates and versions because most of this software is pre-1.0.

**Superseded measurements stay.** When a measurement is replaced, the old one moves to
*Superseded and historical* in `ANALYSIS.md` with a note on what replaced it. Do not delete
it. The talk claims an audit trail, so the audit trail has to exist.

**Comments explain the code, not the talk.** Code and configuration are read by people
copying them, not by the audience. Say why a flag is set and what breaks without it. Do not
reference slides, beats, or the presentation.

**One variable per comparison.** The demo's arguments only work because two runs differ in
exactly one respect. Adding a second difference does not weaken a finding, it deletes it.

## The slides are not in this repository

The talk is delivered from **Google Slides**. This repo keeps what makes that deck
maintainable — `outline.md`, `SPEAKER-NOTES.md`, `SLIDES-STYLE.md` — and nothing else.

The HTML deck the Slides version was built from, together with its element exports and the
tooling that produced them, is archived at `~/Documents/your-agent-did-what/presentation/`.
It runs standalone from there. Do not reintroduce it here: it is 71 MB of rendered PNGs and a
second copy of a deck that is now maintained elsewhere, and two copies will drift.

If you change what a slide claims, change `SPEAKER-NOTES.md` and `outline.md` with it — they
are the only record in this repo of what is actually said on stage.

## Running the demo

```bash
cd demos
cp .env.template .env       # ANTHROPIC_API_KEY
./00_run.sh                 # cluster, database, both agents
./01_start-demo.sh          # port-forwards, waits until they answer
```

**Any deploy or `kubectl set env` replaces a pod and takes the port-forward with it.** The
console then appears dead, `curl` returns `HTTP 000`, and nothing in the logs explains it.
Re-run `./01_start-demo.sh`. This cost six debugging sessions before the script existed, so
if something that worked a minute ago is unreachable, check this first.

Tests: `./mvnw test` in each Java module (install `capybara-db-core` first, or the
applications cannot resolve it), and `pytest` in `agents/beaver-sre`.

## Things that have bitten, and will again

- **`@ApplicationScoped` beans are proxies.** Being injected is not enough to construct one,
  so `@PostConstruct` may never run. Register metrics on `StartupEvent` instead.
- **Helm merges maps but replaces lists.** `observability/collector/values.dash0.yaml`
  restates every pipeline, so an exporter added to the base file is silently dropped unless
  it is added there too. That is how Prometheus went missing from the metrics pipeline.
- **`init.sql` only runs on an empty data directory.** `infrastructure/deploy.sh` stamps the
  schema hash on the pod template so a change recreates the pod; without that a migration
  appears to apply and does not.
- **Fixed `:latest` tags mean `kubectl apply` sees no change.** The deploy scripts restart
  deployments explicitly, and the MCP server has to be ready before the agent, which resolves
  its tool list at startup.
- **The collector's `debug` exporter is the source of truth**, not the app's own logs. It
  shows what actually left the process, including whether a timestamp was set.
