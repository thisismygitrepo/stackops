# StackOps Command Reference: `agents parallel`

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-21.

This page expands exactly one level below `agents parallel`. Follow child links one command segment at a time.

## Current Command

- Path: `agents parallel`
- Kind: `group`
- Source: `src/stackops/scripts/python/agents.py` -> `stackops.scripts.python.agents_parallel.get_app` via `parallel`
- Help: `🧵 <p> Parallel agent workflow commands`

## Help Commands

- `UV_CACHE_DIR=/tmp/uv-cache uv run agents parallel --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run stackops agents parallel --help`

## Immediate Children

- [`agents parallel create`](command--agents--parallel--create.md) - command with no child commands. Help: `f"\n<c> Create agents layout file, ready to run.\n{sep}\nPROVIDER options: {', '.join(get_args(PROVIDER))}\n{sep}\nAGENT options: {', '.join(get_args(AGENTS))}\n"`.
- [`agents parallel create-context`](command--agents--parallel--create-context.md) - command with no child commands. Help: `Run one prompt and ask the selected agent to persist a context file for the job.`.
- [`agents parallel run-parallel`](command--agents--parallel--run-parallel.md) - command with no child commands. Help: `Run a named parallel agent workflow from YAML, with create-option overrides.`.
- [`agents parallel collect`](command--agents--parallel--collect.md) - command with no child commands. Help: `collect.__doc__`.
- [`agents parallel make-template`](command--agents--parallel--make-template.md) - command with no child commands. Help: `make_agents_command_template.__doc__`.

## Notes

- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.
- Callback groups are invoked as the group command itself when their command reference has no children.
- The generated graph stores aliases on each node. Use `src/stackops/scripts/python/graph/cli_graph.json` when alias details matter.
- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.
