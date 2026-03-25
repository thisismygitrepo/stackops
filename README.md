# 🗜 Machineconfig

Machineconfig is a cross-platform CLI for bootstrapping and maintaining a development machine. It groups package installation, config syncing, data syncing, session automation, and helper utilities into one install.

## Install with uv

### Linux / macOS

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install --upgrade --python 3.13 machineconfig
```

### Windows

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
uv tool install --upgrade --python 3.13 machineconfig
```

## Verify the install

```bash
mcfg --help
devops --help
```

`machineconfig` is also installed as an alias-style umbrella entrypoint alongside `mcfg`.

## Command model

Machineconfig now exposes direct command families instead of a single old `mcfg shell/config/dotfiles/...` tree.

- Umbrella entrypoints: `mcfg`, `machineconfig`
- Direct entrypoints: `devops`, `cloud`, `sessions`, `agents`, `utils`, `fire`, `croshell`, `msearch`

### Current command families

| Command | What it covers |
| --- | --- |
| `devops` | `install`, `repos`, `config`, `data`, `self`, `network`, `execute` |
| `cloud` | `sync`, `copy`, `mount`, `ftpx` |
| `sessions` | `run`, `run-aoe`, `attach`, `kill`, `trace`, `create-from-function`, `balance-load`, `create-template`, `summarize` |
| `agents` | `parallel.{create, create-context, collect, make-template}`, `make-config`, `make-todo`, `make-symlinks`, `run-prompt`, `ask`, `add-skill` |
| `utils` | `kill-process`, `environment`, `get-machine-specs`, `init-project`, `upgrade-packages`, `type-hint`, `edit`, `download`, `pdf-merge`, `pdf-compress`, `read-db` |
| `fire`, `croshell`, `msearch` | Standalone helper tools |

## First steps

```bash
mcfg --help
devops --help
devops config shell
devops install --interactive
devops config sync --help
devops data sync --help
```

If you already know the package bundle you want, use:

```bash
devops install --group <group-name>
```

## Repo-local usage

From a checkout of this repository, you can run the current CLI surface without installing globally:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run mcfg --help
UV_CACHE_DIR=/tmp/uv-cache uv run devops --help
```

## Links

- Docs homepage: `docs/index.md`
- Installation guide: `docs/installation.md`
- Quickstart: `docs/quickstart.md`

## Author

Alex Al-Saffar. [email](mailto:programmer@usa.com)

## Contributor

Ruby Chan. [email](mailto:ruby.chan@sa.gov.au)
