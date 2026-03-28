# 🗜 Machineconfig

Machineconfig is a cross-platform CLI for bootstrapping and maintaining a development machine. It groups package installation, config syncing, data syncing, session automation, and helper utilities into one install.

See the [online docs](https://thisismygitrepo.github.io/machineconfig/) for full usage and reference material.

## Install with `uv`

### Linux / macOS

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install --upgrade --python 3.13 machineconfig
```

### Windows

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
uv tool install --upgrade --python 3.14 machineconfig
```

## Repo-local usage

From a checkout of this repository, you can run the current CLI surface without installing globally:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run mcfg --help
UV_CACHE_DIR=/tmp/uv-cache uv run devops --help
```

## Author

Alex Al-Saffar. [email](mailto:programmer@usa.com)

## Contributor

Ruby Chan. [email](mailto:ruby.chan@sa.gov.au)
