# StackOps Command Reference: `devops`

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-21.

This page expands exactly one level below `devops`. Follow child links one command segment at a time.

## Current Command

- Path: `devops`
- Kind: `group`
- Source: `src/stackops/scripts/python/stackops_entry.py` -> `stackops.scripts.python.devops.get_app` via `devops`
- Help: `<d> DevOps related commands`

## Help Commands

- `UV_CACHE_DIR=/tmp/uv-cache uv run devops --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run stackops devops --help`

## Immediate Children

- [`devops install`](command--devops--install.md) - command with no child commands. Help: `📦 Install packages.`.
- [`devops data`](command--devops--data.md) - group with 3 immediate child commands. Help: `💾 <d> Data management`.
- [`devops repos`](command--devops--repos.md) - group with 9 immediate child commands. Help: `📁 <r> Manage development repositories`.
- [`devops config`](command--devops--config.md) - group with 10 immediate child commands. Help: `🔩 <c> Configuration management`.
- [`devops vault`](command--devops--vault.md) - group with 3 immediate child commands. Help: `🔐 <v> Search Bitwarden credentials and manage vault sessions`.
- [`devops network`](command--devops--network.md) - group with 9 immediate child commands. Help: `🌐 <n> Network management`.
- [`devops execute`](command--devops--execute.md) - command with no child commands. Help: `🚀 Execute python/shell scripts from pre-defined directories or as command.`.
- [`devops self`](command--devops--self.md) - group with 14 immediate child commands. Help: `🔧 <s> Self management`.

## Notes

- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.
- Callback groups are invoked as the group command itself when their command reference has no children.
- The generated graph stores aliases on each node. Use `src/stackops/scripts/python/graph/cli_graph.json` when alias details matter.
- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.
