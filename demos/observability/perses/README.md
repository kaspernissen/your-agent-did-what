# Perses

Dashboards, as files. Two of them:

| Dashboard | What it shows |
|---|---|
| **Customer records** | `customer_records` stepping from five to two, and `customer_records_deleted_total` broken down by the database role that did it |
| **Agent traces** | Capybara, Beaver and Otter side by side, plus goose — the same incident, four services, one screen |

```
provisioning/
  00-project.yaml                    the project the dashboards belong to
  01-datasource-prometheus.yaml      metrics
  02-datasource-jaeger.yaml          traces
  03-dashboard-customer-records.yaml
  04-dashboard-agent-traces.yaml
values.yaml                          Helm values; mounts the above as a ConfigMap
```

`cluster/setup.sh` turns `provisioning/` into a ConfigMap and installs the chart. Adding a
dashboard is adding a file. Editing one is editing a file and re-running `./cluster/setup.sh`
— the pod is restarted deliberately, because provisioning is read at startup and `apply` on
an unchanged ConfigMap is a no-op.

Perses re-reads the folder on an interval, so a dashboard deleted by hand in the UI comes
back. On a stage that is the behaviour you want.

## Why Jaeger as well as Prometheus

Jaeger's own UI shows one service at a time, which is right for an investigation and wrong
for a comparison. This demo *is* a comparison — same incident, same question, three
platforms — so four trace tables on one screen is a glance rather than four tab switches.

`JaegerTraceQuery` takes either a `traceId` or a `service`, plus optional `operation`,
`spanKind`, `tags`, `minDuration`, `maxDuration` and `limit`
([schema](https://github.com/perses/plugins/blob/main/jaeger/schemas/jaeger-trace-query/query.cue)).
`TracingGanttChart` is the panel for one trace's waterfall if you want to pin a known run.

## Two things that cost time

**`proxy`, not `directUrl`.** `directUrl` means the *browser* queries the datasource
itself — so your laptop would try to resolve `prometheus.observability.svc.cluster.local`,
and every panel comes up empty. `proxy` routes the query through the Perses backend, which
is inside the cluster. It also means only Perses needs port-forwarding: `01_start-demo.sh`
maps it to **<http://localhost:8080>** — Perses' own port, like Jaeger's and Prometheus'
are theirs — and Prometheus and Jaeger are reached from there.

**One resource per file.** Perses provisioning does not read multi-document YAML. Given two
resources separated by `---` it loads the first and drops the second, logging nothing.
