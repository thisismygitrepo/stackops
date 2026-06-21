# StackOps Command Reference: `utils machine`

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-21.

This page expands exactly one level below `utils machine`. Follow child links one command segment at a time.

## Current Command

- Path: `utils machine`
- Kind: `group`
- Source: `src/stackops/scripts/python/utils.py` -> `stackops.scripts.python.helpers.helpers_utils.machine_utils_app.get_app` via `machine`
- Help: `🖥 <m> Machine and device utilities`

## Help Commands

- `UV_CACHE_DIR=/tmp/uv-cache uv run utils machine --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run stackops utils machine --help`

## Immediate Children

- [`utils machine kill-process`](command--utils--machine--kill-process.md) - command with no child commands. Help: `⚔ <k> Choose a process to kill`.
- [`utils machine environment`](command--utils--machine--environment.md) - command with no child commands. Help: `⌘ <v> Navigate ENV/PATH variables. Default: fuzzy picker with preview; use --tui for Textual.`.
- [`utils machine get-machine-specs`](command--utils--machine--get-machine-specs.md) - command with no child commands. Help: `🖥 <s> Get machine specifications.`.
- [`utils machine list-devices`](command--utils--machine--list-devices.md) - command with no child commands. Help: `💽 <l> List available devices for mounting.`.
- [`utils machine mount`](command--utils--machine--mount.md) - command with no child commands. Help: `🔌 <m> Mount a device to a mount point.`.

## Notes

- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.
- Callback groups are invoked as the group command itself when their command reference has no children.
- The generated graph stores aliases on each node. Use `src/stackops/scripts/python/graph/cli_graph.json` when alias details matter.
- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.
