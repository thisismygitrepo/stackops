# StackOps Command Reference: `devops vault clean-cache`

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-21.

This page expands exactly one level below `devops vault clean-cache`. Follow child links one command segment at a time.

## Current Command

- Path: `devops vault clean-cache`
- Kind: `command`
- Source: `src/stackops/scripts/python/helpers/helpers_devops/cli_vault.py` -> `clean_cache`
- Help: `<c> Remove encrypted vault cache stored under ~/tmp_results.`

## Help Commands

- `UV_CACHE_DIR=/tmp/uv-cache uv run devops vault clean-cache --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run stackops devops vault clean-cache --help`

## Immediate Children

- No child command references. Use `UV_CACHE_DIR=/tmp/uv-cache uv run devops vault clean-cache --help` for options and inspect `src/stackops/scripts/python/graph/cli_graph.json` for full metadata.

## Notes

- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.
- Callback groups are invoked as the group command itself when their command reference has no children.
- The generated graph stores aliases on each node. Use `src/stackops/scripts/python/graph/cli_graph.json` when alias details matter.
- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.
