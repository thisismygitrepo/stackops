# StackOps Command Reference: `devops self build-assets`

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-21.

This page expands exactly one level below `devops self build-assets`. Follow child links one command segment at a time.

## Current Command

- Path: `devops self build-assets`
- Kind: `group`
- Source: `src/stackops/scripts/python/helpers/helpers_devops/cli_self.py` -> `stackops.scripts.python.helpers.helpers_devops.cli_self_assets.get_app` via `build-assets`
- Help: `🗂 <a> Regenerate repo-local CLI and skill assets.`

## Help Commands

- `UV_CACHE_DIR=/tmp/uv-cache uv run devops self build-assets --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run stackops devops self build-assets --help`

## Immediate Children

- [`devops self build-assets update-cli-graph`](command--devops--self--build-assets--update-cli-graph.md) - command with no child commands. Help: `🧩 <g> Regenerate the checked-in CLI graph snapshot.`.
- [`devops self build-assets regenerate-charts`](command--devops--self--build-assets--regenerate-charts.md) - command with no child commands. Help: `☀ <c> Regenerate the checked-in sunburst HTML chart.`.
- [`devops self build-assets update-skill-refs`](command--devops--self--build-assets--update-skill-refs.md) - command with no child commands. Help: `📚 <s> Regenerate the StackOps skill CLI reference maps.`.

## Notes

- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.
- Callback groups are invoked as the group command itself when their command reference has no children.
- The generated graph stores aliases on each node. Use `src/stackops/scripts/python/graph/cli_graph.json` when alias details matter.
- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.
