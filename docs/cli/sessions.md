# sessions

Terminal session and layout management for Zellij/Windows Terminal.

---

## Usage

```bash
sessions [OPTIONS] COMMAND [ARGS]...
```

---

## Commands Overview

| Command | Shortcut | Description |
|---------|----------|-------------|
| `run` | `r` | Launch sessions from layout file |
| `run-aoe` | - | Launch layout tabs as AoE sessions |
| `create-template` | `t` | Create a layout template file |
| `create-from-function` | `c` | Create layout from function |
| `balance-load` | `b` | Balance load across sessions |

---

## run

Launch terminal sessions based on a layout configuration file.
Use `--on-conflict` to choose behavior when a target session already exists (`skip`, `restart`, `rename`).

```bash
sessions run LAYOUT_PATH [OPTIONS]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--max-tabs` | `-mt` | Max tabs per layout (sanity check) |
| `--max-layouts` | `-ml` | Max parallel layouts (sanity check) |
| `--sleep-inbetween` | `-si` | Sleep time between layouts (seconds) |
| `--monitor` | `-m` | Monitor sessions for completion |
| `--parallel` | `-p` | Launch multiple layouts in parallel |
| `--on-conflict` | `-o` | Conflict policy for existing sessions: `skip`, `restart`, `rename` |
| `--kill-upon-completion` | `-k` | Kill sessions when done (requires --monitor) |
| `--choose` | `-c` | Comma-separated layout names to select |
| `--choose-interactively` | `-i` | Select layouts interactively |
| `--substitute-home` | `-sh` | Replace ~ and $HOME in paths |

**Examples:**

```bash
# Run all layouts in a file
sessions run layouts.json

# Run specific layouts
sessions run layouts.json --choose "dev,build"

# Interactive layout selection
sessions run layouts.json -i

# Monitor and kill upon completion
sessions run layouts.json --monitor --kill-upon-completion

# Restart existing session names and relaunch
sessions run layouts.json --on-conflict restart

# Run in parallel
sessions run layouts.json --parallel
```

---

## run-aoe

Launch selected layout tabs through [agent-of-empires](https://github.com/njbrake/agent-of-empires).
`run-aoe` detects the installed AoE CLI shape and adapts to both the older `--agent/--prompt` flow and newer AoE releases that use `--cmd/--cmd-override/--extra-args`.

The mapping is:

- `layoutName` -> `aoe add --group`
- `tabName` -> `aoe add --title`
- `startDir` -> `aoe add <path>`
- `command` -> initial prompt by default

```bash
sessions run-aoe --layouts-file layout.json [OPTIONS]
```

**Useful options:**

| Option | Description |
|--------|-------------|
| `--model` | Model name forwarded to the underlying AoE/agent CLI when supported |
| `--agent` | AoE tool/agent name (defaults to `codex`) |
| `--provider` | Provider forwarded to the underlying AoE/agent CLI when supported |
| `--sandbox` | Convenience flag forwarded to the launched agent CLI as `--sandbox <value>` when supported |
| `--yolo` | Enables AoE/agent YOLO mode when supported |
| `--tab-command-mode` | Interpret `command` as `prompt`, `cmd`, or `ignore` |
| `--dry-run` | Print the generated `aoe add` commands without executing them |
| `--force` | Forward force/overwrite to AoE when supported |

**Examples:**

```bash
# Treat each tab command as the initial prompt
sessions run-aoe --layouts-file layout.json --model gpt-5-codex --sandbox workspace-write --yolo

# Use existing tab commands as agent-command overrides instead
sessions run-aoe --layouts-file layout.json --tab-command-mode cmd

# Preview the generated aoe commands
sessions run-aoe --layouts-file layout.json --model gpt-5-codex --dry-run
```

---

## create-template

Create a layout template file.

```bash
sessions create-template [NAME] [OPTIONS]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--num-tabs` | `-t` | Number of tabs in template (default: 3) |

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
| `--num-process` | `-n` | Number of parallel processes |
| `--path` | `-p` | Path to Python/Shell script file or directory |
| `--function` | `-f` | Function to run (interactive if not provided) |

**Example:**

```bash
# Create layout for running function in 4 parallel processes
sessions create-from-function -n 4 -p ./my_script.py -f process_data
```

---

## balance-load

Adjust layout file to limit tabs per layout.

```bash
sessions balance-load LAYOUT_PATH [OPTIONS]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--max-threshold` | `-m` | Maximum tabs per layout |
| `--threshold-type` | `-t` | Type: `number`/`n` or `weight`/`w` |
| `--breaking-method` | `-b` | Method: `moreLayouts`/`ml` or `combineTabs`/`ct` |
| `--output-path` | `-o` | Output file path |

**Example:**

```bash
# Balance layouts to max 5 tabs each
sessions balance-load layouts.json -m 5 -t number -b moreLayouts
```

---

## Layout File Format

Layouts are defined in JSON format:

```json
[
  {
    "layoutName": "Development",
    "tabs": [
      {
        "tabName": "editor",
        "command": "hx .",
        "cwd": "~/projects/myapp"
      },
      {
        "tabName": "server",
        "command": "python -m http.server 8000"
      },
      {
        "tabName": "tests",
        "command": "pytest --watch"
      }
    ]
  },
  {
    "layoutName": "Monitoring",
    "tabs": [
      {
        "tabName": "htop",
        "command": "htop"
      },
      {
        "tabName": "logs",
        "command": "tail -f /var/log/syslog"
      }
    ]
  }
]
```

---

## Session Backends

Sessions uses platform-specific terminal multiplexers:

| Platform | Backend |
|----------|---------|
| Linux/macOS | Zellij |
| Windows | Windows Terminal |

!!! note "Zellij Required"
    On Linux/macOS, [Zellij](https://zellij.dev/) must be installed.
    Install via: `cargo install zellij` or your package manager.

---

## Examples

```bash
# Create a layout template
sessions create-template dev_environment -t 4

# Run the layout
sessions run dev_environment.json

# Run with monitoring
sessions run tasks.json --monitor --kill-upon-completion

# Interactive selection
sessions run layouts.json -i

# Create multiprocess layout
sessions create-from-function -n 8 -p ./process.py -f worker
```
