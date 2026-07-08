#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
STACKOPS_REPO_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
read -r DISTRIBUTION_ID PACKAGE_MANAGER < <(
  cd "$STACKOPS_REPO_DIR"
  PYTHONPATH="$STACKOPS_REPO_DIR/src" uv run --no-project python -m stackops.utils.installer_utils.linux_package_manager
)
echo "Installing build dependencies on $DISTRIBUTION_ID with $PACKAGE_MANAGER"

if [[ "$PACKAGE_MANAGER" == "apt" ]]; then
  sudo apt-get update
  sudo apt-get install -y ccache patchelf
elif [[ "$DISTRIBUTION_ID" == "fedora" ]]; then
  sudo dnf install -y ccache patchelf
else
  echo "Build dependencies on $DISTRIBUTION_ID require explicit EPEL/CRB repository configuration." >&2
  exit 1
fi

mkdir -p $HOME/data/binaries/stackops
cd "$STACKOPS_REPO_DIR"
rm -rfd build
rm -rfd .venv
uv sync --no-dev
uv pip install nuitka
uv run --no-dev python -m nuitka "$STACKOPS_REPO_DIR/src/stackops/scripts/python/devops.py" --onefile --standalone --output-filename=devops  --output-dir=./build
