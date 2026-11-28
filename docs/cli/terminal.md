# terminal

The Herdr backend supports only the latest Herdr CLI and server. See the [Herdr CLI reference](https://herdr.dev/docs/cli-reference/) for current command syntax. The Zellij backend requires Zellij 0.45 or newer.

## Usage

```bash
terminal [OPTIONS] COMMAND [ARGS]...
```

## Commands Overview

| Command | Description |
|---------|-------------|
| `run` | Launch selected layouts from a layout file or generated test layout |
| `run-all` | Dynamically work through every tab in one merged run |
| `list` | List saved layouts, with optional tab details and statistics |
| `edit` | Edit a layout file and validate it after saving |
| `path` | Print layout configuration and schema paths as JSON |
| `init` | Create a missing layout configuration and its schema |
| `validate` | Validate a layout configuration |
| `attach` | Attach to an existing session, window/tab, or pane |
| `kill` | Kill sessions, idle panes, or one exact window/tab or pane |
| `export` | Export running backend sessions or workspaces into a layout file |
| `trace` | Trace backend sessions until a strict stop condition is met |
| `summary` | Print running session summaries or one session's details |
| `run-function` | Immediately launch a script function in multiple tmux processes |
| `balance-load` | Re-split a layout file by tab count or weight |
| `create-template` | Create a starter layout file in the current directory |

Hidden one-letter aliases exist, but this page uses canonical command names.

`terminal --non-interactive` / `-N` (or the `STACKOPS_NON_INTERACTIVE` environment variable) never prompts or opens a picker or editor; it is also enabled automatically without a terminal. A command that would need a picker then exits with a usage error asking for explicit inputs.

## Common Layout Source Rules

- `run`, `run-all`, and `list` accept `--source` / `-s`: `workspace/w`, `user/u`, or `all/a`, defaulting to `all`.
- The workspace root is the enclosing Git repository root, including when called from a subdirectory, or the current directory when it contains at least two immediate child Git repositories. Outside these locations, the workspace source is unavailable.
- Without `--custom-path` or `--test-layout`, `--source all` combines named layouts from the user file at `~/dotfiles/stackops/config/layout.yaml`, the workspace file at `<workspace-root>/.stackops/config/layout.yaml`, and `.stackops/config/layout.yaml` in each immediate child directory of the root that has one, labelled `workspace:<child>`, including each file that exists. `path`, `init`, `validate`, and `edit` with `--source workspace` use the root file. When the workspace source is unavailable, `all` includes only the user source; explicit `--source workspace` fails. `run` and `run-all` open a picker for the selected source files; cancelling it aborts the command.
- The default picker labels entries `user:name`, `workspace:name`, or `workspace:<child>:name` and previews their source file paths. Layout and session names remain unchanged.
- `--custom-path` / `-p` overrides `--source` and loads layouts only from the supplied file, including outside a workspace.
- For `run`, an explicit `--choose-layouts` or `--choose-tabs` selector uses that selection without opening an additional layout picker.
- `run` and `run-all` also support `--test-layout`, which generates a built-in finite layout set for experimentation and cannot be combined with `--custom-path`.
- `--choose-layouts` / `-l` without a value (or with `""`) opens interactive layout selection.
- Named layout selectors accept an unambiguous name or `user:name` / `workspace:name`. A name shared by both sources requires the qualified form.
- `--choose-tabs` / `-t` without a value (or with `""`) opens interactive tab selection across all layouts, or across the layouts selected with `-l`.
- Tab selectors accept `tabName` or `layoutName::tabName`. When both sources share a layout name, qualify it as `user:layoutName::tabName` or `workspace:layoutName::tabName`; an ambiguous layout name is rejected. Bare tab names match across selected layouts.

## run

Launch selected layouts from an explicit file or the selected configuration sources.

```bash
terminal run [OPTIONS]
```

| Argument / Option | Short | Description |
|-------------------|-------|-------------|
| `--custom-path` | `-p` | Optional layout file path that overrides `--source` |
| `--source` | `-s` | `workspace/w`, `user/u`, or `all/a`; defaults to `all` |
| `--test-layout` | `-L` | Use the generated mock layout instead of reading a file |
| `--choose-layouts` | `-l` | Comma-separated layout names; without a value, interactive selection |
| `--choose-tabs` | `-t` | Comma-separated tab names; without a value, interactive selection across all layouts or those chosen with `-l` |
| `--launch-delay` | `-S` | Delay in seconds between launching layouts; defaults to `1.0` |
| `--parallel-layouts` | `-j` | Maximum number of layouts to launch per monitored batch; implies `--monitor` |
| `--max-tabs-per-layout` | `-T` | Sanity limit for tabs inside a single selected layout; defaults to `25` |
| `--max-parallel-layouts` | `-P` | Sanity limit for total parallel layouts; defaults to `25` |
| `--backend` | `-b` | `tmux`/`t`, `herdr`/`h`, `tuios`/`u`, `aoe`/`e`, or `zellij`/`z`; omitted, uses `default_session_multiplexer` from the StackOps config, else `tmux` |
| `--on-conflict` | `-c` | `error` (default), `restart`, `rename`, `skip`, `merge-overwrite`, or `merge-skip`; the merge policies need tmux, TUIOS, or Zellij |
| `--exit` | `-e` | `back-to-shell` (default), `terminate`, or `kill-window` after each command exits |
| `--monitor` | `-m` | Monitor launched sessions for completion |
| `--kill-upon-completion` | `-k` | Kill sessions after monitored completion |
| `--substitute-home` | `-H` | Expand `~` and `$HOME` inside the selected layout tabs |
| `--attach` | `-a` | Attach to the first launched session (tmux, TUIOS, and Zellij); cannot be combined with `--monitor`, `--parallel-layouts`, or `--kill-upon-completion` |

Examples:

```bash
# Choose layouts from the user file and the workspace's .stackops/config/layout.yaml when present
terminal run

# Run unambiguous named layouts from the combined default files without prompting
terminal run --choose-layouts "dev,build"

# Choose layouts only from the workspace configuration
terminal run --source workspace

# Select the workspace dev layout when both sources define dev
terminal run --choose-layouts "workspace:dev"

# Select a tab from the workspace dev layout
terminal run --choose-tabs "workspace:dev::server"

# Run only selected layouts from an explicit file
terminal run --custom-path layout.yaml --choose-layouts "dev,build"

# Run a generated test layout
terminal run --test-layout --parallel-layouts 2 --monitor

# Select tabs by name or layout-qualified name
terminal run --custom-path layout.yaml --choose-tabs "server,build::tests"

# Restart matching sessions before relaunching
terminal run --custom-path layout.yaml --on-conflict restart

# Launch selected layouts through Herdr
terminal run --custom-path layout.yaml --backend herdr

# Launch selected layout tabs through Agent of Empires
terminal run --custom-path layout.yaml --backend aoe

# Launch through Zellij and attach to the first launched session
terminal run --custom-path layout.yaml --backend zellij --attach
```

## run-all

Merge every tab from the selected layouts into one paced run. `--custom-path` uses all layouts from the given file and overrides `--source`; omitting it opens a picker for the selected sources, defaulting to all available user and workspace files. `--max-parallel-tabs` is required in both cases.

```bash
terminal run-all [OPTIONS]
```

| Argument / Option | Short | Description |
|-------------------|-------|-------------|
| `--custom-path` | `-p` | Optional file whose layouts all run; overrides `--source` |
| `--source` | `-s` | `workspace/w`, `user/u`, or `all/a`; defaults to `all` |
| `--test-layout` | `-L` | Use the generated mock layout instead of reading a file |
| `--max-parallel-tabs` | `-t` | Required cap for concurrently active tabs |
| `--poll-interval` | `-i` | Polling interval in seconds for finished-tab detection; defaults to `2.0` |
| `--backend` | `-b` | `tmux`/`t`, `tuios`/`u`, or `zellij`/`z`; omitted, uses `default_session_multiplexer` from the StackOps config, else `tmux`; any other configured value is rejected |
| `--kill-finished-tabs` | `-k` | Close each tab as soon as its command finishes |
| `--on-conflict` | `-c` | `error` (default), `restart`, or `rename`; `skip` and the merge policies are rejected |
| `--substitute-home` | `-H` | Expand `~` and `$HOME` inside selected tabs |

Examples:

```bash
# Choose layouts from the combined default files and keep at most eight tabs active
terminal run-all --max-parallel-tabs 8

# Choose only user layouts and keep at most eight tabs active
terminal run-all --source user --max-parallel-tabs 8

# Keep at most eight tabs active while working through the whole file
terminal run-all --custom-path layout.yaml --max-parallel-tabs 8

# Use the generated test layout and close finished tabs as work drains
terminal run-all --test-layout --max-parallel-tabs 6 --kill-finished-tabs
```

## attach

Attach to a session target.

```bash
terminal attach [OPTIONS] [NAME]
```

| Option | Short | Description |
|--------|-------|-------------|
| `NAME` | - | Session name to attach to; omit for interactive selection |
| `--new-session` | `-n` | Create a new session instead of attaching |
| `--kill-all` | `-k` | Kill all existing sessions before creating a new one |
| `--first` | `-f` | Attach to the first available tmux, TUIOS, or Zellij session without prompting |
| `--window` | `-w` | Choose a window/tab or pane target instead of only sessions |
| `--backend` | `-b` | `tmux`/`t`, `herdr`/`h`, `tuios`/`u`, `aoe`/`e`, or `zellij`/`z`; omitted, uses `default_session_multiplexer` from the StackOps config, else `tmux` |

`NAME` cannot be combined with `--new-session`, `--kill-all`, `--window`, or `--first`, and `--first` cannot be combined with the other three.

Example:

```bash
# Attach to the first session without opening the chooser
terminal attach --first

# Choose a pane or tab interactively
terminal attach --window

# Attach to a Herdr session
terminal attach --backend herdr

# Attach to an Agent of Empires session
terminal attach --backend aoe
```

## kill

Kill a session target.

```bash
terminal kill [OPTIONS] [NAME]
```

| Option | Short | Description |
|--------|-------|-------------|
| `NAME` | - | Session(s) to kill: comma-separated names and/or `*` and `?` selectors, e.g. `api,web*`; omit for interactive selection |
| `--kill-all` | `-k` | Kill all sessions; with `--idle`, inspect all sessions for idle panes/windows |
| `--idle` | `-i` | Kill idle-shell panes/windows in `NAME` or a chosen session; combine with `--kill-all` to inspect all sessions |
| `--window` | `-w` | Include sessions, windows/tabs, and panes in the chooser; only when `NAME` is omitted |
| `--delete` | `-D` | Delete stopped Herdr or Zellij session records instead of killing running sessions |
| `--backend` | `-b` | `tmux`/`t`, `herdr`/`h`, `tuios`/`u`, `aoe`/`e`, or `zellij`/`z`; omitted, uses `default_session_multiplexer` from the StackOps config, else `tmux` |
| `--window-id`, `--tab-id` | `-W` | Close one exact window/tab by the ID shown by `summary --json --tabs`; `NAME` optionally scopes the session/workspace |
| `--pane-id` | `-p` | Close one exact pane by the ID shown by `summary --json --tabs`; `NAME` optionally scopes the session/workspace |

Herdr named sessions are stopped and deleted; Herdr's reserved default session can only be stopped. `--window-id` and `--pane-id` are mutually exclusive and cannot be combined with `--kill-all`, `--idle`, `--window`, or `--delete`.

Example:

```bash
# Choose an exact pane or tab to kill
terminal kill --window

# Kill several sessions by name and wildcard
terminal kill "api,web*"

# Kill idle-shell panes/windows across every tmux session
terminal kill --idle --kill-all

# Stop an Agent of Empires session
terminal kill --backend aoe
```

## export

Export running tmux, TUIOS, or Zellij sessions or Herdr workspaces into a layout file that `terminal run` can launch.

```bash
terminal export [OPTIONS]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--sessions` | `-s` | Comma-separated backend session names or Herdr workspace labels/IDs; omit or pass an empty value for interactive multi-select |
| `--all` | `-a` | Export all running backend sessions/workspaces without prompting |
| `--output` | `-o` | Output layout file; defaults to `./tmux_export_layout.yaml` |
| `--overwrite` | `-w` | Replace the output file if it already exists |
| `--merge` | `-m` | Merge exported sessions into an existing layout file by `layoutName` |
| `--backend` | `-b` | `tmux`/`t`, `herdr`/`h`, `tuios`/`u`, or `zellij`/`z`; asked with `--interactive`; omitted, uses `default_session_multiplexer` from the StackOps config, else `tmux`; a configured `aoe` is rejected |
| `--command-source` | `-c` | `shell`, `current-command`, or `start-command`; defaults to `shell`, or is asked with `--interactive`. Herdr supports only `shell`; TUIOS supports `shell` and `current-command` |
| `--interactive` | `-i` | Ask for the backend (showing its running sessions), the command source, and how to write an existing output file, unless given as flags |

Examples:

```bash
# Choose tmux sessions interactively, with previews
terminal export

# Export specific sessions into a runnable layout file
terminal export --sessions "dev,build" --output exported_layout.yaml

# Export every running tmux session, then replay it with run
terminal export --all --output exported_layout.yaml --overwrite
terminal run --custom-path exported_layout.yaml

# Export Herdr workspaces, then replay them with run
terminal export --backend herdr --all --output exported_layout.yaml --overwrite
terminal run --custom-path exported_layout.yaml --backend herdr
```

## trace

Trace tmux, TUIOS, Zellij, or Agent of Empires sessions, or Herdr workspaces, until every observable target matches a strict stop criterion.

```bash
terminal trace [OPTIONS] [SESSION_NAMES]
```

| Option | Short | Description |
|--------|-------|-------------|
| `SESSION_NAMES` | - | Comma-separated tmux, TUIOS, Zellij, or AoE sessions, or Herdr workspaces, to trace; supports `*` and `?` selectors; omit when using `--interactive` |
| `--backend` | `-b` | Backend to trace; `tmux`/`t`, `herdr`/`h`, `tuios`/`u`, `aoe`/`e`, or `zellij`/`z`; omitted, uses `default_session_multiplexer` from the StackOps config, else `tmux` |
| `--interactive` | `-i` | Choose an existing backend session/workspace interactively |
| `--poll-interval` | `-p` | Polling interval in seconds; defaults to `10.0` |
| `--until` | `-u` | `idle-shell` (default), `all-exited`, `exit-code`, or `session-missing` |
| `--exit-code` | `-c` | Required exit code when `--until exit-code` is selected |
| `--kill` | `-k` | Kill finalized panes, windows, and sessions as they satisfy the selected criterion |
| `--json` | `-j` | Stream snapshots and completion events as newline-delimited JSON; cannot be combined with `--interactive` |

With `--backend herdr`, tracing supports `idle-shell` and `session-missing`. Herdr's API does not expose process exit status, so `all-exited` and `exit-code` are rejected. Herdr agent states `idle` and `done` both count as ready for input; `done` indicates an unseen completion. With `--backend aoe`, `exit-code` is rejected because AoE does not expose process exit codes.

Examples:

```bash
# Choose an existing session interactively
terminal trace --interactive

# Wait until every pane returns to an idle shell
terminal trace build-session

# Wait until every pane has exited
terminal trace build-session --poll-interval 5 --until all-exited

# Trace several sessions and kill each target as it finishes
terminal trace "build-*,tests" --kill

# Trace a Herdr workspace by label
terminal trace build-workspace --backend herdr

# Trace an Agent of Empires session by title
terminal trace build-session --backend aoe

# Require successful exit codes from every pane
terminal trace build-session --until exit-code --exit-code 0
```

## summary

Print running terminal session summaries, or show details for one chosen session.

```bash
terminal summary [OPTIONS]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--backend` | `-b` | Backend to summarize; `tmux`/`t`, `herdr`/`h`, `tuios`/`u`, `aoe`/`e`, or `zellij`/`z`; omitted, uses `default_session_multiplexer` from the StackOps config, else `tmux` |
| `--session` | `-s` | Show details for one backend session or workspace by name |
| `--choose-session` | `-c` | Choose one backend session or workspace interactively and show details |
| `--tabs` | `-t` | Include tab/window and pane details for every session (tmux, Herdr, TUIOS, and Zellij) |
| `--json` | `-j` | Print structured session summaries as JSON without a picker; `--tabs` adds pane details; cannot be combined with `--choose-session` |

Examples:

```bash
# Show the aggregate tmux session table
terminal summary

# Show windows and panes for one named session
terminal summary --session build-session

# Choose a session interactively, with preview, then show details
terminal summary --choose-session

# Show Herdr workspaces
terminal summary --backend herdr

# Show Agent of Empires sessions
terminal summary --backend aoe

# Print every session with its tab and pane details as JSON
terminal summary --json --tabs
```

## run-function

Launch a function immediately in multiple tmux processes. Each process receives its index and the total process count.

```bash
terminal run-function [OPTIONS]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--num-process` | `-n` | Required number of parallel processes |
| `--path` | `-p` | Script file or directory to search; defaults to `.` |
| `--function` | `-f` | Function name to run; omit to choose interactively |

Each generated tab runs:

```bash
uv run python -m fire <file> <function> --idx=<n> --idx_max=<num_process>
```

Example:

```bash
terminal run-function --num-process 4 --path ./my_script.py --function process_data
```

## balance-load

Adjust a layout file to limit tabs per layout or total layout weight.

```bash
terminal balance-load LAYOUT_PATH [OPTIONS]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--max-threshold` | `-m` | Required threshold value |
| `--threshold-type` | `-t` | `number`/`n` (default) or `weight`/`w` |
| `--breaking-method` | `-b` | `more-layouts`/`ml` (default) or `combine-tabs`/`ct` |
| `--output` | `-o` | Output path for the rewritten file |

If `--output` is omitted, StackOps writes `<stem>_adjusted_<max>_<threshold>_<method>.yaml` beside the source file, where `<threshold>` is the `--threshold-type` value as typed and `<method>` is `moreLayouts` or `combineTabs` (for example `layout_adjusted_4_number_moreLayouts.yaml`).

## create-template

Create a starter layout file in the current directory.

```bash
terminal create-template [NAME] [OPTIONS]
```

| Option | Short | Description |
|--------|-------|-------------|
| `NAME` | - | Optional output filename stem; defaults to `layout.yaml` |
| `--num-tabs` | `-t` | Number of tabs to include; defaults to `3` |

Current behavior:

- The template uses the current directory to build `startDir`.
- The default tab command is `bash` on non-Windows systems and `powershell` on Windows.
- Existing files are not overwritten.

## list

List saved layouts and their source files. Add `--stats` / `-S` for aggregate counts, `--tabs` / `-t` for tab and pane details, and `--json` / `-j` to print the same data as JSON. `--source` / `-s` accepts `workspace/w`, `user/u`, or `all/a`, defaulting to `all`.

```bash
terminal list --stats
terminal list --source workspace --tabs --stats
terminal list --custom-path layout.yaml --tabs --stats
terminal list --json --tabs
```

Omitting `--custom-path` lists layouts from the selected source files. The default `all` includes available user and workspace files; when no workspace root can be resolved, it includes only the user file. Explicit `--source workspace` requires a workspace root as described above. `--custom-path` / `-p` overrides the source selection. Statistics include layout, tab and pane totals, average tabs per layout, and the largest and smallest layouts. Layouts, tabs, and panes with `enabled: false` are marked `(off)`.

## edit, path, init, validate

`edit` opens a layout file, creates it if missing, and validates it after saving. Omit `--custom-path` to choose a configuration interactively, or pass `--source workspace` (alias `w`) or `--source user` (alias `u`). `--editor` / `-e` accepts `hx` (the default), `nano`, or `code`; `--install-lsp` / `-l` installs the required language server if it is missing (Helix only).

`path` prints file and schema paths as JSON; with no options it shows the user path and, when a workspace root can be resolved, the workspace paths. `init` creates a missing file and schema. `validate` checks a file without opening an editor. Both `init` and `validate` require `--custom-path`, `--source workspace` (alias `w`), or `--source user` (alias `u`). For all four commands, `--custom-path` / `-p` overrides `--source`.

```bash
terminal edit --source workspace
terminal path
terminal init --source workspace
terminal path --source user
terminal validate --custom-path layout.yaml
```

## Layout File Format

Layout files are YAML and must use the `.yaml` suffix; StackOps rejects any other suffix. They use the `LayoutsFile` wrapper, and `version` must be the quoted string `"0.2"`. The important keys are `layouts`, `layoutName`, `layoutTabs`, `tabName`, `panes`, `paneName`, `startDir`, and `command`. A layout is a session, a tab holds one or more panes, and each pane runs one command.

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/thisismygitrepo/stackops/refs/heads/main/src/stackops/utils/schemas/layouts/layout.schema.json

version: "0.2"
layouts:
  - layoutName: Development
    layoutTabs:
      - tabName: editor
        panes:
          - paneName: helix
            startDir: ~/projects/myapp
            command: hx .
      - tabName: server
        arrangement: columns
        panes:
          - paneName: http
            startDir: ~/projects/myapp
            command: python -m http.server 8000
          - paneName: logs
            startDir: ~/projects/myapp/logs
            command: tail -f server.log
```

`arrangement` is optional and only matters for tabs with more than one pane: `columns` places panes side by side, `rows` stacks them, and `grid` (the default) balances them. `paneName` must be unique within its tab. `tabWeight` stays on the tab.

A layout, tab, or pane can carry `enabled: false` to stay in the file without launching; a tab whose panes are all off is left out too. A layout or tab that is off still launches when it is named with `--choose-layouts` / `--choose-tabs` or picked from the list; its own tabs and panes that are off stay off.

Each backend uses its own names for the same levels:

| Layout level | tmux | Herdr | TUIOS | Zellij | AoE |
| --- | --- | --- | --- | --- | --- |
| Layout | session | workspace | session | session | group |
| Tab | window | tab | workspace | tab | agent session |
| Pane | pane | pane | window | pane | one pane per tab only |

TUIOS ignores `arrangement` because its tiler arranges the windows of a workspace. AoE starts one agent session per tab and rejects tabs with more than one pane. `balance-load` with `combine-tabs` joins the commands of several tabs into one, so the tabs it merges must be single-pane; `more-layouts` moves whole tabs and accepts any.

Any file with a different `version` is rejected, including older `0.1` files that put `startDir`/`command` directly on the tab. Long commands can use a `>-` folded block, which joins its lines with single spaces. Quote values YAML would otherwise retype: an unquoted `0.2` is a number and a bare `~` is null.

## Backend Notes

- `trace` supports tmux, TUIOS, Zellij, and Agent of Empires sessions and Herdr workspaces.
- `run-all` supports tmux, TUIOS, and Zellij; `export` supports tmux, Herdr, TUIOS, and Zellij.
- With Herdr or AoE, `run` rejects `--monitor`, `--parallel-layouts`, `--kill-upon-completion`, `--attach`, and any `--exit` other than `back-to-shell`; AoE also rejects any `--on-conflict` other than `error`.
- Herdr, AoE, and Zellij require macOS or Linux.
