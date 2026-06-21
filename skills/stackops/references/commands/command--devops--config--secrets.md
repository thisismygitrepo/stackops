# StackOps Command Reference: `devops config secrets`

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-21.

This page expands exactly one level below `devops config secrets`. Follow child links one command segment at a time.

## Current Command

- Path: `devops config secrets`
- Kind: `group`
- Source: `src/stackops/scripts/python/helpers/helpers_devops/cli_config.py` -> `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets.get_app` via `secrets`
- Help: `f'🔐 <S> {secrets_module.SECRETS_HELP}'`

## Help Commands

- `UV_CACHE_DIR=/tmp/uv-cache uv run devops config secrets --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run stackops devops config secrets --help`

## Immediate Children

- [`devops config secrets search`](command--devops--config--secrets--search.md) - command with no child commands. Help: `f'🔎 <s> {SECRETS_SEARCH_HELP}'`.
- [`devops config secrets stats`](command--devops--config--secrets--stats.md) - command with no child commands. Help: `f'📊 <t> {SECRETS_STATS_HELP}'`.
- [`devops config secrets subset`](command--devops--config--secrets--subset.md) - command with no child commands. Help: `f'📦 <u> {SECRETS_SUBSET_HELP}'`.
- [`devops config secrets add`](command--devops--config--secrets--add.md) - command with no child commands. Help: `➕ <a> Append a new login entry to a StackOps secrets file.`.
- [`devops config secrets edit`](command--devops--config--secrets--edit.md) - command with no child commands. Help: `📝 <e> Open a StackOps secrets file for editing.`.

## Notes

- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.
- Callback groups are invoked as the group command itself when their command reference has no children.
- The generated graph stores aliases on each node. Use `src/stackops/scripts/python/graph/cli_graph.json` when alias details matter.
- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.
