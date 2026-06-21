# StackOps Command Reference: `devops vault`

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-21.

This page expands exactly one level below `devops vault`. Follow child links one command segment at a time.

## Current Command

- Path: `devops vault`
- Kind: `group`
- Source: `src/stackops/scripts/python/devops.py` -> `stackops.scripts.python.helpers.helpers_devops.cli_vault.get_app` via `vault`
- Help: `🔐 <v> Search Bitwarden credentials and manage vault sessions`

## Help Commands

- `UV_CACHE_DIR=/tmp/uv-cache uv run devops vault --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run stackops devops vault --help`

## Immediate Children

- [`devops vault search`](command--devops--vault--search.md) - command with no child commands. Help: `<s> Retrieve credentials from Bitwarden CLI and optionally copy them to the clipboard.`.
- [`devops vault login-and-unlock`](command--devops--vault--login-and-unlock.md) - command with no child commands. Help: `<l> Log in with Bitwarden API credentials from StackOps secrets, unlock the vault, and persist BW_SESSION locally.`.
- [`devops vault clean-cache`](command--devops--vault--clean-cache.md) - command with no child commands. Help: `<c> Remove encrypted vault cache stored under ~/tmp_results.`.

## Notes

- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.
- Callback groups are invoked as the group command itself when their command reference has no children.
- The generated graph stores aliases on each node. Use `src/stackops/scripts/python/graph/cli_graph.json` when alias details matter.
- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.
