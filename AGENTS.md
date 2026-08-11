# Working in this repo

A conference talk: a slide deck, and a runnable demo that every factual claim in the deck
comes from. The unusual constraint is that **the demo is the evidence**. A slide that says
"we measured this" has to be backed by a measurement in `demos/ANALYSIS.md`, so changing a
number in one place without the other is the main way to do damage here.

## Layout

```
presentation/     the deck — 52 slides, plus a conformance checker and a geometry audit
demos/            the demo — two agents, one incident, one collector, in kind
  agents/         capybara-sre (Java) · capybara-db-mcp · capybara-db-core · beaver-sre (Python)
  infrastructure/ postgres: the schema, the trigger, the roles, the seed
  observability/  collector, jaeger and prometheus values
  cluster/        kind, secrets, helm installs
outline.md        beat-by-beat structure and timing
ANALYSIS.md       (in demos/) the measurements, with dates and versions
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

## Before committing a deck change

```bash
cd presentation
python3 check-deck.py        # design-system conformance; exits non-zero
python3 test-check-deck.py   # the checker's own tests
```

Then the geometry audit — the command is in `presentation/README.md`. The checker reads
markup and cannot see geometry, so **text overflowing a slide or printed on top of other
text passes it**. The audit is what catches that, and it has caught it repeatedly, including
three times in one afternoon after adding a line to a fixed layout.

Speaker notes live in a JSON array inside `presentation/index.html`; the count must match the
slide count, and the checker enforces that. If you add a slide, add its note.

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
