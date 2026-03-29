# sessions

Terminal session and layout management for `tmux`, `zellij`, and Windows Terminal.

---

## Usage

```bash
sessions [OPTIONS] COMMAND [ARGS]...
```

---

## Commands overview

| Command | Description |
|---------|-------------|
| `run` | Launch terminal sessions from a layout file |
| `run-all` | Dynamically work through every tab in a layout file |
| `run-aoe` | Launch selected layout tabs as agent-of-empires sessions |
| `attach` | Attach to a session target |
| `kill` | Kill a session target |
| `trace` | Trace a tmux session until it reaches a strict stop condition |
| `create-from-function` | Create a layout from a function |
| `balance-load` | Split or rebalance layouts |
| `create-template` | Create a layout template file |
| `summarize` | Summarize a layout file |

The CLI help also exposes one-letter aliases, but this page uses canonical command names.

---

## run

Launch selected layout sessions from a layout file. Current `run` usage is option-based: pass the file with `--layouts-file` instead of as a positional argument.

```bash
sessions run [OPTIONS]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--layouts-file` | `-f` | Path to the layout file |
| `--choose-layouts` | `-c` | Comma-separated layout names; pass `""` for interactive layout selection |
| `--choose-tabs` | `-t` | Comma-separated tab names; pass `""` for interactive tab selection |
| `--sleep-inbetween` | `-S` | Delay in seconds between launching layouts |
| `--parallel-layouts` | `-p` | Maximum number of layouts to launch per monitored batch |
| `--max-tabs-per-layout` | `-T` | Sanity-check cap for tabs inside a single layout |
| `--max-parallel-layouts` | `-P` | Sanity-check cap for the number of parallel layouts |
| `--backend` | `-b` | Backend to use: `tmux`, `zellij`, `windows-terminal`, or `auto` |
| `--on-conflict` | `-o` | Conflict policy: `error`, `restart`, `rename`, `mergeNewWindowsOverwriteMatchingWindows`, or `mergeNewWindowsSkipMatchingWindows` |
| `--monitor` | `-m` | Monitor sessions for completion |
| `--kill-upon-completion` | `-k` | Kill sessions after completion when monitoring is enabled |
| `--substitute-home` | `-H` | Expand `~` and `$HOME` inside the layout file |

**Examples:**

```bash
# Run every layout in a file
sessions run --layouts-file layouts.json

# Run specific layouts
sessions run --layouts-file layouts.json --choose-layouts "dev,build"

# Choose layouts interactively
sessions run --layouts-file layouts.json --choose-layouts ""

# Monitor and kill sessions when they finish
sessions run --layouts-file layouts.json --monitor --kill-upon-completion

# Restart matching sessions before relaunching
sessions run --layouts-file layouts.json --on-conflict restart
```

---

## run-all

Dynamically merge every layout in a file into one paced run. Use this when you want to chug through the whole file while capping how many tabs stay active at once.

```bash
sessions run-all [OPTIONS]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--layouts-file` | `-f` | Path to the layout file |
| `--max-parallel-tabs` | - | Maximum number of tabs to keep active while dynamically scheduling the whole file |
| `--poll-seconds` | - | Polling interval used to detect finished tabs |
| `--kill-finished-tabs` | - | Close each dynamically scheduled tab after it finishes |
| `--backend` | `-b` | Backend to use: `tmux`, `zellij`, or `auto` |
| `--on-conflict` | `-o` | Conflict policy for the dynamic session |
| `--substitute-home` | `-H` | Expand `~` and `$HOME` inside the layout file |

**Examples:**

```bash
# Dynamically schedule at most eight tabs at a time
sessions run-all --layouts-file layouts.json --max-parallel-tabs 8

# Close finished tabs as the scheduler works through the file
sessions run-all --layouts-file layouts.json --max-parallel-tabs 8 --kill-finished-tabs
```

---

## run-aoe

Launch selected layout tabs through [agent-of-empires](https://github.com/njbrake/agent-of-empires).

The mapping is:

- `layoutName` -> `aoe add --group`
- `tabName` -> `aoe add --title`
- `startDir` -> `aoe add <path>`
- `command` -> initial prompt by default

```bash
sessions run-aoe [OPTIONS]
```

**Useful options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--layouts-file` | `-f` | Path to the layout file |
| `--choose-layouts` | `-c` | Comma-separated layout names; pass `""` for interactive selection |
| `--choose-tabs` | `-t` | Comma-separated tab names; pass `""` for interactive selection |
| `--sleep-inbetween` | `-S` | Delay between AoE launches |
| `--max-tabs-per-layout` | `-T` | Sanity-check cap for selected layouts |
| `--agent` | - | AoE tool or agent name; defaults to `codex` |
| `--model` | `-m` | Model forwarded to the underlying AoE or agent CLI |
| `--provider` | `-p` | Provider forwarded to the underlying AoE or agent CLI |
| `--sandbox` | - | Forward `--sandbox <value>` when supported |
| `--yolo` | - | Enable AoE or agent YOLO mode when supported |
| `--cmd` | - | Override the launched agent binary or command |
| `--args` | - | Repeatable extra arguments forwarded to the launched agent CLI |
| `--env` | - | Repeatable `KEY=VALUE` pairs forwarded to AoE when supported |
| `--force` | - | Forward force or overwrite to AoE when supported |
| `--dry-run` | - | Print generated `aoe add` commands without executing them |
| `--aoe-bin` | - | AoE executable to invoke |
| `--tab-command-mode` | - | Interpret `command` as `prompt`, `cmd`, or `ignore` |
| `--substitute-home` | `-H` | Expand `~` and `$HOME` inside the layout file |
| `--launch` / `--no-launch` | - | Control whether AoE sessions are launched immediately |

**Examples:**

```bash
# Treat each tab command as the initial prompt
sessions run-aoe --layouts-file layout.json --model gpt-5-codex --sandbox workspace-write --yolo

# Use tab commands as agent-command overrides instead
sessions run-aoe --layouts-file layout.json --tab-command-mode cmd

# Preview the generated aoe commands
sessions run-aoe --layouts-file layout.json --model gpt-5-codex --dry-run
```

---

## trace

Trace a tmux session until every target matches a strict stop criterion.

```bash
sessions trace SESSION_NAME [OPTIONS]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--every` | `-e` | Polling interval in seconds between tmux checks |
| `--until` | `-u` | Stop criterion: `idle-shell`, `all-exited`, `exit-code`, or `session-missing` |
| `--exit-code` | - | Required exit code when `--until exit-code` is selected |

**Examples:**

```bash
# Wait until every pane returns to an idle shell
sessions trace build-session

# Check every 5 seconds until every pane has exited
sessions trace build-session --every 5 --until all-exited

# Require every pane to exit successfully
sessions trace build-session --until exit-code --exit-code 0
```

---

## create-template

Create a layout template file in the current directory.

```bash
sessions create-template [NAME] [OPTIONS]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--num-tabs` | `-t` | Number of tabs in the template (default: 3) |

**Example:**

```bash
# Create a template with 5 tabs
sessions create-template my_layout --num-tabs 5
```

---

## create-from-function

Create a layout from a Python function to run in multiple processes.

```bash
sessions create-from-function [OPTIONS]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--num-process` | `-n` | Number of parallel processes to run |
| `--path` | `-p` | Path to a Python or shell script file, or a directory containing candidates |
| `--function` | `-f` | Function to run; if omitted, Machineconfig prompts you to choose |

**Example:**

```bash
# Create a layout for running a function in 4 parallel processes
sessions create-from-function --num-process 4 --path ./my_script.py --function process_data
```

---

## balance-load

Adjust a layout file to limit tabs per layout or total layout weight.

```bash
sessions balance-load LAYOUT_PATH [OPTIONS]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--max-threshold` | `-m` | Maximum tabs or total weight per layout |
| `--threshold-type` | `-t` | Threshold type: `number` or `weight` |
| `--breaking-method` | `-b` | Split strategy: `moreLayouts` or `combineTabs` |
| `--output-path` | `-o` | Output file path |

**Example:**

```bash
# Balance layouts to max 5 tabs each
sessions balance-load layouts.json --max-threshold 5 --threshold-type number --breaking-method moreLayouts
```

---

## Layout file format

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
        },
        {
          "tabName": "tests",
          "startDir": "~/projects/myapp",
          "command": "pytest --watch"
        }
      ]
    }
  ]
}
```

Older examples that use `tabs` or `cwd` are stale; the current schema uses `layoutTabs` and `startDir`.

---

## Session backends

`sessions run` currently supports these backends through `--backend`:

- `tmux` (default)
- `zellij`
- `windows-terminal`
- `auto`

`sessions run-all` supports:

- `tmux` (default)
- `zellij`
- `auto`

`trace` is tmux-specific. Use `auto` when you want Machineconfig to pick an available backend.

---

## Examples

```bash
# Create a layout template
sessions create-template dev_environment --num-tabs 4

# Run the layout
sessions run --layouts-file dev_environment.json

# Run with monitoring
sessions run --layouts-file tasks.json --monitor --kill-upon-completion

# Choose layouts interactively
sessions run --layouts-file layouts.json --choose-layouts ""

# Create a multiprocess layout
sessions create-from-function --num-process 8 --path ./process.py --function worker
```
