## self

Self management commands.

```bash
devops self [SUBCOMMAND] [ARGS]...
```

Manage stackops itself: upgrades, install flows, docs preview, CLI graph exploration, and repo-local developer utilities.

Current `devops self --help` exposes:

| Command | Description | Availability |
|---------|-------------|--------------|
| `install` | Install stackops locally, optionally from a development checkout | Always |
| `clone` | Clone the StackOps source checkout into a local directory | Always |
| `update` | Upgrade stackops, refresh packaged assets, and optionally apply packaged settings | Always |
| `status` | Inspect machine, repository, application, and configuration state | Always |
| `explore-cli` | Search, run, or inspect the CLI graph in terminal, DOT, Plotly, or TUI form | Always |
| `explore-python-api` | Inspect the documented Python API graph in terminal, DOT, Plotly, or search form | Always |
| `readme` | Render the project README in the terminal | Always |
| `docs` | Serve the local docs preview, optionally after rebuilding | Only when `~/code/stackops` exists |
| `build-installer` | Export installation files for an offline installer image | Always |
| `download-installer` | Download and extract a published offline installer image | Always |
| `release` | Bump the calendar version and update version references | Only when `~/code/stackops` is a StackOps Git checkout |
| `build-docker` | Build Docker images from the repo script | Only when `~/code/stackops` exists |
| `build-graph` | Build the architecture dependency graph | Only when `~/code/stackops` exists |
| `build-assets` | Regenerate the checked-in CLI graph snapshot and chart artifacts | Only when `~/code/stackops` exists |

### update

Upgrade the installed tool, refresh packaged assets, and optionally apply the packaged settings to their default paths.

```bash
devops self update [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--sync-configs`, `-l` | Apply the packaged settings after the update, overwriting your configs at their default paths |
| `--no-copy-assets`, `-a` | Skip copying scripts and settings after the update |
| `--config-shell`, `-s` | Create or configure the default shell profile after the update |
| `--dev`, `-d` | Before updating, commit local changes in the development checkout and sync it with origin (`pull --rebase`, then push) |

Current behavior:

- If the `~/code/stackops` checkout exists, the command pulls it with `git pull --ff-only`, runs `uv self update`, and reinstalls the checkout as an editable tool.
- Otherwise it updates `uv` and upgrades the installed `stackops` tool package.
- After the update succeeds, it copies packaged scripts and settings onto the current machine, unless `--no-copy-assets` is passed.
- `--sync-configs` additionally runs the equivalent of `devops config dotfiles sync down --source library --method copy --on-conflict overwrite-default-path --which all`.

Examples:

```bash
devops self update
devops self update --sync-configs
```

### status

Inspect the current machine, optionally limited to specific sections.

```bash
devops self status [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--machine`, `-m` | Show the machine and system information section |
| `--shell`, `-s` | Show the shell profile section |
| `--repos`, `-r` | Show the configured repositories section |
| `--ssh`, `-H` | Show the SSH configuration section |
| `--configs`, `--dotfiles`, `--symlinks`, `-c`, `-d`, `-l` | Show managed files, schemas, configuration mappings, and symlinks |
| `--apps`, `--tools`, `-a`, `-t` | Show installed apps and tools |
| `--backup`, `-b` | Show backup configuration status |
| `--plain`, `-p` | Print a report instead of opening the interactive dashboard |
| `--json`, `-j` | Print structured section results |
| `--as-html`, `-w` | Write a navigable HTML dashboard of the selected sections and open it in the browser; cannot be combined with `--json` or `--plain` |

Without section flags, the command includes all sections. Use `--plain` for a printed report.

### install

Install stackops locally, optionally from a local development checkout.

```bash
devops self install [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--dev`, `-d` | Install from a local development checkout instead of PyPI |

Current behavior:

- `--dev` clones `~/code/stackops` first when that checkout does not already exist, then installs it editable.
- Without `--dev`, it installs the published tool package from PyPI.
- Either way, it then creates or configures the default shell profile.

Examples:

```bash
devops self install
devops self install --dev
```

### clone

Clone the StackOps source checkout. The positional `DIRECTORY` is the checkout directory itself and defaults to the current working directory.

```bash
devops self clone [OPTIONS] [DIRECTORY]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--remote`, `-r` | Git remote URL to clone from |
| `--ssh`, `-s` | Use the built-in SSH remote instead of HTTPS |
| `--branch`, `-b` | Branch or tag to check out |
| `--depth`, `-d` | Create a shallow clone with the given depth |
| `--pull`, `-p` | Pull an existing checkout with `--ff-only` |
| `--install`, `-i` | Run `uv sync` and install the checkout editable |
| `--dry-run`, `-n` | Print planned git and uv actions without changing files |

Examples:

```bash
devops self clone
devops self clone ~/code/stackops --ssh
devops self clone ~/code/stackops --branch main --depth 1
devops self clone ~/code/stackops --pull --install
```

### build-installer

Export the installation files used to create an offline installer image.

```bash
devops self build-installer
devops self build-installer --upload-to-cloud
```

The installer folder and zip archive are written under `~/.config/stackops/offline_installers` unless `--output-dir`, `-o` is given. `--no-include-configs`, `-c` leaves out the StackOps config tree, `--no-include-uv-bundle`, `-b` leaves out the uv-managed runtime bundle, `--keep-unpacked`, `-k` keeps the unpacked installer directory after the zip is written, and `--json`, `-j` prints the artifact receipt as JSON.

Use `--upload-to-cloud`, `-u` to upload the generated archive to the mirrored path on the configured default rclone remote, generate a shared URL, and update the JSON URL map consumed by `scripts_dynamic/download_stackops_offline_installer.py`. It requires an editable install backed by the `~/code/stackops` checkout.

### download-installer

Download and extract an offline installer published in `download_stackops_offline_installer.json`.

```bash
devops self download-installer
devops self download-installer --list
devops self download-installer --target linux-x64
devops self download-installer --target linux-x64 --output-dir ~/stackops-offline-installer-linux-x64
```

Valid targets are `linux-x64`, `linux-arm`, `macos-x64`, `macos-arm`, `windows-x64`, and `windows-arm`. The checked-in URL map currently publishes only `linux-x64`; the other targets are accepted but exit with `No Google Drive URL is configured yet for <target>`. An existing output directory is deleted before extraction.

When `--target`, `-t` is omitted, StackOps prompts for one of the configured OS/architecture pairs. `--list`, `-l` prints the targets and whether each has a published installer, without downloading. By default, the installer is extracted to `~/.config/stackops/offline_installers/stackops-offline-installer-<target>`; `--output-dir`, `-o` overrides it. `--json`, `-j` prints the target list or the downloaded artifact as JSON.

### explore-cli

CLI graph inspection lives under a nested Typer app:

```bash
devops self explore-cli [SUBCOMMAND] [ARGS]...
```

Current `devops self explore-cli --help` exposes:

| Command | Description |
|---------|-------------|
| `search` | Search all `cli_graph.json` command entries |
| `run` | Pick a command, fill its arguments and options, then type, run, or print it |
| `tree` | Render a rich tree view in the terminal |
| `dot` | Export the graph as Graphviz DOT |
| `view` | Render a Plotly hierarchy chart (`sunburst`, `treemap`, or `icicle`) |
| `tui` | Open the full-screen Textual navigator |

#### search

Interactive fuzzy-search over the generated CLI graph JSON. The optional `QUERY`
narrows the entries by command name, description, and source path. By default it
shows a rendered Markdown summary for the selected command or group; use `--json`
or `-j` to print every matching entry as a JSON array without a picker.

```bash
devops self explore-cli search [OPTIONS] [QUERY]
```

Key options:

| Option | Description |
|--------|-------------|
| `--graph-path`, `-g` | Override the path to `cli_graph.json` |
| `--json`, `-j` | Print all matching `cli_graph.json` entries as a JSON array, without prompts or a picker |
| `--non-interactive`, `-N` | List the matching commands without opening a picker |

#### run

Pick a command from the graph, answer prompts for its arguments and options, then act on the built command line.

```bash
devops self explore-cli run [OPTIONS] [QUERY]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--action`, `-a` | `type` (default) pre-types the command in your shell prompt, `run` executes it now, `print` prints it to stdout |
| `--skip-prompts`, `-s` | Skip the argument and option prompts and use the bare command |
| `--graph-path`, `-g` | Override the path to `cli_graph.json` |

#### tree

Render the graph as a terminal tree. Help text is shown in each node label by default.

```bash
devops self explore-cli tree [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--no-show-help`, `-H` | Hide help text in node labels |
| `--show-aliases`, `-a` | Include aliases in labels |
| `--max-depth`, `-d` | Limit the rendered depth |

Example:

```bash
devops self explore-cli tree --max-depth 2
```

#### dot

Export the graph as Graphviz DOT text. Help text is included in labels by default.

```bash
devops self explore-cli dot [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--output`, `-o` | Write DOT output to a file |
| `--no-include-help`, `-H` | Hide help text in labels |
| `--max-depth`, `-d` | Limit the exported depth |

Example:

```bash
devops self explore-cli dot --max-depth 2
```

#### view

Render the graph as a Plotly hierarchy chart. The default view is `sunburst`.

```bash
devops self explore-cli view [OPTIONS] [VIEW]
```

Supported `VIEW` values from current help:

| Value | Meaning |
|-------|---------|
| `sunburst` | Render a sunburst chart |
| `treemap` | Render a treemap chart |
| `icicle` | Render an icicle chart |

Key options from current help:

| Option | Description |
|--------|-------------|
| `--output`, `-o` | Write HTML or image output |
| `--max-depth`, `-d` | Limit depth of the graph |
| `--template`, `-t` | Plotly template name (default `plotly_dark`) |
| `--height`, `-H` | Static image height (default 900) |
| `--width`, `-w` | Static image width (default 1200) |

Examples:

```bash
devops self explore-cli view
devops self explore-cli view treemap
devops self explore-cli view icicle --output /tmp/icicle.html
```

<iframe
  class="plotly-preview-frame"
  src="../assets/devops-self-explore/sunburst.html"
  title="Interactive sunburst preview"
  loading="lazy"
></iframe>

Checked-in example: [sunburst.html](../assets/devops-self-explore/sunburst.html)

Only the sunburst artifact is checked in by default. Use `--output` if you want local treemap or icicle exports.

#### tui

Open the full-screen Textual navigator.

```bash
devops self explore-cli tui
```

Interactive controls:

- `/` focuses search
- `c` copies the selected command
- `r` runs the selected command
- `b` builds the selected command with arguments
- `?` opens in-app help
- `q` quits

No static screenshot is checked into the docs for the TUI. Launch it locally to inspect the current command tree.

### explore-python-api

Python API graph inspection lives under a separate nested Typer app:

```bash
devops self explore-python-api [SUBCOMMAND] [ARGS]...
```

Current `devops self explore-python-api --help` exposes:

| Command | Description |
|---------|-------------|
| `search` | Search API entries and show the selected import summary |
| `tree` | Render a rich tree view in the terminal |
| `dot` | Export the graph as Graphviz DOT |
| `view` | Render a Plotly hierarchy chart (`sunburst`, `treemap`, or `icicle`) |
| `dump` | Write the generated Python API graph JSON |
| `explain-filter` | Explain how API files and members are selected |

`search`, `tree`, `dot`, and `view` take the same options as their `explore-cli` counterparts (`tree` has no `--show-aliases`), and each accepts `--graph-path`, `-g` to read an existing Python API graph JSON file. `dump` requires the output path.

The API graph starts from `docs/api` instead of the raw source tree. It includes modules named by mkdocstrings directives and explicit docs imports, then uses AST inspection to include public classes, functions, async functions, and uppercase constants. Private names and common CLI wiring helpers such as `main`, `get_app`, `app`, and `cli_app` are skipped.

Examples:

```bash
devops self explore-python-api tree --max-depth 3
devops self explore-python-api dot --max-depth 2
devops self explore-python-api dump /tmp/stackops-python-api.json
devops self explore-python-api explain-filter
```

### release

Bump the calendar version and update the StackOps version references in the `~/code/stackops` Git checkout, then reinstall the editable tool so `stackops --version` reports the new version.

```bash
devops self release [--publish]
```

Without `--publish`, the release changes are left uncommitted for review. `--publish`, `-p` commits them and pushes `main` with its version tag to origin; it requires a clean `main` branch synchronized with origin.

This command is only registered when `~/code/stackops` is a StackOps Git checkout.

### build-docker

Build the repo Docker image variants through the checked-in shell wrapper. The local image is built as `stackops-VARIANT:latest`; without `--publish`, no Docker credentials are read. With `--publish`, `-P`, the command first looks up Docker publish credentials with `search_logins`, builds the image, then passes the matched `keyValues` only to the publish process and uses the matched login's `entries[].username` as the remote image namespace. `--json`, `-j` prints an image/result receipt as JSON.

```bash
devops self build-docker VARIANT [OPTIONS]
```

Supported variants from current help (`VARIANT` is required):

| Variant | Meaning |
|---------|---------|
| `slim` | Build the slim image |
| `ai` | Build the AI-oriented image |

Examples:

```bash
devops self build-docker ai
devops self build-docker ai --publish
```

By default, Docker credentials are selected from the login named `docker` with one of these token env keys: `DOCKER_TOKEN`, `DOCKERHUB_TOKEN`, `DOCKER_PASSWORD`, or `DOCKER_PAT`. Use `--docker-login-name`/`-n`, `--docker-account-name`/`-a`, `--docker-secret-name`/`-N`, `--docker-secret-tag`/`-T`, `--docker-scope`/`-S`, `--docker-token-key`/`-k`, or `--docker-secrets-path`/`-p` to narrow the match.

This command is only registered when `~/code/stackops` exists locally.

### Security: `devops security`

Security helpers live under a nested Typer app:

```bash
devops security [SUBCOMMAND] [ARGS]...
```

Security is a top-level group. Current `devops security --help` exposes:

| Command | Description |
|---------|-------------|
| `scan` | Scan installed apps or a single file with VirusTotal |
| `status` | Show installed apps with their latest scan verdict |
| `list` | List installed apps, optionally filtered by name |
| `upload` | Upload a local file to cloud storage and print its share link |
| `download` | Download a file from Google Drive |
| `install` | Install safe apps from one saved scan run |
| `report` | Inspect one saved run; defaults to the latest started run |
| `history` | List saved scan runs, newest first |
| `export` | Export one run to a new directory |

`scan`, `status`, `install`, `report`, `history`, and `export` accept `--records-dir`, `-d` to use another scan history directory; the default is `~/.config/stackops/profile/records/<os>/security`.

#### scan

Scan installed apps or one local file path with VirusTotal. Exactly one of `APPS`, `--path`, or `--all` is required. Every scan is saved as a separate history run unless `--no-record` is passed.

```bash
devops security scan [OPTIONS] [APPS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `APPS` | Comma-separated installed app names to scan |
| `--path`, `-p` | Scan one explicit file path instead of installed apps |
| `--all`, `-a` | Scan all installed apps |
| `--no-record`, `-n` | Do not save this scan as a history run |
| `--upload`, `-u` | Upload each file to cloud storage after its VirusTotal check completes |
| `--concurrency`, `-c` | Maximum concurrent files; defaults to the number of configured VirusTotal accounts |

Examples:

```bash
devops security scan --all
devops security scan git,uv
devops security scan --path ./downloads/tool.exe --no-record
```

#### status

Show the installed apps with their latest scan verdict. `--json`, `-j` prints the overview as JSON.

```bash
devops security status
```

#### list

List the installed CLI apps that the security tooling knows how to inspect. `--json`, `-j` prints their metadata as JSON.

```bash
devops security list [APPS]
```

Example:

```bash
devops security list git,uv
```

#### upload

Upload one local file to the configured default rclone remote and print its share link.

```bash
devops security upload PATH
```

Example:

```bash
devops security upload ./dist/tool.exe
```

#### download

Download a previously shared file from Google Drive.

```bash
devops security download URL
```

The argument can be a full Google Drive URL or a raw file id.

#### install

Install safe apps from one saved scan run.

```bash
devops security install [OPTIONS] [NAME]
```

Pass one app `NAME` from the run, or `--all`, `-a` for every eligible app; exactly one of the two is required. `--run`, `-R` selects an exact run ID and defaults to the latest started run. Only apps from a finished run with no positive detections and a saved download link are eligible.

#### report

Inspect one saved run in full, summary, table, CSV, or JSON form. The default invocation shows the full engine-level report of the latest started run.

```bash
devops security report [OPTIONS] [APPS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `APPS` | Optional comma-separated app names to filter on |
| `--run`, `-R` | Exact run ID; defaults to the latest started run |
| `--view`, `-v` | Choose `engines`, `app-summary`, `apps`, `options`, `stats`, or `accounts` |
| `--format`, `-f` | Choose `table` or `csv` output; CSV is supported for the `apps`, `engines`, and `accounts` views |
| `--json`, `-j` | Print the run as JSON: its targets, engine results, and account statistics |

Examples:

```bash
devops security report
devops security report --view app-summary
devops security report --view stats
devops security report uv --view apps --format csv
devops security report git --view engines
```

#### history

List saved scan runs, newest first. `APPS` limits the list to runs targeting those apps, `--limit`, `-l` caps the number of runs (default 20), and `--format`, `-f` (`table` or `csv`) or `--json`, `-j` changes the output.

```bash
devops security history [OPTIONS] [APPS]
```

#### export

Write one run to a new directory as `run.json`, `apps.csv`, `engines.csv`, and `accounts.csv`. `--output`, `-o` is required and must not exist yet; `--run`, `-R` defaults to the latest started run.

```bash
devops security export --output ./scan-export
```

### docs

Serve the local docs preview and print the localhost and LAN URLs.

```bash
devops self docs [OPTIONS]
```

Key options:

| Option | Description |
|--------|-------------|
| `--rebuild`, `-b` | Rebuild the docs before starting the preview server |
| `--create-artifacts`, `-a` | Regenerate the Plotly CLI graph HTML artifacts before serving |

Current behavior:

- Prints `http://127.0.0.1:8000/stackops/` and, when available, the LAN preview URL.
- With `--rebuild`, runs `zensical build` before `zensical serve`.
- With `--create-artifacts`, regenerates both `src/stackops/scripts/python/graph/cli_graph.json` and `docs/assets/devops-self-explore/sunburst.html`.
- Serves on `0.0.0.0:8000`.

Examples:

```bash
devops self docs
devops self docs --rebuild
devops self docs --rebuild --create-artifacts
```

### build-assets

Regenerate the checked-in CLI graph JSON and chart artifacts from the local repo checkout.

```bash
devops self build-assets [SUBCOMMAND] [ARGS]...
```

Current `devops self build-assets --help` exposes:

| Command | Description |
|---------|-------------|
| `cli-graph` | Rewrite `src/stackops/scripts/python/graph/cli_graph.json` from the current Typer source |
| `charts` | Rewrite `docs/assets/devops-self-explore/sunburst.html` from the current graph snapshot |
| `skill-refs` | Regenerate the StackOps skill CLI reference maps |

Examples:

```bash
devops self build-assets cli-graph
devops self build-assets charts
devops self build-assets skill-refs
```

This sub-app is only registered when `~/code/stackops` exists locally.

### build-graph

Build the architecture dependency graph from the local repo checkout and write the HTML output.

```bash
devops self build-graph [OPTIONS]
```

Key option:

| Option | Description |
|--------|-------------|
| `--view`, `-v` | Preview the generated HTML graph in the browser |

Example:

```bash
devops self build-graph
devops self build-graph --view
```

This command is only registered when `~/code/stackops` exists locally.

### readme

Render the project README in the terminal. When the `~/code/stackops` checkout exists, it reads the local `README.md`; otherwise it reads the README stored in the installed `stackops` package metadata.

```bash
devops self readme
```

This keeps local development checkouts authoritative while still working on machines that do not have the repo cloned.

---
