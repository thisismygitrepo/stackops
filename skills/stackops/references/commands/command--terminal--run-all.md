# StackOps Command Reference: `terminal run-all`

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-21.

This page expands exactly one level below `terminal run-all`. Follow child links one command segment at a time.

## Current Command

- Path: `terminal run-all`
- Kind: `command`
- Source: `src/stackops/scripts/python/terminal.py` -> `run_all`
- Help: `Run every tab from every layout in a layout configuration file at a controlled pace.
New tab kicks in as soon as another tab finishes, keeping the total number of active tabs under the specified maximum.
Use this if problem is embarresingly parallel and is only constrained by resources.`

## Help Commands

- `UV_CACHE_DIR=/tmp/uv-cache uv run terminal run-all --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run stackops terminal run-all --help`

## Immediate Children

- No child command references. Use `UV_CACHE_DIR=/tmp/uv-cache uv run terminal run-all --help` for options and inspect `src/stackops/scripts/python/graph/cli_graph.json` for full metadata.

## Notes

- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.
- Callback groups are invoked as the group command itself when their command reference has no children.
- The generated graph stores aliases on each node. Use `src/stackops/scripts/python/graph/cli_graph.json` when alias details matter.
- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.
