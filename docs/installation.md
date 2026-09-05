# Installation

StackOps supports Python 3.13+ and is easiest to install with [uv](https://docs.astral.sh/uv/).

## Install with uv

### 1. Install uv

=== "Linux / macOS"

    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

=== "Alpine Linux"

    On a fresh Alpine system, enable the `community` repository and run this as root first:

    ```sh
    apk add --no-cache bash ca-certificates curl sudo
    ```

    Then install uv:

    ```sh
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

=== "Windows"

    ```powershell
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

### 2. Install StackOps

```bash
uv tool install --upgrade --python 3.14 stackops
```

This installs nine commands: `devops`, `cloud`, `terminal`, `agents`, `utils`, `fire`, `preview`, `seek`, and `stackops`. Open the command index with:

```bash
stackops --help
```

Alpine support covers native APK package-manager paths. Portable Linux assets built for glibc and offline bundles produced on another Linux libc are not guaranteed to run on Alpine.

## Report the installed version

The current source supports `stackops --version`. Published release `26.9` predates that option; for that release, inspect the installed package with:

```bash
uv tool list
```

When reporting behavior from a source checkout, include its Git commit as well as the package version. Source changes can precede the next release.

## Upgrade or remove

```bash
uv tool upgrade stackops
uv tool uninstall stackops
```
