
sudo nala install ccache patchelf -y

STACKOPS_REPO_DIR="$HOME/code/stackops"

mkdir -p $HOME/data/binaries/stackops
cd "$STACKOPS_REPO_DIR"
rm -rfd build
rm -rfd .venv
uv sync --no-dev
uv pip install nuitka
uv run --no-dev python -m nuitka "$STACKOPS_REPO_DIR/src/stackops/scripts/python/devops.py" --onefile --standalone --output-filename=devops  --output-dir=./build
