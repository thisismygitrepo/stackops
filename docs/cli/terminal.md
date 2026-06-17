# terminal


## Usage

```bash
terminal [OPTIONS] COMMAND [ARGS]...
```

## Commands Overview

| Command | Description |
|---------|-------------|
| `run` | Launch selected layouts from a layout file or generated test layout |
| `run-all` | Dynamically work through every tab in one merged run |
| `run-aoe` | Launch selected layout tabs through agent-of-empires |
| `attach` | Attach to an existing session, window/tab, or pane |
| `kill` | Kill a session target |
| `trace` | Trace a tmux session until a strict stop condition is met |
| `summary` | Print running session summaries or one session's details |
| `create-from-function` | Build and launch a multiprocess layout from a script function |
| `balance-load` | Re-split a layout file by tab count or weight |
| `create-template` | Create a starter layout file in the current directory |
| `summarize` | Print layout counts and per-layout tab totals |

Hidden one-letter aliases exist, but this page uses canonical command names.

## Common Layout Source Rules

- `run`, `run-all`, and `run-aoe` default to `~/dotfiles/stackops/layouts.json` when `--layouts-file` is omitted.
- `run` and `run-all` also support `--test-layout`, which generates a built-in finite layout set for experimentation and cannot be combined with `--layouts-file`.
- `--choose-layouts ""` opens interactive layout selection.
- `--choose-tabs ""` opens interactive tab selection.
- Explicit tab selectors can be either `tabName` or `layoutName::tabName`.

## run

Launch selected layouts from a layout configuration file.

```bash
terminal run [OPTIONS]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--layouts-file` | `-f` | Override the default layout file |
| `--test-layout` | `-L` | Use the generated mock layout instead of reading a file |
| `--choose-layouts` | `-l` | Comma-separated layout names, or `""` for interactive selection |
| `--choose-tabs` | `-t` | Comma-separated tab names, or `""` for interactive selection across all layouts |
| `--sleep-inbetween` | `-S` | Delay between launching layouts |
| `--parallel-layouts` | `-p` | Maximum number of layouts to launch per monitored batch |
| `--max-tabs-per-layout` | `-T` | Sanity limit for tabs inside a single selected layout |
| `--max-parallel-layouts` | `-P` | Sanity limit for total parallel layouts |
| `--backend` | `-b` | `tmux`/`t`, `herdr`/`h`, or `auto`/`a` |
| `--on-conflict` | `-c` | `error`, `restart`, `rename`, `mergeOverwrite`, or `mergeSkip` |
| `--exit` | `-e` | `backToShell`, `terminate`, or `killWindow` after each command exits |
| `--monitor` | `-m` | Monitor launched sessions for completion |
| `--kill-upon-completion` | `-k` | Kill sessions after monitored completion |
| `--substitute-home` | `-H` | Expand `~` and `$HOME` inside the selected layout tabs |

Examples:

```bash
# Run the default ~/dotfiles/stackops/layouts.json
terminal run

# Run only selected layouts from an explicit file
terminal run --layouts-file layouts.json --choose-layouts "dev,build"

# Run a generated test layout
terminal run --test-layout --parallel-layouts 2 --monitor

# Select tabs by name or layout-qualified name
terminal run --layouts-file layouts.json --choose-tabs "server,build::tests"

# Restart matching sessions before relaunching
terminal run --layouts-file layouts.json --on-conflict restart

# Launch selected layouts through Herdr
terminal run --layouts-file layouts.json --backend herdr
```

## run-all

Merge every tab from every layout into one paced run.

```bash
terminal run-all [OPTIONS]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--layouts-file` | `-f` | Override the default layout file |
| `--test-layout` | `-T` | Use the generated mock layout instead of reading a file |
| `--max-parallel-tabs` | `-t` | Required cap for concurrently active tabs |
| `--poll-seconds` | `-p` | Polling interval for finished-tab detection |
| `--kill-finished-tabs` | `-k` | Close each tab as soon as its command finishes |
| `--on-conflict` | `-c` | `error`, `restart`, or `rename`; merge policies are rejected |
| `--substitute-home` | `-H` | Expand `~` and `$HOME` inside selected tabs |

Examples:

```bash
# Keep at most eight tabs active while working through the whole file
terminal run-all --layouts-file layouts.json --max-parallel-tabs 8

# Use the generated test layout and close finished tabs as work drains
terminal run-all --test-layout --max-parallel-tabs 6 --kill-finished-tabs
```

## run-aoe

Launch selected layout tabs through [agent-of-empires](https://github.com/njbrake/agent-of-empires).

Mapping:

- `layoutName` -> AoE group
- `tabName` -> AoE title
- `startDir` -> AoE target path
- `command` -> initial prompt by default

```bash
terminal run-aoe [OPTIONS]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--layouts-file` | `-f` | Override the default layout file |
| `--choose-layouts` | `-c` | Comma-separated layout names, or `""` for interactive selection |
| `--choose-tabs` | `-t` | Comma-separated tab names, or `""` for interactive selection |
| `--sleep-inbetween` | `-S` | Delay between AoE launches |
| `--max-tabs-per-layout` | `-T` | Sanity limit for selected layouts |
| `--agent` | `-a` | Agent/tool name; defaults to `codex` |
| `--model` | `-m` | Model forwarded to the launched CLI when supported |
| `--provider` | `-p` | Provider forwarded to the launched CLI when supported |
| `--sandbox` | `-s` | Forward `--sandbox <value>` when supported |
| `--yolo` | `-y` | Enable YOLO mode when supported |
| `--cmd` | `-C` | Override the launched agent binary/command |
| `--args` | `-A` | Repeatable extra argument forwarded to the launched CLI |
| `--env` | `-e` | Repeatable `KEY=VALUE` pair forwarded to AoE when supported |
| `--force` | `-F` | Forward force/overwrite when supported |
| `--dry-run` | `-d` | Print generated `aoe add` commands without executing them |
| `--aoe-bin` | `-b` | AoE executable to invoke |
| `--tab-command-mode` | `-M` | `prompt`, `cmd`, or `ignore` for each tab's `command` field |
| `--substitute-home` | `-H` | Expand `~` and `$HOME` inside selected tabs |
| `--no-launch` | `-n` | Create each AoE session without launching it immediately |

Examples:

```bash
# Treat each tab command as the initial prompt
terminal run-aoe --layouts-file layout.json --model <model-name> --sandbox workspace-write --yolo

# Use each tab command as an agent-command override instead
terminal run-aoe --layouts-file layout.json --tab-command-mode cmd

# Preview generated aoe commands without executing them
terminal run-aoe --layouts-file layout.json --dry-run
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
| `--window` | `-w` | Choose a window/tab or pane target instead of only sessions |
| `--backend` | `-b` | `tmux`, `herdr`, `aoe`, or `auto` |

Example:

```bash
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
| `--all` | `-a` | Kill all sessions; with `--idle`, inspect all sessions for idle panes/windows |
| `--idle` | `-i` | Kill idle-shell panes/windows in `NAME` or a chosen session; combine with `--all` to inspect all sessions |
| `--window` | `-w` | Include sessions, windows/tabs, and panes in the chooser |
| `--backend` | `-b` | `tmux`, `herdr`, `aoe`, or `auto` |

Example:

```bash
# Choose an exact pane or tab to kill
terminal kill --window

# Kill idle-shell panes/windows across every tmux session
terminal kill --idle --all

# Stop an Agent of Empires session
terminal kill --backend aoe
```

## trace

Trace a tmux session or Herdr workspace until every observable target matches a strict stop criterion.

```bash
terminal trace [SESSION_NAME] [OPTIONS]
```

| Option | Short | Description |
|--------|-------|-------------|
| `SESSION_NAME` | - | tmux session name or Herdr workspace label/id to trace; omit when using `--interactive` |
| `--backend` | `-b` | Backend to trace; `tmux`/`t` or `herdr`/`h` |
| `--interactive` | `-i` | Choose an existing backend session/workspace interactively |
| `--every` | `-e` | Polling interval in seconds |
| `--until` | `-u` | `idle-shell`, `all-exited`, `exit-code`, or `session-missing` |
| `--exit-code` | `-c` | Required exit code when `--until exit-code` is selected |

Examples:

```bash
# Choose an existing session interactively
terminal trace --interactive

# Wait until every pane returns to an idle shell
terminal trace build-session

# Wait until every pane has exited
terminal trace build-session --every 5 --until all-exited

# Trace a Herdr workspace by label
terminal trace build-workspace --backend herdr

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
| `--backend` | `-b` | Backend to summarize; `tmux`/`t`, `herdr`/`h`, or `auto`/`a` |
| `--session` | `-s` | Show details for one tmux session or Herdr workspace by name |
| `--choose-session` | `-c` | Choose one tmux session or Herdr workspace interactively and show details |

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
```

## create-from-function


```bash
terminal create-from-function [OPTIONS]
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
terminal create-from-function --num-process 4 --path ./my_script.py --function process_data
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
| `--breaking-method` | `-b` | `moreLayouts`/`ml` or `combineTabs`/`ct` |
| `--output-path` | `-o` | Output path for the rewritten file |

If `--output-path` is omitted, StackOps writes `<stem>_adjusted_<max>_<threshold>_<method>.json` beside the source file.

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

## summarize

Print layout counts and per-layout tab totals.

```bash
terminal summarize LAYOUT_PATH [OPTIONS]
```

Current behavior:

- Prints the file path, version, total layout count, total tab count, average tabs per layout, and min/max tab counts.
- Accepts the current wrapped layout-file shape with a top-level `layouts` array.
- Use `--backend herdr` to summarize the same layout file with Herdr workspace terminology.

## Layout File Format

Current layout files use the `LayoutsFile` wrapper. The important keys are `layouts`, `layoutName`, `layoutTabs`, `tabName`, `startDir`, and `command`.

```json
{
  "$schema": "https://bit.ly/cfglayout",
  "version": "0.1",
  "layouts": [
    {
      "layoutName": "Development",
      "layoutTabs": [
        {
          "tabName": "editor",
          "startDir": "~/projects/myapp",
          "command": "hx ."
        },
        {
          "tabName": "server",
          "startDir": "~/projects/myapp",
          "command": "python -m http.server 8000"
        }
      ]
    }
  ]
}
```

Older examples that use `tabs` or `cwd` are stale. The current schema uses `layoutTabs` and `startDir`.

## Backend Notes

- `trace` supports tmux sessions and Herdr workspaces.
