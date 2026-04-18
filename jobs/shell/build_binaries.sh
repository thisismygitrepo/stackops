
sudo nala install ccache patchelf -y

mkdir -p $HOME/data/binaries/stackops
cd $HOME/code/ stackops
rm -rfd build
rm -rfd .venv
uv sync --no-dev
uv pip install nuitka
uv run --no-dev python -m nuitka $HOME/code/ stackops/src/stackops/scripts/python/devops.py --onefile --standalone --output-filename=devops  --output-dir=./build
