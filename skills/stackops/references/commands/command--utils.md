# StackOps Command Reference: `utils`

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-21.

This page expands exactly one level below `utils`. Follow child links one command segment at a time.

## Current Command

- Path: `utils`
- Kind: `group`
- Source: `src/stackops/scripts/python/stackops_entry.py` -> `stackops.scripts.python.utils.get_app` via `utils`
- Help: `<u> Utility commands`

## Help Commands

- `UV_CACHE_DIR=/tmp/uv-cache uv run utils --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run stackops utils --help`

## Immediate Children

- [`utils machine`](command--utils--machine.md) - group with 5 immediate child commands. Help: `🖥 <m> Machine and device utilities`.
- [`utils pyproject`](command--utils--pyproject.md) - group with 7 immediate child commands. Help: `🐍 <p> Pyproject bootstrap and typing utilities`.
- [`utils file`](command--utils--file.md) - group with 7 immediate child commands. Help: `📁 <f> File, document, and database utilities`.

## Notes

- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.
- Callback groups are invoked as the group command itself when their command reference has no children.
- The generated graph stores aliases on each node. Use `src/stackops/scripts/python/graph/cli_graph.json` when alias details matter.
- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.
