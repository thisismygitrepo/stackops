# StackOps Command Reference: `stackops`

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-21.

This page expands exactly one level below `stackops`. Follow child links one command segment at a time.

## Current Command

- Path: `stackops`
- Kind: `root`
- Source: `src/stackops/scripts/python/stackops_entry.py` -> `stackops.scripts.python.stackops_entry.get_app`
- Help: `StackOps CLI - Manage your machine configurations and workflows`

## Help Commands

- `UV_CACHE_DIR=/tmp/uv-cache uv run stackops --help`

## Immediate Children

- [`devops`](command--devops.md) - group with 8 immediate child commands. Help: `<d> DevOps related commands`.
- [`cloud`](command--cloud.md) - group with 4 immediate child commands. Help: `<c> Cloud management commands`.
- [`terminal`](command--terminal.md) - group with 10 immediate child commands. Help: `<t> Terminal and layout management`.
- [`agents`](command--agents.md) - group with 10 immediate child commands. Help: `<a> 🤖 AI Agents management commands`.
- [`utils`](command--utils.md) - group with 3 immediate child commands. Help: `<u> Utility commands`.
- [`seek`](command--seek.md) - group with 1 immediate child command. Help: `<s> Search across files, text matches, and code symbols`.
- [`fire`](command--fire.md) - command with no child commands. Help: `<f> Fire and manage jobs`.
- [`preview`](command--preview.md) - command with no child commands. Help: `<p> Preview files and launch reader backends`.

## Notes

- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.
- Callback groups are invoked as the group command itself when their command reference has no children.
- The generated graph stores aliases on each node. Use `src/stackops/scripts/python/graph/cli_graph.json` when alias details matter.
- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.
