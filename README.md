<div align="center">

<h1>🗜 StackOps</h1>

<strong>Digital Life Manager.</strong>

<p>
  <a href="https://thisismygitrepo.github.io/stackops/"><img alt="Docs" src="https://img.shields.io/badge/docs-online-2f6f6f"></a>
  <a href="https://pypi.org/project/stackops/"><img alt="PyPI package" src="https://img.shields.io/pypi/v/stackops?color=2f6f6f"></a>
  <img alt="Python 3.13+" src="https://img.shields.io/badge/python-3.13%2B-3776AB">
  <img alt="Installed with uv" src="https://img.shields.io/badge/install-uv-f05d23">
</p>

</div>

StackOps is a cross-platform CLI for managing your development stack. It is package installer, configurator, dotfile/secrets manager, data and code sync solution, command launcher, processes orchestrator (is there anything else?) all wrapped into one solution. As such, it should take a few minutes to make a fresh new machine to look like the machine you were customizing for 10 years.


| Before | After |
| --- | --- |
| ![Fresh minimal machine state](docs/assets/before.png) | ![Developer-ready machine state](docs/assets/after.png) |


See the [online docs](https://thisismygitrepo.github.io/stackops/) for full usage and reference material.

## Install

Choose your platform and expand only the commands you need.

<details>
<summary><strong>Linux</strong></summary>

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install --upgrade --python 3.14 stackops
stackops --help
# OR: . < (curl -L https://bit.ly/sopsu)
```

</details>

<details>
<summary><strong>macOS</strong></summary>

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install --upgrade --python 3.14 stackops
stackops --help
# OR: . < (curl -L https://bit.ly/sopsu)
```

</details>

<details>
<summary><strong>Windows PowerShell</strong></summary>

```powershell
powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
uv tool install --upgrade --python 3.14 stackops
stackops --help
# OR: irm bit.ly/sopsw | iex
```

</details>


## Quick Init

Run these once StackOps is installed.

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


## CLI

StackOps exposes standalone commands and an umbrella wrapper:

| Command | Purpose |
| --- | --- |
| `devops` | Package installation, repo automation, config/data sync, self-management, networking, script execution, vault |
| `cloud` | Cloud sync, copy, mount, and SSH transfer helpers |
| `terminal` | Terminal session and layout management |
| `agents` | AI agent scaffolding, MCP catalog installs, prompt runs, parallel workflows |
| `utils` | General-purpose utility commands |
| `fire` | File, function, notebook, and app runner |
| `preview` | File preview and `uv run` backend launcher |
| `seek` | Interactive search across files, text matches, and symbols |
| `stackops` | Umbrella wrapper that routes into all of the above |

Run `<command> --help` for details, or `stackops --help` to see the full tree.


## Author

Alex Al-Saffar. [email](mailto:programmer@usa.com)

## Contributor

Ruby Chan. [email](mailto:ruby.chan@sa.gov.au)
