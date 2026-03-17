# Installation

Machineconfig supports Python 3.13+ and is easiest to install with [uv](https://docs.astral.sh/uv/).

## Install with uv

### 1. Install uv

=== "Linux / macOS"

    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

=== "Windows"

    ```powershell
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

### 2. Install Machineconfig

```bash
uv tool install --upgrade --python 3.13 machineconfig
```

## Verify the CLI surface

Check the umbrella entrypoint:

```bash
mcfg --help
machineconfig --help
```

Then check a direct command family:

```bash
devops --help
```

## Understand the entrypoint model

Machineconfig installs multiple commands:

- Umbrella entrypoints: `mcfg`, `machineconfig`
- Direct entrypoints: `devops`, `cloud`, `sessions`, `agents`, `utils`, `fire`, `croshell`, `msearch`

Use the direct entrypoints for day-to-day work. The umbrella commands dispatch to the top-level apps and are useful when you want a single starting point, but they are not the old monolithic `mcfg shell/config/dotfiles/...` interface.

## Recommended follow-up checks

```bash
devops config --help
devops data --help
cloud --help
sessions --help
agents --help
utils --help
```

## Run from a repository checkout

If you are working from source instead of installing globally:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run mcfg --help
UV_CACHE_DIR=/tmp/uv-cache uv run devops --help
```

The same pattern works for the direct entrypoints:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run cloud --help
UV_CACHE_DIR=/tmp/uv-cache uv run sessions --help
```

## Upgrade or remove

```bash
uv tool upgrade machineconfig
uv tool uninstall machineconfig
```
