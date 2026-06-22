# StackOps Command Reference: `agents add-symlinks`

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-21.

This page expands exactly one level below `agents add-symlinks`. Follow child links one command segment at a time.

## Current Command

- Path: `agents add-symlinks`
- Kind: `command`
- Source: `src/stackops/scripts/python/agents.py` -> `create_symlink_command`
- Help: `Create symlinks to repo_root at ~/code_copies/${repo_name}_copy_{i}.`

## Help Commands

- `UV_CACHE_DIR=/tmp/uv-cache uv run agents add-symlinks --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run stackops agents add-symlinks --help`

## Immediate Children

- No child command references. Use `UV_CACHE_DIR=/tmp/uv-cache uv run agents add-symlinks --help` for options and inspect `src/stackops/scripts/python/graph/cli_graph.json` for full metadata.

## Notes

- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.
- Callback groups are invoked as the group command itself when their command reference has no children.
- The generated graph stores aliases on each node. Use `src/stackops/scripts/python/graph/cli_graph.json` when alias details matter.
- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.
