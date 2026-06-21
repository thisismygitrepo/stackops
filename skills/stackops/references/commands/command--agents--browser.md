# StackOps Command Reference: `agents browser`

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-21.

This page expands exactly one level below `agents browser`. Follow child links one command segment at a time.

## Current Command

- Path: `agents browser`
- Kind: `group`
- Source: `src/stackops/scripts/python/agents.py` -> `stackops.scripts.python.agents_browser.get_app` via `browser`
- Help: `🌐 <b> Browser automation for agent CLIs and MCP`

## Help Commands

- `UV_CACHE_DIR=/tmp/uv-cache uv run agents browser --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run stackops agents browser --help`

## Immediate Children

- [`agents browser install-tech`](command--agents--browser--install-tech.md) - command with no child commands. Help: `Install browser automation CLI or MCP support for agents.`.
- [`agents browser launch-browser`](command--agents--browser--launch-browser.md) - command with no child commands. Help: `Launch Chrome or Brave with CDP enabled and an isolated profile.`.

## Notes

- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.
- Callback groups are invoked as the group command itself when their command reference has no children.
- The generated graph stores aliases on each node. Use `src/stackops/scripts/python/graph/cli_graph.json` when alias details matter.
- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.
