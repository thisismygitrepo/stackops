# StackOps Command Reference: `terminal run`

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-21.

This page expands exactly one level below `terminal run`. Follow child links one command segment at a time.

## Current Command

- Path: `terminal run`
- Kind: `command`
- Source: `src/stackops/scripts/python/terminal.py` -> `run`
- Help: `Launch selected layouts from a layout configuration file.

Use --on-conflict to choose behavior when a target session already exists:
error, restart, rename, mergeOverwrite, or
mergeSkip. Those two merge policies are
supported for tmux.
Use 'run-all' for the paced whole-file dynamic scheduler.

The type of parallelization here is constrained by layouts. It asumes that every layout is a self-contained unit that must be launched in its entirety before the next one is launched, but multiple layouts can be launched at the same time if --parallel-layouts is set. If you want to launch every tab as soon as possible without waiting for the whole layout to launch, use 'run-all' instead.`

## Help Commands

- `UV_CACHE_DIR=/tmp/uv-cache uv run terminal run --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run stackops terminal run --help`

## Immediate Children

- No child command references. Use `UV_CACHE_DIR=/tmp/uv-cache uv run terminal run --help` for options and inspect `src/stackops/scripts/python/graph/cli_graph.json` for full metadata.

## Notes

- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.
- Callback groups are invoked as the group command itself when their command reference has no children.
- The generated graph stores aliases on each node. Use `src/stackops/scripts/python/graph/cli_graph.json` when alias details matter.
- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.
