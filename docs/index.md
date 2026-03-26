---
hide:
  - navigation
  - toc
---

<style>
.md-content .md-typeset h1 { display: none; }
</style>

<div align="center" markdown>

# **Machineconfig**

### Cross-platform CLI for machine setup and maintenance

[![PyPI version](https://img.shields.io/pypi/v/machineconfig.svg)](https://pypi.org/project/machineconfig/)
[![Python versions](https://img.shields.io/pypi/pyversions/machineconfig.svg)](https://pypi.org/project/machineconfig/)
[![License](https://img.shields.io/github/license/thisismygitrepo/machineconfig.svg)](https://github.com/thisismygitrepo/machineconfig/blob/main/LICENSE)
[![GitHub commit activity](https://img.shields.io/github/commit-activity/m/thisismygitrepo/machineconfig)](https://github.com/thisismygitrepo/machineconfig/commits)

Machineconfig offers a cli family to manage your digital life.

[Install with uv](installation.md){ .md-button .md-button--primary }
[Quickstart](quickstart.md){ .md-button }
[View on GitHub](https://github.com/thisismygitrepo/machineconfig){ .md-button }

</div>

---

## What you get

Machineconfig is organized around direct CLI families:

| Command | What it covers |
| --- | --- |
| `devops` | Package installs, repos, config, data, self-management, networking, scripted execution |
| `cloud` | Syncing, copying, mounting, and SSH file transfer workflows |
| `sessions` | Launching, attaching to, killing, templating, and summarizing session layouts |
| `agents` | Generating agent configs, templates, prompts, symlinks, and skills |
| `utils` | Process, environment, project, file, PDF, and database helpers |
| `fire`, `croshell`, `msearch` | Standalone helper entrypoints |

The umbrella commands dispatch into the current top-level apps. Treat the direct entrypoints as the primary interface; do not expect the old `mcfg shell/config/dotfiles/...` layout.

---

## Install and verify

=== "Linux / macOS"

    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    uv tool install --upgrade --python 3.13 machineconfig
    mcfg --help
    devops --help
    ```

=== "Windows"

    ```powershell
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    uv tool install --upgrade --python 3.13 machineconfig
    mcfg --help
    devops --help
    ```

---

## Good first commands

```bash
mcfg --help
devops --help
devops config --help
devops config terminal --help
devops install --interactive
devops config sync --help
devops data sync --help
```

---

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } **Getting Started**

    ---

    Install Machineconfig and verify the active command surface.

    [:octicons-arrow-right-24: Installation](installation.md)

-   :material-run-fast:{ .lg .middle } **Quickstart**

    ---

    Follow a short path through help, shell setup, install, and sync commands.

    [:octicons-arrow-right-24: Quickstart](quickstart.md)

-   :material-console:{ .lg .middle } **CLI Reference**

    ---

    Browse the full command reference.

    [:octicons-arrow-right-24: CLI Reference](cli/index.md)

-   :material-api:{ .lg .middle } **API Reference**

    ---

    Explore the Python API and internals.

    [:octicons-arrow-right-24: API Reference](api/index.md)

</div>
