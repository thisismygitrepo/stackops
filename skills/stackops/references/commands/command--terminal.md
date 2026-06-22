# StackOps Command Reference: `terminal`

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-21.

This page expands exactly one level below `terminal`. Follow child links one command segment at a time.

## Current Command

- Path: `terminal`
- Kind: `group`
- Source: `src/stackops/scripts/python/stackops_entry.py` -> `stackops.scripts.python.terminal.get_app` via `terminal`
- Help: `<t> Terminal and layout management`

## Help Commands

- `UV_CACHE_DIR=/tmp/uv-cache uv run terminal --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run stackops terminal --help`

## Immediate Children

- [`terminal run`](command--terminal--run.md) - command with no child commands. Help: `Launch selected layouts from a layout configuration file.

Use --on-conflict to choose behavior when a target session already exists:
error, restart, rename, mergeOverwrite, or
mergeSkip. Those two merge policies are
supported for tmux.
Use 'run-all' for the paced whole-file dynamic scheduler.

The type of parallelization here is constrained by layouts. It asumes that every layout is a self-contained unit that must be launched in its entirety before the next one is launched, but multiple layouts can be launched at the same time if --parallel-layouts is set. If you want to launch every tab as soon as possible without waiting for the whole layout to launch, use 'run-all' instead.`.
- [`terminal run-all`](command--terminal--run-all.md) - command with no child commands. Help: `Run every tab from every layout in a layout configuration file at a controlled pace.
New tab kicks in as soon as another tab finishes, keeping the total number of active tabs under the specified maximum.
Use this if problem is embarresingly parallel and is only constrained by resources.`.
- [`terminal attach`](command--terminal--attach.md) - command with no child commands. Help: `Choose a session or deeper target to attach to.`.
- [`terminal kill`](command--terminal--kill.md) - command with no child commands. Help: `Choose one or more session targets to kill.`.
- [`terminal trace`](command--terminal--trace.md) - command with no child commands. Help: `Trace a terminal backend session until every target matches a strict stop criterion.`.
- [`terminal create-from-function`](command--terminal--create-from-function.md) - command with no child commands. Help: `Create a layout from a function to run in multiple processes.`.
- [`terminal balance-load`](command--terminal--balance-load.md) - command with no child commands. Help: `Adjust layout file to limit max tabs per layout, etc.`.
- [`terminal create-template`](command--terminal--create-template.md) - command with no child commands. Help: `Create a layout template file.`.
- [`terminal summary`](command--terminal--summary.md) - command with no child commands. Help: `summary.__doc__`.
- [`terminal summarize`](command--terminal--summarize.md) - command with no child commands. Help: `summarize.__doc__`.

## Notes

- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.
- Callback groups are invoked as the group command itself when their command reference has no children.
- The generated graph stores aliases on each node. Use `src/stackops/scripts/python/graph/cli_graph.json` when alias details matter.
- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.
