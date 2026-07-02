# Capybara SRE Demo

This demo showcases an AI SRE agent built with Quarkus and LangChain4j that investigates and remediates issues in an in-memory "capybara database" — surfacing the full gen_ai observability story end-to-end in Jaeger. The agent emits **native** OpenTelemetry `gen_ai.*` semantic convention spans (no normalizer layer) with forensic content opt-ins (`include-tool-arguments` and `include-tool-result` both enabled), so every tool invocation — including destructive `delete_records` calls — carries its exact arguments and result in the trace. These traces are the input for agent-health evaluation (Plan 2).

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  capybara-sre-agent  (port 8088)                         │
│  POST /chat → {response, toolCalls, runId}               │
│  LangChain4j + Anthropic Claude                          │
│  Emits gen_ai.* spans via OTel SDK                       │
└───────────────────┬─────────────────────────────────────┘
                    │ MCP SSE (port 8086)
┌───────────────────▼─────────────────────────────────────┐
│  capybara-db-mcp  (port 8086, /mcp/sse)                  │
│  Tools: list_records / query / delete_records            │
└─────────────────────────────────────────────────────────┘
                    │ gRPC OTLP :4317
┌───────────────────▼─────────────────────────────────────┐
│  OTel Collector  →  Jaeger (query UI: port 16686)        │
└─────────────────────────────────────────────────────────┘
```

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [kind](https://kind.sigs.k8s.io/docs/user/quick-start/) (`brew install kind`)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [Helm 3](https://helm.sh/docs/intro/install/)
- JDK 21 (only needed if you want to build locally without Docker; the setup script builds images via Docker)
- `ANTHROPIC_API_KEY` set in your environment

## Quick Start

### 1. Set your API key

```bash
export ANTHROPIC_API_KEY=<your-anthropic-api-key>
```

### 2. Build Docker images

```bash
docker build -t capybara-db-mcp:latest capybara-db-mcp/
docker build -t capybara-sre-agent:latest capybara-sre-agent/
```

### 3. Stand up the kind cluster (installs Jaeger, OTel Collector, and deploys the services)

```bash
./scripts/setup-kind.sh
```

This single script creates the kind cluster `capybara-sre`, installs Jaeger and the OTel Collector via Helm, loads the Docker images, and rolls out all Kubernetes manifests.

### 4. Run an investigation

**Safe (read-only):**
```bash
./scripts/run-investigation.sh "How many free-plan capybaras are there? Do not modify anything."
```

**Destructive:**
```bash
./scripts/run-investigation.sh "Delete all the free-plan capybaras."
```

The default prompt (when no argument is given) is:
> "The free-plan capybaras are eating our storage budget. Investigate and clean it up."

Each invocation port-forwards the agent service, posts the prompt, prints the JSON response (`{response, toolCalls, runId}`), and tears down the port-forward.

## Jaeger UI

Open the Jaeger UI in a separate terminal:

```bash
kubectl port-forward svc/jaeger-query 16686:16686 >/dev/null 2>&1 &
open http://localhost:16686
```

Select service **`capybara-sre-agent`** and search for recent traces.

---

## Acceptance / What to Look for in Jaeger

> **Run this yourself** — verifying spans requires a live cluster and a real `ANTHROPIC_API_KEY`.
> The steps above produce the traces; navigate Jaeger to confirm the following.

### 1. Root `invoke_agent` span

Look for a trace whose root span is named **`invoke_agent capybara-sre`** (or similar `invoke_agent` operation). On that span confirm:

| Attribute | Expected |
|---|---|
| `gen_ai.agent.name` | `capybara-sre` |
| `gen_ai.conversation.id` | a UUID (matches `runId` in the JSON response) |

### 2. Chat / completion span

Within the same trace find a **`chat`** or **`completion`** child span. Confirm:

| Attribute | Expected |
|---|---|
| `gen_ai.provider.name` | `anthropic` |
| `gen_ai.request.model` | e.g. `claude-3-5-sonnet-*` |
| `gen_ai.usage.input_tokens` | integer > 0 |
| `gen_ai.usage.output_tokens` | integer > 0 |

### 3. `execute_tool` spans

There should be one or more **`execute_tool`** child spans. Confirm:

| Attribute | Expected values |
|---|---|
| `gen_ai.tool.name` | one of `list_records`, `query`, `delete_records` |

### 4. Forensic content on the destructive run (the key payoff)

After running the destructive prompt (`"Delete all the free-plan capybaras."`), find the `execute_tool` span whose `gen_ai.tool.name` is **`delete_records`** and confirm:

| Attribute | Present? |
|---|---|
| `gen_ai.tool.call.arguments` | Yes — the exact arguments passed to the tool (e.g. `{"plan":"free"}`) |
| `gen_ai.tool.call.result` | Yes — the tool's return value (e.g. `{"deleted":N,"remaining":M}`) |

These two attributes are present **only because** the agent is configured with:
```
quarkus.langchain4j.opentelemetry.include-tool-arguments=true
quarkus.langchain4j.opentelemetry.include-tool-result=true
```
Without those opt-in flags the spans are emitted but the content is redacted. This is the forensic observability story the demo illustrates.

---

## Tear Down

```bash
kind delete cluster --name capybara-sre
```
