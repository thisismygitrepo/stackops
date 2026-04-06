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
uv tool install --upgrade --python 3.14 machineconfig
```

This should give entrypoints: `devops`, `cloud`, `terminal`, `agents`, `utils`, `fire`, `croshell`, `seek`
You can verify with, e.g.:

```bash
devops --help
```

## Upgrade or remove

```bash
uv tool upgrade machineconfig
uv tool uninstall machineconfig
```
