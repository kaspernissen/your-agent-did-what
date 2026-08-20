# Working in this repo

A conference talk: a slide deck, and a runnable demo that every factual claim in the deck
comes from. The unusual constraint is that **the demo is the evidence**. A slide that says
"we measured this" has to be backed by a measurement in the archived `ANALYSIS.md` (see
*The slides are not in this repository*), so changing a number in one place without the
other is the main way to do damage here.

## Layout

```
demos/            the demo — three agents, one incident, one collector, in kind
  agents/         capybara-sre (Java) · sre-agents-mcp · goose-mcp · goose
                  beaver-sre and otter-sre: the same Python agent twice, as separate
                  complete copies, differing only in the instrumentation library.
                  check-agents-agree.sh fails if the shared files drift apart.
  infrastructure/ postgres: the schema, the trigger, the roles, the seed
  observability/  collector, jaeger and prometheus values
  cluster/        kind, secrets, helm installs
  console/        the page, and the nginx that fronts all three agents
outline.md        the talk slide by slide, aligned to the 46-slide Google Slides deck
research.md       everything the talk is sourced from
mascots/          42 transparent cut-outs, used by the README
```


## The rules that matter

**Measure, do not reason.** Every number in the deck came off a live run. If you are about to
write a plausible number, run it instead — several confident claims in this repo turned out
to be wrong when finally measured, and one had to be withdrawn from the deck. The archived
`ANALYSIS.md` records dates and versions because most of this software is pre-1.0.

**Superseded measurements stay.** When a measurement is replaced, the old one moves to
*Superseded and historical* in the archived `ANALYSIS.md` with a note on what replaced it.
Do not delete it. The talk claims an audit trail, so the audit trail has to exist.

**Comments explain the code, not the talk.** Code and configuration are read by people
copying them, not by the audience. Say why a flag is set and what breaks without it. Do not
reference slides, beats, or the presentation.

**One variable per comparison.** The demo's arguments only work because two runs differ in
exactly one respect. Adding a second difference does not weaken a finding, it deletes it.

## The slides are not in this repository

The talk is delivered from **Google Slides**. This repo keeps `outline.md` — what each
slide has to land, and in what order — and nothing else about the deck.

The speaker notes (`SPEAKER-NOTES.md`), the type spec (`SLIDES-STYLE.md`), the measurement
log (`ANALYSIS.md`), the HTML deck with its element exports and tooling, and the original
specs and plans (`docs/superpowers/`) are all archived at `~/Documents/your-agent-did-what/`. The deck runs standalone from there. Do not reintroduce it here: it is 71 MB of rendered PNGs and a
second copy of a deck that is now maintained elsewhere, and two copies will drift.

If you change what a slide claims, change `outline.md` here and `SPEAKER-NOTES.md` in the
archive with it. `outline.md` is the only record in this repo of what is said on stage.

## Running the demo

```bash
cd demos
cp .env.template .env       # ANTHROPIC_API_KEY
./00_run.sh                 # cluster, database, all three agents
./01_start-demo.sh          # port-forwards, waits until they answer
```

**Any deploy or `kubectl set env` replaces a pod and takes the port-forward with it.** The
console then appears dead, `curl` returns `HTTP 000`, and nothing in the logs explains it.
Re-run `./01_start-demo.sh`. This cost six debugging sessions before the script existed, so
if something that worked a minute ago is unreachable, check this first.

Tests: `./mvnw test` in each Java module (install `customer-db-core` first, or the
applications cannot resolve it), and `pytest` in `agents/beaver-sre` and `agents/otter-sre`.

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
- **Maven leaves deleted resources in `target/classes`.** An incremental `package` copies
  new files in and never takes removed ones out, so a file you deleted keeps shipping. That
  is how capybara-sre went on serving the console after it moved to `demos/console/`. Use
  `clean` when the change is a deletion.
- **nginx resolves `proxy_pass` hostnames at startup and refuses to boot if they are
  missing**, unless the address goes through a variable — and its `resolver` ignores the
  search domains in `/etc/resolv.conf`, so upstreams have to be fully qualified. Both are
  written up in `demos/console/README.md`.
