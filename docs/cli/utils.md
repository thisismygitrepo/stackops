# utils

`utils` is the grouped entrypoint for StackOps helper workflows.

## Usage

```bash
utils [OPTIONS] COMMAND [ARGS]...
```

Top-level sub-apps:

| Sub-app | Purpose |
|---------|---------|
| `machine` | Process, environment, hardware, and local device helpers |
| `pyproject` | Project bootstrap, dependency maintenance, and typing workflows |
| `file` | File editing, downloading, PDF tools, and database viewing |

Hidden one-letter aliases exist, but this page uses canonical names.

## machine

```bash
utils machine [OPTIONS] COMMAND [ARGS]...
```

| Command | Summary |
|---------|---------|
| `kill-process` | Interactive process picker with configurable filter field |
| `environment` | Inspect `ENV` or `PATH` using the default fuzzy picker or a Textual TUI |
| `specs` | Print machine specifications |
| `list-devices` | List available devices for mounting |
| `mount` | Mount a device by query or through an interactive picker |
| `clean-drive` | Measure and reclaim disk space from caches, Docker, trash, logs, and project build folders |

Key behavior:

- `kill-process` defaults to interactive mode and supports `--filter-by command|ports|name|pid|username|status|memory|cpu`. Direct selectors are `--command`/`-c`, `--port`/`-p`, `--name`/`-n`, `--pid`/`-P`, `--username`/`-u`, `--status`/`-s`, `--memory`/`-m`, and `--cpu`/`-C`. Pass exactly one direct selector; add `--yes`/`-y` to kill every match without prompting. Memory and CPU selectors are inclusive minimums; the other selectors are exact except for command substring matching.
- `environment` defaults to `ENV`; pass `PATH` as the positional argument to browse `PATH` entries instead.
- `environment --tui` uses the full-screen Textual UI instead of the default fuzzy picker.
- `specs --hardware` includes compute capability details; without `--hardware`, it prints specs and writes `machine_specs.json` under the StackOps config root.
- `mount` requires `--device` unless `--interactive` is set, and requires `--mount-point` unless `--interactive` is set or `--backend udisksctl` is used.
- `mount --backend` accepts `mount`, `dislocker`, or `udisksctl`.
- `clean-drive` measures every target for the current OS first: real allocated size, where a hardlinked file counts only when every link would be deleted (uv and Bun hardlink their caches into `.venv` and `node_modules`). `--dry-run`/`-d` stops after the report; `--interactive`/`-i` opens a multi-select picker of every target with a preview, then confirms; with no mode flag it confirms the ● selection; `--yes`/`-y` cleans the ● selection without asking.
- `clean-drive` selection: `--target`/`-t KEY` (repeatable) picks targets explicitly; otherwise ● marks targets within `--max-risk`/`-r safe|caution|danger` (default `safe`), and targets needing root only with `--sudo`/`-s`. Narrow the scan with `--category`/`-c dev|containers|system|trash|projects` and `--exclude`/`-x KEY`. `--root`/`-R` sets where project folders (`.ai`, `node_modules`, `.venv`, `__pycache__`, Rust `target`) are searched (default: home; hidden folders, `node_modules`, and other filesystems are never entered). `--json`/`-j` prints records with `--dry-run` or `--yes`.
- `clean-drive` delegates to each tool's own cleaner where one exists (`uv cache clean`, `bun pm cache rm`, `pnpm store prune`, `go clean`, `docker … prune`, `journalctl --vacuum-size`, `apt-get clean`, `brew cleanup`) and to the [BleachBit](https://www.bleachbit.org) CLI for trash, temp files, thumbnails, browser caches, and disabled snap revisions on Linux and Windows. Install BleachBit from your distro (`sudo apt install bleachbit`); the `bleachbit` package on PyPI is not the official one.

Examples:

```bash
utils machine environment PATH
utils machine environment ENV --tui
utils machine kill-process --port 9221
utils machine kill-process --name uvicorn --yes
utils machine kill-process --memory 500 --yes
utils machine specs --hardware
utils machine mount --interactive
utils machine mount --device sdb1 --mount-point /mnt/data --read-only
utils machine clean-drive --dry-run
utils machine clean-drive --interactive
utils machine clean-drive --yes --category dev
utils machine clean-drive --target docker-build-cache --target uv-cache --yes
utils machine clean-drive --max-risk caution --sudo --root ~/code
```

## pyproject

```bash
utils pyproject [OPTIONS] COMMAND [ARGS]...
```

| Command | Summary |
|---------|---------|
| `init` | Initialize a project with a uv virtual environment and dev packages |
| `generate-upgrade-script` | Write a dependency upgrade script; optional cleanup flags take effect immediately |
| `type-check` | Run the lint-and-type-check suite for a repository |
| `check-deps` | Check Python import dependencies and cycles with `pyan3` or `pydeps` |
| `configure-linters` | Add standard linter configuration files to a git repository |
| `cleanup` | Clean cache files from one or more git repositories |
| `test-reference` | Validate `_PATH_REFERENCE` targets in a repository |
| `type-fix` | Create and optionally launch an agent layout from `./.ai/linters/issues_<checker>.md` |
| `generate-tests` | Create and optionally launch an agent layout for runtime-test generation |

Key behavior:

- `init` defaults to Python `3.13` and package groups `p,t,l,i,d`; `--tmp-dir` creates a temporary project, `--libraries` adds extra packages, and `--group` accepts comma-separated group keys.
- `generate-upgrade-script [ROOT]` writes `pyproject_init.sh` without running it. After writing the script, `--clean-group` immediately clears selected dependency groups or extras, `--clean-all-groups` clears all groups and extras, and `--delete-venv` deletes the project's `.venv`. Repeat `--clean-group` to select multiple groups. Run the generated script separately to upgrade dependencies.
- `type-check [REPO]` resolves the repository root from the nearest `pyproject.toml` and passes exclusions through the lint/type-check script.
- If `--exclude` is omitted, `type-check` currently defaults to excluding `tests`, `.github`, `.codex`, `.ai`, `.links`, and `.venv`.
- `check-deps [TARGET]` runs either `pyan3` or `pydeps` through `uv run --with`, emits JSON/JSONIC by default, can write interactive HTML under `./.ai/check_deps`, and highlights direct mutual dependencies plus larger cycle groups. Use `--format/-F` for `json`, `jsonic`, or `html`, and `--output/-o` for a destination file.
- `configure-linters [DIRECTORY]` writes the standard `ruff`, `mypy`, `pylint`, `flake8`, and `ty` configurations at the git working-tree root. Use `--linter/-t` to select one; existing divergent files are never overwritten.
- `cleanup [REPO]` cleans one git working tree by default. Use `--recursive/-r` to discover and clean repositories below a directory.
- `test-reference [REPO]` supports `--search-root` and `--verbose`.
- `type-fix` is a nested app whose callback runs when invoked with no subcommand. It accepts `--agent`, `--agent-load`, `--which-checker`/`--which`, and `--max-agents`, generates a layout under `./.ai/agents/fix_<checker>_issues/`, then prompts to run it.
- `generate-tests` prepares agents to write runtime tests. It runs from the current directory, writes context to `.ai/agents/test_runtime/context.md`, skips hidden paths, `.venv`, and existing repo test files, then prompts to launch the agents. It does not run an existing test suite.

Examples:

```bash
utils pyproject init --name sample --python 3.14
utils pyproject generate-upgrade-script . --clean-group dev
utils pyproject generate-upgrade-script . --clean-all-groups --delete-venv
utils pyproject type-check . --exclude tests --exclude .venv
utils pyproject check-deps . --backend pyan --format html
utils pyproject check-deps src/my_package --backend pydeps --focus my_package --edge-filter dual
utils pyproject configure-linters ~/code/myrepo --linter ruff
utils pyproject cleanup ~/code/stackops
utils pyproject cleanup ~/code --recursive
utils pyproject test-reference . --verbose
utils pyproject type-fix --which-checker pyright --agent codex
utils pyproject generate-tests --agent codex --agent-load 5
```

## file

```bash
utils file [OPTIONS] COMMAND [ARGS]...
```

| Command | Summary |
|---------|---------|
| `edit` | Open a file or project path in the default editor |
| `download` | Download a file and optionally decompress it |
| `scrape` | Scrape a page to Markdown with Scrapling |
| `merge-pdf` | Merge two or more PDF files |
| `compress-pdf` | Compress a PDF file |
| `ocr` | Run Surya OCR, layout, detection, or table recognition |
| `read-db` | Launch a terminal database client |

Key behavior:

- `download [URL]` supports `--decompress`, `--output`, and `--output-dir`.
- `scrape [URL] [OUTPUT_PATH]` wraps `uvx "scrapling[shell]" extract stealthy-fetch`, defaulting to `f.md`, `article` selectors, `--wait 2000`, `--timeout 60000`, and `--enable-resources`. Additional options: `--output/-o` (alternative to positional output path), `--selector/-s` (CSS selector), `--wait-selector/-W` (CSS selector to wait for), `--enable-resources/-e/-E` (toggle browser resources), `--package-spec/-p` (uvx package spec).
- `merge-pdf PDFS...` requires at least two distinct input files, defaults to `merged.pdf`, refuses to overwrite an existing output, and can `--compress` the merged output.
- `compress-pdf PDF_INPUT` defaults to `<input>_compressed.pdf` and supports `--quality` and `--image-dpi`. Stream and object-stream compression are enabled by default; use `--no-compress-streams/-C` or `--no-object-streams/-S` to disable either behavior.
- `ocr DATA_PATH` runs the `surya-ocr` package through `uv run --with ... --no-project` without importing Surya during CLI startup. Use `--task` with `ocr`, `detect`, `layout`, or `table`; common Surya flags include `--output-dir`, `--page-range`, `--images`, `--debug`, `--keep-server`, and `--skip-table-detection` (table task only). `--package-spec/-P` overrides the uv package spec. Extra Surya flags can be passed after `--`.
- `read-db [PATH]` defaults to the `harlequin` backend. Provide only one of positional `PATH`, `--url/-u`, or `--find/-f`; `--find-root` and `--recursive` refine file discovery.
- `read-db` supports backends `rainfrog`, `lazysql`, `dblab`, `usql`, `harlequin`, and `sqlit` plus their one-letter aliases. Local databases open read-only by default; `--read-write/-w` disables read-only mode. StackOps rejects a local backend that cannot provide verified read-only access unless `--read-write` is set. `--theme/-t` sets the TUI theme when supported by the backend. `--limit/-l` caps the number of rows loaded when supported by the backend.

Examples:

```bash
utils file edit .
utils file download https://example.com/archive.tar.gz --decompress --output-dir ./downloads
utils file scrape https://example.com/article article.md
utils f s https://example.com/article
utils file merge-pdf a.pdf b.pdf c.pdf --output merged.pdf
utils file compress-pdf report.pdf --output report-small.pdf --quality 75 --image-dpi 144
utils file ocr report.pdf --task ocr --output-dir ./surya-results --page-range 0,5-10 --images
utils f o table.png --task table --skip-table-detection -- --debug
utils file read-db ./local.db --backend harlequin
utils file read-db --find "*.duckdb" --recursive
utils file read-db --url postgres://postgres:1234@192.168.20.4:5432/binance
```

## Typical Flow

Use live help to drill into the subgroup you need:

```bash
utils --help
utils machine --help
utils machine mount --help
utils pyproject --help
utils pyproject type-check --help
utils pyproject configure-linters --help
utils pyproject cleanup --help
utils pyproject test-reference --help
utils pyproject type-fix --help
utils pyproject generate-tests --help
utils file --help
utils file read-db --help
```
