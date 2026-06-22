# StackOps Command Reference: `agents`

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-21.

This page expands exactly one level below `agents`. Follow child links one command segment at a time.

## Current Command

- Path: `agents`
- Kind: `group`
- Source: `src/stackops/scripts/python/stackops_entry.py` -> `stackops.scripts.python.agents.get_app` via `agents`
- Help: `<a> 🤖 AI Agents management commands`

## Help Commands

- `UV_CACHE_DIR=/tmp/uv-cache uv run agents --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run stackops agents --help`

## Immediate Children

- [`agents parallel`](command--agents--parallel.md) - group with 5 immediate child commands. Help: `🧵 <p> Parallel agent workflow commands`.
- [`agents browser`](command--agents--browser.md) - group with 2 immediate child commands. Help: `🌐 <b> Browser automation for agent CLIs and MCP`.
- [`agents add-mcp`](command--agents--add-mcp.md) - command with no child commands. Help: `Resolve MCP servers from stackops catalogs, install supported agent skills, or edit catalogs.`.
- [`agents add-skill`](command--agents--add-skill.md) - command with no child commands. Help: `Add a skill through an installer backend.`.
- [`agents add-todo`](command--agents--add-todo.md) - command with no child commands. Help: `Generate checklist with Python and shell script files in the repository or workspace filtered by pattern.`.
- [`agents add-symlinks`](command--agents--add-symlinks.md) - command with no child commands. Help: `Create symlinks to repo_root at ~/code_copies/${repo_name}_copy_{i}.`.
- [`agents add-config`](command--agents--add-config.md) - command with no child commands. Help: `Initialize AI configurations in the current repository.`.
- [`agents run-prompt`](command--agents--run-prompt.md) - command with no child commands. Help: `Run one prompt via selected agent.`.
- [`agents run-interactive`](command--agents--run-interactive.md) - command with no child commands. Help: `Launch an agent with reasonable defaults.`.
- [`agents ask`](command--agents--ask.md) - command with no child commands. Help: `Ask a selected agent directly.`.

## Notes

- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.
- Callback groups are invoked as the group command itself when their command reference has no children.
- The generated graph stores aliases on each node. Use `src/stackops/scripts/python/graph/cli_graph.json` when alias details matter.
- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.
