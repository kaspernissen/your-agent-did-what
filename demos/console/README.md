# console

The page the demo is driven from, and the single origin in front of all three agents.

```
index.html              the whole page — markup, CSS and JavaScript in one file
markdown.js             renders the agents' answers
capybara/beaver/otter   the mascots
default.conf.template   nginx: serve the files, proxy the four API calls
Dockerfile              nginx:1.27-alpine + the five files
k8s/console.yaml        Deployment + Service, namespace `agents`
deploy.sh               build, load into kind, roll
```

## Why it is a service

It used to be five files inside `capybara-sre`, served out of `META-INF/resources`. That
worked, but it meant the Java agent also owned an HTTP pass-through — `AgentProxyResource`,
89 lines — for one reason: **the browser cannot see cluster-internal services.** Something
had to forward the calls to `beaver-sre` and `otter-sre`, and the only thing already
reachable was the agent serving the page.

nginx does that forwarding now, and the Java class is gone. The console is also no longer
hidden three directories inside an unrelated application.

## What it proxies

Same-origin, all of it. The alternative is CORS plus absolute URLs compiled into the page,
and absolute URLs mean the page only works from the port-forward it was built for.

| The page calls | goes to |
|---|---|
| `POST /chat` | `capybara-sre:8088/chat` |
| `POST /incident/reset`, `/incident/rehearse-deletion` | `capybara-sre:8088` |
| `POST /agents/chat/beaver` | `beaver-sre:8000/run` |
| `POST /agents/chat/otter` | `otter-sre:8000/run` |

All three agents accept the same `{"prompt": "..."}` body, so nginx forwards it untouched
rather than re-modelling it on the way through.

## Run it

```bash
./deploy.sh            # build, load, roll — no Maven, no pip, a few seconds
../01_start-demo.sh    # forwards it to localhost:8088
```

Editing the page is `./deploy.sh` and a reload. Nothing else has to be rebuilt.

## Two things that bite

**nginx resolves upstreams at startup unless you make it not.** With a literal hostname in
`proxy_pass` it looks the name up once and *refuses to boot* if it fails — so a console
deployed before the agents crash-loops instead of serving the page. Every `proxy_pass` here
goes through a variable, with a `resolver`, which defers the lookup to the request. The
cost is that nginx then stops appending the matched location to the upstream URI, so each
route states its target path in full.

**`resolver` ignores `/etc/resolv.conf`'s search domains.** The short names every other pod
in this demo uses come back NXDOMAIN here, which shows up as "that agent is not reachable"
while the agent is running perfectly well. The upstreams are fully qualified for that
reason, and only that reason.
