#!/bin/bash

### -------------------
### Install Ollama and pull the model — opt-in, and nothing runs this for you
### -------------------
###
### Linux only (it fetches ollama-linux-*), so this is for inside the container. On a Mac host
### use brew or the Ollama app; the host is where the GPU is, and where the Ollama path is meant
### to run from.
###
### Two things to know before reaching for it:
###
###   * Nothing keeps the server up. The `ollama serve &` below lives as long as this script
###     does — there is no postStartCommand running it afterwards. Start it yourself in the
###     terminal you want to use it from.
###   * goose will still use Anthropic. devcontainer.json pins GOOSE_PROVIDER=anthropic, and an
###     explicit value beats 02_run-goose.sh's own detection, so pass GOOSE_PROVIDER=ollama on the
###     run to get any benefit from having installed this.
###
### Both of those are deliberate: the container has no GPU to pass through, and a model small
### enough to be tolerable on CPU cannot be relied on to call the tool the demo turns on.
###
### Nothing references this script; run it by hand when you want the Ollama path inside the
### container. Without `set -e` a failed download fell through to tar and unpacked nothing,
### which surfaced three steps later as "ollama: not found".
set -euo pipefail

OLLAMA_VERSION=$(curl -fsSL https://api.github.com/repos/ollama/ollama/releases/latest | grep -m1 '"tag_name"' | cut -d'"' -f4)
ARCH=$(uname -m | sed 's/aarch64/arm64/;s/x86_64/amd64/')
curl -fsSL "https://github.com/ollama/ollama/releases/download/${OLLAMA_VERSION}/ollama-linux-${ARCH}.tar.zst" -o /tmp/ollama.tar.zst
sudo apt-get install -y zstd
sudo tar -I zstd -xf /tmp/ollama.tar.zst -C /usr/local
rm /tmp/ollama.tar.zst

# Start the server just long enough to pull the model. It goes away with this script — see the
# header — so start it again in whatever shell you actually want to use it from.
ollama serve &
for i in $(seq 1 30); do
  curl -fs http://localhost:11434 >/dev/null 2>&1 && break
  sleep 1
done
ollama pull qwen3.6:35b-a3b-q4_K_M