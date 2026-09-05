<div align="center">

<h1>🗜 StackOps</h1>

<strong>Developer workstation and workflow CLI.</strong>

<p>
  <a href="https://thisismygitrepo.github.io/stackops/"><img alt="Docs" src="https://img.shields.io/badge/docs-online-2f6f6f"></a>
  <a href="https://pypi.org/project/stackops/"><img alt="PyPI package" src="https://img.shields.io/pypi/v/stackops?color=2f6f6f"></a>
  <img alt="Python 3.13+" src="https://img.shields.io/badge/python-3.13%2B-3776AB">
  <img alt="Installed with uv" src="https://img.shields.io/badge/install-uv-f05d23">
</p>

</div>

StackOps coordinates packages, configuration, repositories, data, terminal layouts, and coding-agent resources around the tools you already use. Install selected packages, synchronize declared configuration, or launch an authored tmux workspace through focused commands. Available installers and integrations vary by operating system and external tool.

See the [online docs](https://thisismygitrepo.github.io/stackops/) for full usage and reference material.

## Install

Choose your platform and expand only the commands you need.

<details>
<summary><strong>Linux</strong></summary>

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install --upgrade --python 3.14 stackops
stackops --help
```

</details>

<details>
<summary><strong>macOS</strong></summary>

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install --upgrade --python 3.14 stackops
stackops --help
```

</details>

<details>
<summary><strong>Windows PowerShell</strong></summary>

```powershell
powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
uv tool install --upgrade --python 3.14 stackops
stackops --help
```

</details>


## Codex Skill

Install the StackOps skill for Codex with:

```bash
bunx skills add thisismygitrepo/stackops --skill stackops --global --agent codex --yes
```


## Start with a workflow

Inspect the commands for the workflow you need:

```bash
devops install --help
devops config sync --help
terminal run --help
```

The [quickstart](https://thisismygitrepo.github.io/stackops/quickstart/) shows a selected-package example and configuration options.

## Optional workstation setup

This broader setup installs system and terminal package groups, copies bundled assets, applies public configuration mappings, and configures the default shell. Use it when you want those workstation conventions; existing customized systems can use individual commands instead. Package-group behavior depends on the platform and may invoke privileged package managers.

```bash
devops install --group sysabc
devops config copy-assets all
devops config sync down \
  --sensitivity public \
  --method copy \
  --on-conflict throw-error \
  --which all
devops config terminal config-shell --which default
devops install --group termabc
```

The scripted sync above copies configuration and stops on conflicts. The public copy/symlink choices in `devops config interactive` use `overwrite-default-path` and can replace existing targets; they are a different setup choice.


## CLI

StackOps exposes standalone commands and an umbrella wrapper:

| Command | Purpose |
| --- | --- |
| `devops` | Package installation, repo automation, config/data sync, self-management, networking, script execution, vault |
| `cloud` | Cloud sync, copy, mount, SSH transfer, and OneDrive helpers |
| `terminal` | Terminal session and layout management |
| `agents` | AI agent scaffolding, MCP catalog installs, prompt runs, parallel workflows |
| `utils` | General-purpose utility commands |
| `fire` | File, function, notebook, and app runner |
| `preview` | File preview and `uv run` backend launcher |
| `seek` | Interactive search across files, text matches, and symbols |
| `stackops` | Umbrella wrapper that routes into all of the above |

Run `<command> --help` for details, or `stackops --help` to see the command families.


## Author

Alex Al-Saffar. [email](mailto:programmer@usa.com)

## Contributor

Ruby Chan. [email](mailto:ruby.chan@sa.gov.au)
