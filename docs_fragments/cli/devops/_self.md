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
| `update` | Upgrade stackops, refresh packaged assets, and optionally relink public configs | Always |
| `status` | Inspect machine, shell, repo, SSH, config, app, or backup state | Always |
| `security` | Run security and installer-audit helpers | Always |
| `explore` | Inspect the CLI graph in terminal, DOT, Plotly, or TUI form | Always |
| `readme` | Fetch and render the project README in the terminal | Always |
| `docs` | Serve the local docs preview, optionally after rebuilding | Only when `~/code/stackops` exists |
| `build-installer` | Export installation files for an offline installer image | Always |
| `build-docker` | Build Docker images from the repo script | Only when `~/code/stackops` exists |
| `build-assets` | Regenerate the checked-in CLI graph snapshot and chart artifacts | Only when `~/code/stackops` exists |

The nested help screens render shortened usage such as `Usage: devops update ...`, but the full entrypoints remain `devops self ...` and `devops self security ...`.

### update

Upgrade the installed tool, refresh packaged assets, and optionally relink public configs.

```bash
devops self update [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--link-public-configs`, `-b` | Re-link public configs after the update |

Current behavior:

- If `~/code/stackops` exists, the command runs `uv self update`, `git pull`, and reinstalls the repo checkout as an editable tool.
- Otherwise it updates `uv` and upgrades the installed `stackops` tool package.
- After the update succeeds, it copies packaged scripts and settings onto the current machine.
- On non-Windows platforms, `--link-public-configs` additionally re-links the public config set.

Examples:

```bash
devops self update
devops self update --link-public-configs
```

### status

Run the self-audit report for the current machine, optionally limited to specific sections.

```bash
devops self status [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--machine`, `-m` | Show the machine and system information section |
| `--shell`, `-s` | Show the shell profile section |
| `--repos`, `-r` | Show the configured repositories section |
| `--ssh`, `-h` | Show the SSH configuration section |
| `--configs`, `--dotfiles`, `--symlinks`, `-c`, `-d`, `-l` | Show linked config, dotfile, and symlink state |
| `--apps`, `--tools`, `-a`, `-t` | Show installed apps and tools |
| `--backup`, `-b` | Show backup configuration status |

Without flags, the command prints the full report.

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
- Without a local checkout, the default path installs the published tool package.

Examples:

```bash
devops self install
devops self install --dev
```

### build-installer

Export the installation files used to create an offline installer image.

```bash
devops self build-installer
```

This command wraps the offline installer export path and does not accept extra options.

### explore

CLI graph inspection lives under a nested Typer app:

```bash
devops self explore [SUBCOMMAND] [ARGS]...
```

Current `devops self explore --help` exposes:

| Command | Description |
|---------|-------------|
| `search` | Search all `cli_graph.json` command entries |
| `tree` | Render a rich tree view in the terminal |
| `dot` | Export the graph as Graphviz DOT |
| `view` | Render a Plotly hierarchy chart (`sunburst`, `treemap`, or `icicle`) |
| `tui` | Open the full-screen Textual navigator |

#### search

Interactive fuzzy-search over the generated CLI graph JSON. By default it runs `--help`
for the selected command or group; use `--show-json` to print the raw graph entry.

```bash
devops self explore search [OPTIONS]
```

Key option:

| Option | Description |
|--------|-------------|
| `--graph-path`, `-g` | Override the path to `cli_graph.json` |
| `--show-json` | Print the selected `cli_graph.json` entry instead of running help |

#### tree

Render the graph as a terminal tree.

```bash
devops self explore tree [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--show-help` | Include help text in each node label |
| `--show-aliases` | Include hidden aliases in labels |
| `--max-depth`, `-d` | Limit the rendered depth |

Example:

```bash
devops self explore tree --max-depth 2
```

#### dot

Export the graph as Graphviz DOT text.

```bash
devops self explore dot [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--output`, `-o` | Write DOT output to a file |
| `--include-help` | Include help text in labels |
| `--max-depth`, `-d` | Limit the exported depth |

Example:

```bash
devops self explore dot --max-depth 2
```

#### view

Render the graph as a Plotly hierarchy chart. The default view is `sunburst`.

```bash
devops self explore view [OPTIONS] [VIEW]
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
| `--template` | Plotly template name |
| `--height` | Static image height |
| `--width` | Static image width |

Examples:

```bash
devops self explore view
devops self explore view treemap
devops self explore view icicle --output /tmp/icicle.html
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
devops self explore tui
```

Interactive controls:

- `/` focuses search
- `c` copies the selected command
- `r` runs the selected command
- `b` builds the selected command with arguments
- `?` opens in-app help
- `q` quits

No static screenshot is checked into the docs for the TUI. Launch it locally to inspect the current command tree.

### build-docker

Build the repo Docker image variants through the checked-in shell wrapper.

```bash
devops self build-docker [VARIANT]
```

Supported variants from current help:

| Variant | Meaning |
|---------|---------|
| `slim` | Build the slim image |
| `ai` | Build the AI-oriented image |

Example:

```bash
devops self build-docker ai
```

This command is only registered when `~/code/stackops` exists locally.

### security

Security helpers live under a nested Typer app:

```bash
devops self security [SUBCOMMAND] [ARGS]...
```

Current `devops self security --help` exposes:

| Command | Description |
|---------|-------------|
| `scan` | Scan installed apps or a single file with VirusTotal |
| `list` | List installed apps, optionally filtered by name |
| `upload` | Upload a local file to the project cloud storage |
| `download` | Download a file from Google Drive |
| `install` | Install safe apps from the saved app metadata report |
| `repo-licenses` | Download GitHub repo license files for installer entries |
| `report` | Inspect saved scan reports, raw rows, or summary statistics |

#### scan

Scan installed apps or one local file path with VirusTotal.

```bash
devops self security scan [OPTIONS] [APPS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `APPS` | Optional comma-separated app names to scan |
| `--path` | Scan one explicit file path instead of installed apps |
| `--record`, `--no-record` | Control whether the result is saved into the repo reports |

Examples:

```bash
devops self security scan
devops self security scan git,uv
devops self security scan --path ./downloads/tool.exe --no-record
```

#### list

List the installed CLI apps that the security tooling knows how to inspect.

```bash
devops self security list [APPS]
```

Example:

```bash
devops self security list git,uv
```

#### upload

Upload one local file into the cloud storage used by the security workflow.

```bash
devops self security upload PATH
```

Example:

```bash
devops self security upload ./dist/tool.exe
```

#### download

Download a previously shared file from Google Drive.

```bash
devops self security download URL
```

The argument can be a full Google Drive URL or a raw file id.

#### install

Install a safe app from the saved metadata report.

```bash
devops self security install NAME
```

`NAME` can be one app entry from the report or the special `essentials` bundle.

#### repo-licenses

Download GitHub license files for repos referenced by the installer metadata.

```bash
devops self security repo-licenses [OPTIONS]
```

Key option:

| Option | Description |
|--------|-------------|
| `--github-token` | GitHub token, also read from `STACKOPS_GITHUB_TOKEN`, `GITHUB_TOKEN`, or `GH_TOKEN` |

#### report

Inspect saved report data in full, summary, table, or CSV form. The default invocation shows the full engine-level report.

```bash
devops self security report [OPTIONS] [APPS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `APPS` | Optional comma-separated app names to filter on |
| `--view`, `-v` | Choose `engines`, `app-summary`, `apps`, `options`, or `stats` |
| `--format`, `-f` | Choose `table` or `csv` output for the raw `apps` and `engines` views |

Examples:

```bash
devops self security report
devops self security report --view app-summary
devops self security report --view stats
devops self security report uv --view apps --format csv
devops self security report git --view engines
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
| `update-cli-graph` | Rewrite `src/stackops/scripts/python/graph/cli_graph.json` from the current Typer source |
| `regenerate-charts` | Rewrite `docs/assets/devops-self-explore/sunburst.html` from the current graph snapshot |

Examples:

```bash
devops self build-assets update-cli-graph
devops self build-assets regenerate-charts
```

This sub-app is only registered when `~/code/stackops` exists locally.

### readme

Render the project README in the terminal. When `~/code/stackops` exists, it reads the local `README.md`; otherwise it fetches the upstream README from GitHub.

```bash
devops self readme
```

This keeps local development checkouts authoritative while still working on machines that do not have the repo cloned.

---
