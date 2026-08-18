#!/bin/bash

### -------------------
### Uncomment ll command in bashrc
### -------------------

sed -i -e "s/#alias ll='ls -l'/alias ll='ls -al'/g" ~/.bashrc
. $HOME/.bashrc

### -------------------
### Install Helm
### -------------------

curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
chmod 700 get_helm.sh
./get_helm.sh
rm -rf get_helm.sh

### -------------------
### Pre-requisites for running Goose
### -------------------

sudo apt update && sudo apt install -y \
  gnome-keyring \
  dbus-x11 \
  libsecret-1-0 \
  libsecret-1-dev \
  libsecret-tools

mkdir -p ~/.local/share/keyrings
touch ~/.local/share/keyrings/login.keyring
eval $(dbus-launch)
export $(dbus-launch)
gnome-keyring-daemon --start --components=secrets
echo "blah" | gnome-keyring-daemon -r --unlock --components=secret

## Pinning down specific version
# GOOSE_RELEASE="stable"
GOOSE_RELEASE="v1.46.0"
curl -fsSL https://github.com/aaif-goose/goose/releases/download/${GOOSE_RELEASE}/download_cli.sh | bash

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