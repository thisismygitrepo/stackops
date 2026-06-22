# StackOps Command Reference: `devops repos`

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-21.

This page expands exactly one level below `devops repos`. Follow child links one command segment at a time.

## Current Command

- Path: `devops repos`
- Kind: `group`
- Source: `src/stackops/scripts/python/devops.py` -> `stackops.scripts.python.helpers.helpers_devops.cli_repos.get_app` via `repos`
- Help: `📁 <r> Manage development repositories`

## Help Commands

- `UV_CACHE_DIR=/tmp/uv-cache uv run devops repos --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run stackops devops repos --help`

## Immediate Children

- [`devops repos sync`](command--devops--repos--sync.md) - command with no child commands. Help: `📥 <s> Clone repositories described by a repos.json specification`.
- [`devops repos register`](command--devops--repos--register.md) - command with no child commands. Help: `📝 <r> Record repositories into a repos.json specification`.
- [`devops repos action`](command--devops--repos--action.md) - command with no child commands. Help: `🔄 <a> Run pull/commit/push actions across repositories`.
- [`devops repos analyze`](command--devops--repos--analyze.md) - command with no child commands. Help: `📊 <z> Analyze repository development over time`.
- [`devops repos guard`](command--devops--repos--guard.md) - command with no child commands. Help: `🔐 <g> Securely sync git repository to/from cloud with encryption`.
- [`devops repos viz`](command--devops--repos--viz.md) - command with no child commands. Help: `🎬 <v> Visualize repository activity using Gource`.
- [`devops repos count-lines`](command--devops--repos--count-lines.md) - command with no child commands. Help: `📄 <c> Count python lines of code in current repo + historical edits.`.
- [`devops repos config-linters`](command--devops--repos--config-linters.md) - command with no child commands. Help: `🧰 <l> Add linter config files to a git repository`.
- [`devops repos cleanup`](command--devops--repos--cleanup.md) - command with no child commands. Help: `🧹 <n> Clean repository directories from cache files`.

## Notes

- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.
- Callback groups are invoked as the group command itself when their command reference has no children.
- The generated graph stores aliases on each node. Use `src/stackops/scripts/python/graph/cli_graph.json` when alias details matter.
- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.
