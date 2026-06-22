# StackOps Command Reference: `cloud`

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-21.

This page expands exactly one level below `cloud`. Follow child links one command segment at a time.

## Current Command

- Path: `cloud`
- Kind: `group`
- Source: `src/stackops/scripts/python/stackops_entry.py` -> `stackops.scripts.python.cloud.get_app` via `cloud`
- Help: `<c> Cloud management commands`

## Help Commands

- `UV_CACHE_DIR=/tmp/uv-cache uv run cloud --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run stackops cloud --help`

## Immediate Children

- [`cloud sync`](command--cloud--sync.md) - command with no child commands. Help: `🔄 Synchronize files/folders between local and cloud storage.`.
- [`cloud copy`](command--cloud--copy.md) - command with no child commands. Help: `📤 Upload or 📥 Download files/folders to/from cloud storage services.`.
- [`cloud mount`](command--cloud--mount.md) - command with no child commands. Help: `🔗 Mount cloud storage services as local drives.`.
- [`cloud ftpx`](command--cloud--ftpx.md) - command with no child commands. Help: `📦 File transfer utility through SSH.`.

## Notes

- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.
- Callback groups are invoked as the group command itself when their command reference has no children.
- The generated graph stores aliases on each node. Use `src/stackops/scripts/python/graph/cli_graph.json` when alias details matter.
- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.
