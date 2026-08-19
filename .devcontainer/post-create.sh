#!/bin/bash
# Container setup. Fail loudly: a silent failure here produces a container that looks built
# and breaks at demo time, which is the worst moment to discover a half-finished install.
set -euo pipefail

### -------------------
### Uncomment ll command in bashrc
### -------------------

sed -i -e "s/#alias ll='ls -l'/alias ll='ls -al'/g" ~/.bashrc

### -------------------
### Install kubectl
### -------------------

KUBECTL_VERSION=$(curl -fsSL https://dl.k8s.io/release/stable.txt)
ARCH=$(uname -m | sed 's/aarch64/arm64/;s/x86_64/amd64/')
curl -fsSL "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${ARCH}/kubectl" -o /tmp/kubectl
sudo install -o root -g root -m 0755 /tmp/kubectl /usr/local/bin/kubectl
rm /tmp/kubectl

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
### goose keeps provider secrets in a keyring, and errors out on a headless container
### without one. dbus is launched once and its address written to ~/.bashrc: the variables
### are shell-local, so a container-creation-only launch leaves every later terminal without
### them and goose fails there instead.

sudo apt-get update && sudo apt-get install -y \
  gnome-keyring \
  dbus-x11 \
  libsecret-1-0 \
  libsecret-1-dev \
  libsecret-tools

mkdir -p ~/.local/share/keyrings
touch ~/.local/share/keyrings/login.keyring
eval "$(dbus-launch --sh-syntax)"
grep -q DBUS_SESSION_BUS_ADDRESS ~/.bashrc \
  || echo "export DBUS_SESSION_BUS_ADDRESS='${DBUS_SESSION_BUS_ADDRESS}'" >> ~/.bashrc
gnome-keyring-daemon --start --components=secrets
echo "blah" | gnome-keyring-daemon -r --unlock --components=secret

### -------------------
### Install Goose
### -------------------
### Pinned deliberately. Releases before 1.46.0 emit no gen_ai.* attributes at all — the two
### PRs that added them merged four hours after 1.45.0 was cut — so an older goose produces a
### run that looks fine and records nothing the talk is about.

GOOSE_RELEASE="v1.46.0"
curl -fsSL "https://github.com/aaif-goose/goose/releases/download/${GOOSE_RELEASE}/download_cli.sh" | bash

### -------------------
### No Ollama in here, on purpose
### -------------------
### Docker cannot pass the GPU through on a Mac, so a containerised Ollama runs on CPU, and a
### model small enough to be tolerable there cannot be relied on to call the tool this demo
### turns on. In the container goose talks to Anthropic instead — same gen_ai.* spans, only
### gen_ai.request.model differs — and demos/agents/goose/run-recipe.sh selects that itself.
### The Ollama path stays on the host, which is where the talk is given from.

echo
echo "Container ready. goose will use Anthropic in here (ANTHROPIC_API_KEY in demos/.env)."
echo "The Ollama path is host-only; see demos/agents/goose/run-recipe.sh."
