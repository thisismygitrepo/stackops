#!/bin/bash
set -euo pipefail

echo "STARTING OZ CLI INSTALLATION | Setting up Warp apt repository"

arch="$(dpkg --print-architecture)"
case "$arch" in
    amd64|arm64)
        ;;
    *)
        echo "Unsupported architecture for oz-stable: $arch"
        exit 1
        ;;
esac

echo "Installing repository setup dependencies..."
sudo apt-get update
sudo apt-get install -y ca-certificates wget gpg

echo "Adding Warp apt signing key..."
tmp_keyring="$(mktemp)"
trap 'rm -f "$tmp_keyring"' EXIT
wget -qO- https://releases.warp.dev/linux/keys/warp.asc | gpg --dearmor > "$tmp_keyring"
sudo install -D -o root -g root -m 644 "$tmp_keyring" /etc/apt/keyrings/warpdotdev.gpg

echo "Adding Warp apt repository..."
echo "deb [arch=$arch signed-by=/etc/apt/keyrings/warpdotdev.gpg] https://releases.warp.dev/linux/deb stable main" \
    | sudo tee /etc/apt/sources.list.d/warpdotdev.list >/dev/null

echo "Installing oz-stable..."
sudo apt-get update
sudo apt-get install -y oz-stable

echo "Oz CLI installed successfully"
