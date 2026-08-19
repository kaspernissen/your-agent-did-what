#!/usr/bin/env bash
# Run the goose recipe against the cluster's database, exporting to the cluster's collector.
#
# Two supported paths, and the provider decides which one you are on:
#
#   ollama     (default) goose talks to a local Ollama. This is the path the talk is given on:
#              a local model on the presenter's own laptop, which is the story the slides tell.
#              It has to run on the host, because Docker cannot pass the GPU through on a Mac
#              and a containerised Ollama falls back to CPU.
#   anthropic  goose talks to the Anthropic API. This is the devcontainer path: no GPU, no
#              multi-gigabyte model pull, and — the reason it exists — reliable tool calling.
#              The demo only works if the model actually calls delete_records, and that is
#              exactly where a small CPU-sized model becomes a coin toss.
#
# Either way goose emits the same gen_ai.* spans; only gen_ai.request.model differs. Needs
# goose v1.46.0 or newer: earlier releases emit no gen_ai.* attributes at all, because the two
# PRs that added them merged four hours after 1.45.0 was cut and shipped in 1.46.0.
set -euo pipefail
cd "$(dirname "$0")"

if [ -f ../../.env ]; then set -a; . ../../.env; set +a; fi   # demos/.env
echo "✅ Loaded environment variables."

# Pick the provider rather than making the operator remember which machine they are on.
# An explicit GOOSE_PROVIDER always wins; otherwise: inside a container there is no GPU and
# no Ollama worth having, so Anthropic. On a host, a working Ollama is the demo as presented,
# and an API key is the fallback when it is absent.
#
# .env.template calls these optional, so the defaults have to exist here: under `set -u` an
# unset GOOSE_PROVIDER is a fatal unbound variable, and every .env written before the template
# gained them is missing both. Exported because goose reads them from the environment — the
# recipe itself no longer carries a settings block.
in_container() { [ -f /.dockerenv ] || [ -n "${REMOTE_CONTAINERS:-}" ] || [ -n "${CODESPACES:-}" ]; }

# Capture, then test. `ollama list | grep -q` looks equivalent and is not: grep -q exits on the
# first match, ollama takes SIGPIPE, and `set -o pipefail` turns that into a failed pipeline —
# so a perfectly healthy Ollama reports as missing. It depends on whether the producer finishes
# writing before the consumer quits, which makes it intermittent rather than simply broken.
ollama_models() { command -v ollama >/dev/null 2>&1 || return 1; ollama list 2>/dev/null; }
have_ollama()   { local o; o="$(ollama_models)" || return 1; [ "$(printf '%s' "$o" | wc -l)" -ge 1 ]; }

if [ -z "${GOOSE_PROVIDER:-}" ]; then
  if in_container;                        then GOOSE_PROVIDER=anthropic; WHY="in a container, so no GPU"
  elif have_ollama;                       then GOOSE_PROVIDER=ollama;    WHY="Ollama is running locally"
  elif [ -n "${ANTHROPIC_API_KEY:-}" ];   then GOOSE_PROVIDER=anthropic; WHY="no Ollama, but an API key is set"
  else
    echo "No provider available. Either start Ollama and pull a model, or set ANTHROPIC_API_KEY"
    echo "in demos/.env. Force one with GOOSE_PROVIDER=ollama|anthropic."
    exit 1
  fi
  echo "→ provider: $GOOSE_PROVIDER  ($WHY; override with GOOSE_PROVIDER)"
fi
export GOOSE_PROVIDER

# The model default has to follow the provider. A single default cannot serve both: setting
# only GOOSE_PROVIDER=anthropic — which .env.template invites you to do — would otherwise ask
# Anthropic for a qwen model and fail on a name it has never heard of.
if [ -z "${GOOSE_MODEL:-}" ]; then
  case "$GOOSE_PROVIDER" in
    anthropic) GOOSE_MODEL="claude-sonnet-5" ;;               # as beaver and otter use
    ollama)    GOOSE_MODEL="qwen3.6:35b-a3b-q4_K_M" ;;
    *)         echo "Set GOOSE_MODEL: no default for provider '$GOOSE_PROVIDER'"; exit 1 ;;
  esac
fi
export GOOSE_MODEL

command -v goose >/dev/null || { echo "goose not installed: see block.github.io/goose"; exit 1; }

case "$GOOSE_PROVIDER" in
  ollama)
    command -v ollama >/dev/null || { echo "ollama not installed: see ollama.com"; exit 1; }
    # shell pattern match on the captured text, for the pipefail reason above
    case "$(ollama_models)" in
      *"${GOOSE_MODEL%%:*}"*) ;;
      *) echo "Model $GOOSE_MODEL not pulled. Run: ollama pull $GOOSE_MODEL"; exit 1 ;;
    esac
    ;;
  anthropic)
    : "${ANTHROPIC_API_KEY:?GOOSE_PROVIDER=anthropic needs ANTHROPIC_API_KEY in demos/.env}"
    ;;
esac

# The MCP server the recipe points at, and the collector goose reports to.
pkill -f "port-forward svc/prod-db-mcp" 2>/dev/null || true
kubectl port-forward svc/prod-db-mcp 8086:8086 >/tmp/pf-prod-mcp.log 2>&1 &
pkill -f "port-forward svc/otel-collector" 2>/dev/null || true
kubectl port-forward svc/otel-collector-opentelemetry-collector 4318:4318 >/tmp/pf-col.log 2>&1 &
echo "✅ Set up port-forwarding."

echo "Waiting on OTel Collector readiness..."
for _ in $(seq 1 30); do
  curl -sf -o /dev/null "http://localhost:4318/" 2>/dev/null && break || sleep 1
  echo "..."
done
echo "✅ Ready!"

export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4318"
export OTEL_SERVICE_NAME="goose"
export OTEL_METRICS_EXPORTER=none
export OTEL_LOGS_EXPORTER=none
# The convention's own variable. It takes the literal string "true", compared case-insensitively;
# `1` is silently ignored. Without it there are no tool call arguments or results to read, which
# is the whole reason for pointing goose at this collector.
export OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true

echo "--- goose $(goose --version 2>/dev/null | tr -d '\n') · provider $GOOSE_PROVIDER · model $GOOSE_MODEL ---"
goose run --recipe tidy-free-plan.yaml