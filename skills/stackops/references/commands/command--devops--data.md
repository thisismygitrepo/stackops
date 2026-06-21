# StackOps Command Reference: `devops data`

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-21.

This page expands exactly one level below `devops data`. Follow child links one command segment at a time.

## Current Command

- Path: `devops data`
- Kind: `group`
- Source: `src/stackops/scripts/python/devops.py` -> `stackops.scripts.python.helpers.helpers_devops.cli_data.get_app` via `data`
- Help: `💾 <d> Data management`

## Help Commands

- `UV_CACHE_DIR=/tmp/uv-cache uv run devops data --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run stackops devops data --help`

## Immediate Children

- [`devops data sync`](command--devops--data--sync.md) - command with no child commands. Help: `🔄 <s> Back up or retrieve files and directories using rclone or share links.`.
- [`devops data register`](command--devops--data--register.md) - command with no child commands. Help: `📝 <r> Register a new backup entry in user mapper/data.yaml.`.
- [`devops data edit`](command--devops--data--edit.md) - command with no child commands. Help: `✏️ <e> Open backup configuration file in nano, hx, or code.`.

## Notes

- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.
- Callback groups are invoked as the group command itself when their command reference has no children.
- The generated graph stores aliases on each node. Use `src/stackops/scripts/python/graph/cli_graph.json` when alias details matter.
- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.
