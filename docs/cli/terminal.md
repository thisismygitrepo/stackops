# terminal

The Herdr backend supports only the latest Herdr CLI and server. See the [Herdr CLI reference](https://herdr.dev/docs/cli-reference/) for current command syntax.

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
| `kill` | Kill a session target |
| `export` | Export running tmux sessions into a layout file |
| `trace` | Trace a tmux session until a strict stop condition is met |
| `summary` | Print running session summaries or one session's details |
| `run-function` | Immediately launch a script function in multiple tmux processes |
| `balance-load` | Re-split a layout file by tab count or weight |
| `create-template` | Create a starter layout file in the current directory |

Hidden one-letter aliases exist, but this page uses canonical command names.

## Common Layout Source Rules

- `run`, `run-all`, and `list` accept `--source` / `-s`: `workspace/w`, `user/u`, or `all/a`, defaulting to `all`.
- The workspace root is the enclosing Git repository root, including when called from a subdirectory, or the current directory when it contains at least two immediate child Git repositories. Outside these locations, the workspace source is unavailable.
- Without `--custom-path` or `--test-layout`, `--source all` combines named layouts from the user file at `~/dotfiles/stackops/config/layouts.json` and the workspace file at `<workspace-root>/.stackops/config/layout.json`, including each file that exists. When the workspace source is unavailable, `all` includes only the user source; explicit `--source workspace` fails. `run` and `run-all` open a picker for the selected source files; cancelling it aborts the command.
- The default picker labels entries `user:name` or `workspace:name` and previews their source file paths. Layout and session names remain unchanged.
- `--custom-path` / `-p` overrides `--source` and loads layouts only from the supplied file, including outside a workspace.
- For `run`, an explicit `--choose-layouts` or `--choose-tabs` selector uses that selection without opening an additional layout picker.
- `run` and `run-all` also support `--test-layout`, which generates a built-in finite layout set for experimentation and cannot be combined with `--custom-path`.
- `--choose-layouts ""` opens interactive layout selection.
- Named layout selectors accept an unambiguous name or `user:name` / `workspace:name`. A name shared by both sources requires the qualified form.
- `--choose-tabs ""` opens interactive tab selection.
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
| `--choose-layouts` | `-l` | Comma-separated layout names, or `""` for interactive selection |
| `--choose-tabs` | `-t` | Comma-separated tab names, or `""` for interactive selection across all layouts |
| `--launch-delay` | `-S` | Delay in seconds between launching layouts |
| `--parallel-layouts` | `-j` | Maximum number of layouts to launch per monitored batch |
| `--max-tabs-per-layout` | `-T` | Sanity limit for tabs inside a single selected layout |
| `--max-parallel-layouts` | `-P` | Sanity limit for total parallel layouts |
| `--backend` | `-b` | `tmux`/`t`, `herdr`/`h`, `tuios`/`u`, `aoe`/`e`, or `auto`/`a` |
| `--on-conflict` | `-c` | `error`, `restart`, `rename`, `merge-overwrite`, or `merge-skip` |
| `--exit` | `-e` | `back-to-shell`, `terminate`, or `kill-window` after each command exits |
| `--monitor` | `-m` | Monitor launched sessions for completion |
| `--kill-upon-completion` | `-k` | Kill sessions after monitored completion |
| `--substitute-home` | `-H` | Expand `~` and `$HOME` inside the selected layout tabs |

Examples:

```bash
# Choose layouts from the user file and the workspace's .stackops/config/layout.json when present
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
terminal run --custom-path layouts.json --choose-layouts "dev,build"

# Run a generated test layout
terminal run --test-layout --parallel-layouts 2 --monitor

# Select tabs by name or layout-qualified name
terminal run --custom-path layouts.json --choose-tabs "server,build::tests"

# Restart matching sessions before relaunching
terminal run --custom-path layouts.json --on-conflict restart

# Launch selected layouts through Herdr
terminal run --custom-path layouts.json --backend herdr

# Launch selected layout tabs through Agent of Empires
terminal run --custom-path layout.json --backend aoe
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
| `--poll-interval` | `-i` | Polling interval for finished-tab detection |
| `--backend` | `-b` | `tmux`/`t`, `tuios`/`u`, or `auto`/`a` |
| `--kill-finished-tabs` | `-k` | Close each tab as soon as its command finishes |
| `--on-conflict` | `-c` | `error`, `restart`, or `rename`; merge policies are rejected |
| `--substitute-home` | `-H` | Expand `~` and `$HOME` inside selected tabs |

Examples:

```bash
# Choose layouts from the combined default files and keep at most eight tabs active
terminal run-all --max-parallel-tabs 8

# Choose only user layouts and keep at most eight tabs active
terminal run-all --source user --max-parallel-tabs 8

# Keep at most eight tabs active while working through the whole file
terminal run-all --custom-path layouts.json --max-parallel-tabs 8

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
| `--first` | `-f` | Attach to the first available tmux session without prompting |
| `--window` | `-w` | Choose a window/tab or pane target instead of only sessions |
| `--backend` | `-b` | `tmux`/`t`, `herdr`/`h`, `tuios`/`u`, `aoe`/`e`, or `auto`/`a` |

Example:

```bash
# Attach to the first tmux session without opening the chooser
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
| `NAME` | - | Session name to kill; omit for interactive selection |
| `--kill-all` | `-k` | Kill all sessions; with `--idle`, inspect all sessions for idle panes/windows |
| `--idle` | `-i` | Kill idle-shell panes/windows in `NAME` or a chosen session; combine with `--kill-all` to inspect all sessions |
| `--window` | `-w` | Include sessions, windows/tabs, and panes in the chooser |
| `--delete` | `-D` | Delete stopped Herdr session records instead of killing running sessions |
| `--backend` | `-b` | `tmux`/`t`, `herdr`/`h`, `tuios`/`u`, `aoe`/`e`, or `auto`/`a` |

Example:

```bash
# Choose an exact pane or tab to kill
terminal kill --window

# Kill idle-shell panes/windows across every tmux session
terminal kill --idle --kill-all

# Stop an Agent of Empires session
terminal kill --backend aoe
```

## export

Export running tmux sessions or Herdr workspaces into a layout file that `terminal run` can launch.

```bash
terminal export [OPTIONS]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--sessions` | `-s` | Comma-separated tmux session names or Herdr workspace labels/IDs; omit for interactive multi-select |
| `--all` | `-a` | Export all running backend sessions/workspaces without prompting |
| `--output` | `-o` | Output layout file; defaults to `./tmux_export_layout.json` |
| `--overwrite` | `-w` | Replace the output file if it already exists |
| `--merge` | `-m` | Merge exported sessions into an existing layout file by `layoutName` |
| `--backend` | `-b` | `tmux`/`t`, `herdr`/`h`, or `tuios`/`u`; defaults to `tmux` |
| `--command-source` | `-c` | `shell`, `current-command`, or `start-command`; defaults to `shell` |

Examples:

```bash
# Choose tmux sessions interactively, with previews
terminal export

# Export specific sessions into a runnable layout file
terminal export --sessions "dev,build" --output exported_layout.json

# Export every running tmux session, then replay it with run
terminal export --all --output exported_layout.json --overwrite
terminal run --custom-path exported_layout.json

# Export Herdr workspaces, then replay them with run
terminal export --backend herdr --all --output exported_layout.json --overwrite
terminal run --custom-path exported_layout.json --backend herdr
```

## trace

Trace a tmux session, Herdr workspace, or Agent of Empires session until every observable target matches a strict stop criterion.

```bash
terminal trace [SESSION_NAME] [OPTIONS]
```

| Option | Short | Description |
|--------|-------|-------------|
| `SESSION_NAME` | - | tmux session name, Herdr workspace label/id, or AoE session title/id to trace; omit when using `--interactive` |
| `--backend` | `-b` | Backend to trace; `tmux`/`t`, `herdr`/`h`, `tuios`/`u`, or `aoe`/`e` |
| `--interactive` | `-i` | Choose an existing backend session/workspace interactively |
| `--poll-interval` | `-p` | Polling interval in seconds |
| `--until` | `-u` | `idle-shell`, `all-exited`, `exit-code`, or `session-missing` |
| `--exit-code` | `-c` | Required exit code when `--until exit-code` is selected |

With `--backend herdr`, tracing supports `idle-shell` and `session-missing`. Herdr's API does not expose process exit status, so `all-exited` and `exit-code` are rejected. Herdr agent states `idle` and `done` both count as ready for input; `done` indicates an unseen completion.

Examples:

```bash
# Choose an existing session interactively
terminal trace --interactive

# Wait until every pane returns to an idle shell
terminal trace build-session

# Wait until every pane has exited
terminal trace build-session --poll-interval 5 --until all-exited

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
| `--backend` | `-b` | Backend to summarize; `tmux`/`t`, `herdr`/`h`, `tuios`/`u`, `aoe`/`e`, or `auto`/`a` |
| `--session` | `-s` | Show details for one tmux session, Herdr workspace, or AoE session by name |
| `--choose-session` | `-c` | Choose one tmux session, Herdr workspace, or AoE session interactively and show details |

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
```

## run-function

Launch a function immediately in multiple tmux processes. Each process receives its index and the total process count.

```bash
terminal run-function [OPTIONS]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--num-process` | `-n` | Required number of parallel processes |
| `--path` | `-p` | Script file or directory to search |
| `--function` | `-f` | Function name to run |

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
| `--threshold-type` | `-t` | `number`/`n` or `weight`/`w` |
| `--breaking-method` | `-b` | `more-layouts`/`ml` or `combine-tabs`/`ct` |
| `--output` | `-o` | Output path for the rewritten file |

If `--output` is omitted, StackOps writes `<stem>_adjusted_<max>_<threshold>_<method>.json` beside the source file.

## create-template

Create a starter layout file in the current directory.

```bash
terminal create-template [NAME] [OPTIONS]
```

| Option | Short | Description |
|--------|-------|-------------|
| `NAME` | - | Optional output filename stem; defaults to `layout.json` |
| `--num-tabs` | `-t` | Number of tabs to include |

Current behavior:

- The template uses the current directory to build `startDir`.
- The default tab command is `bash` on non-Windows systems and `powershell` on Windows.
- Existing files are not overwritten.

## list

List saved layouts and their source files. Add `--stats` / `-S` for aggregate counts and `--tabs` / `-t` for tab details. `--source` / `-s` accepts `workspace/w`, `user/u`, or `all/a`, defaulting to `all`.

```bash
terminal list --stats
terminal list --source workspace --tabs --stats
terminal list --custom-path layout.json --tabs --stats
```

Omitting `--custom-path` lists layouts from the selected source files. The default `all` includes available user and workspace files; when no workspace root can be resolved, it includes only the user file. Explicit `--source workspace` requires a workspace root as described above. `--custom-path` / `-p` overrides the source selection. Statistics include layout, tab and pane totals, average tabs per layout, and the largest and smallest layouts.

## edit, path, init, validate

`edit` opens a layout file, creates it if missing, and validates it after saving. Omit `--custom-path` to choose a configuration interactively, or pass `--source workspace` (alias `w`) or `--source user` (alias `u`). `--editor` accepts `hx`, `nano`, or `code`.

`path` prints file and schema paths as JSON; with no options it shows the user path and, when a workspace root can be resolved, the workspace path. `init` creates a missing file and schema. `validate` checks a file without opening an editor. Both `init` and `validate` require `--custom-path`, `--source workspace` (alias `w`), or `--source user` (alias `u`). For all four commands, `--custom-path` / `-p` overrides `--source`.

```bash
terminal edit --source workspace
terminal path
terminal init --source workspace
terminal path --source user
terminal validate --custom-path layout.json
```

## Layout File Format

Current layout files use the `LayoutsFile` wrapper. The important keys are `layouts`, `layoutName`, `layoutTabs`, `tabName`, `panes`, `paneName`, `startDir`, and `command`. A layout is a session, a tab holds one or more panes, and each pane runs one command.

```json
{
  "$schema": "https://raw.githubusercontent.com/thisismygitrepo/stackops/refs/heads/main/src/stackops/utils/schemas/layouts/layout.schema.json",
  "version": "0.1",
  "layouts": [
    {
      "layoutName": "Development",
      "layoutTabs": [
        {
          "tabName": "editor",
          "panes": [
            {
              "paneName": "helix",
              "startDir": "~/projects/myapp",
              "command": "hx ."
            }
          ]
        },
        {
          "tabName": "server",
          "arrangement": "columns",
          "panes": [
            {
              "paneName": "http",
              "startDir": "~/projects/myapp",
              "command": "python -m http.server 8000"
            },
            {
              "paneName": "logs",
              "startDir": "~/projects/myapp/logs",
              "command": "tail -f server.log"
            }
          ]
        }
      ]
    }
  ]
}
```

`arrangement` is optional and only matters for tabs with more than one pane: `columns` places panes side by side, `rows` stacks them, and `grid` (the default) balances them. `paneName` must be unique within its tab. `tabWeight` stays on the tab.

Each backend uses its own names for the same levels:

| Layout level | tmux | Herdr | TUIOS | AoE |
| --- | --- | --- | --- | --- |
| Layout | session | workspace | session | group |
| Tab | window | tab | workspace | agent session |
| Pane | pane | pane | window | one pane per tab only |

TUIOS ignores `arrangement` because its tiler arranges the windows of a workspace. AoE starts one agent session per tab and rejects tabs with more than one pane. `balance-load` with `combine-tabs` joins the commands of several tabs into one, so it requires single-pane tabs; `more-layouts` moves whole tabs and accepts any.

Older examples that use `tabs`, `cwd`, or a `startDir`/`command` directly on the tab are stale. The current schema uses `layoutTabs` and `panes`.

## Backend Notes

- `trace` supports tmux sessions, Herdr workspaces, and Agent of Empires sessions.
