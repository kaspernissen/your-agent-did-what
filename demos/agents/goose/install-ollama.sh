#!/bin/bash

### -------------------
### Install Ollama and pull model
### -------------------

OLLAMA_VERSION=$(curl -fsSL https://api.github.com/repos/ollama/ollama/releases/latest | grep -m1 '"tag_name"' | cut -d'"' -f4)
ARCH=$(uname -m | sed 's/aarch64/arm64/;s/x86_64/amd64/')
curl -fsSL "https://github.com/ollama/ollama/releases/download/${OLLAMA_VERSION}/ollama-linux-${ARCH}.tar.zst" -o /tmp/ollama.tar.zst
sudo apt-get install -y zstd
sudo tar -I zstd -xf /tmp/ollama.tar.zst -C /usr/local
rm /tmp/ollama.tar.zst

# Start the server just long enough to pull the model; postStartCommand
# takes over running it for the rest of the container's life.
ollama serve &
for i in $(seq 1 30); do
  curl -fs http://localhost:11434 >/dev/null 2>&1 && break
  sleep 1
done
ollama pull qwen3.6:35b-a3b-q4_K_M