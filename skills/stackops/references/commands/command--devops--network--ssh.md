# StackOps Command Reference: `devops network ssh`

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-21.

This page expands exactly one level below `devops network ssh`. Follow child links one command segment at a time.

## Current Command

- Path: `devops network ssh`
- Kind: `group`
- Source: `src/stackops/scripts/python/helpers/helpers_devops/cli_nw.py` -> `stackops.scripts.python.helpers.helpers_devops.cli_ssh.get_app` via `ssh`
- Help: `🔐 <S> SSH subcommands`

## Help Commands

- `UV_CACHE_DIR=/tmp/uv-cache uv run devops network ssh --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run stackops devops network ssh --help`

## Immediate Children

- [`devops network ssh install-server`](command--devops--network--ssh--install-server.md) - command with no child commands. Help: `📡 <i> Install SSH server`.
- [`devops network ssh change-port`](command--devops--network--ssh--change-port.md) - command with no child commands. Help: `🔌 <p> Change SSH port (Linux/WSL only)`.
- [`devops network ssh add-key`](command--devops--network--ssh--add-key.md) - command with no child commands. Help: `🔑 <k> Add SSH public key to this machine`.
- [`devops network ssh debug`](command--devops--network--ssh--debug.md) - command with no child commands. Help: `🐛 <d> Debug SSH connection`.

## Notes

- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.
- Callback groups are invoked as the group command itself when their command reference has no children.
- The generated graph stores aliases on each node. Use `src/stackops/scripts/python/graph/cli_graph.json` when alias details matter.
- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.
