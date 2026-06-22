# StackOps Command Reference: `utils pyproject`

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-21.

This page expands exactly one level below `utils pyproject`. Follow child links one command segment at a time.

## Current Command

- Path: `utils pyproject`
- Kind: `group`
- Source: `src/stackops/scripts/python/utils.py` -> `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_app.get_app` via `pyproject`
- Help: `🐍 <p> Pyproject bootstrap and typing utilities`

## Help Commands

- `UV_CACHE_DIR=/tmp/uv-cache uv run utils pyproject --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run stackops utils pyproject --help`

## Immediate Children

- [`utils pyproject init-project`](command--utils--pyproject--init-project.md) - command with no child commands. Help: `✦ <i> Initialize a project with a uv virtual environment and install dev packages.`.
- [`utils pyproject upgrade-packages`](command--utils--pyproject--upgrade-packages.md) - command with no child commands. Help: `↑ <a> Upgrade project dependencies.`.
- [`utils pyproject type-hint`](command--utils--pyproject--type-hint.md) - command with no child commands. Help: `✐ <t> Type hint a file or project directory.`.
- [`utils pyproject type-check`](command--utils--pyproject--type-check.md) - command with no child commands. Help: `🧪 <c> Run the lint-and-type-check suite for a repository.`.
- [`utils pyproject type-fix`](command--utils--pyproject--type-fix.md) - callback group with no child commands. Help: `🛠 <f> Create and run the type-fix workflow from ./.ai/linters issues files.`.
- [`utils pyproject test-runtime`](command--utils--pyproject--test-runtime.md) - callback group with no child commands. Help: `🧪 <R> Create and run the runtime-test workflow for Python files under the current directory.`.
- [`utils pyproject test-reference`](command--utils--pyproject--test-reference.md) - command with no child commands. Help: `🔎 <r> Validate _PATH_REFERENCE targets in a repository.`.

## Notes

- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.
- Callback groups are invoked as the group command itself when their command reference has no children.
- The generated graph stores aliases on each node. Use `src/stackops/scripts/python/graph/cli_graph.json` when alias details matter.
- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.
