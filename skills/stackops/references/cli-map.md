# StackOps CLI Map

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-21.

This reference intentionally uses:
- direct commands only
- canonical command names only
- one-level command expansion through linked command reference files

This reference intentionally excludes:
- short aliases
- hidden alias-only paths
- nested command trees

Open exactly the next command reference you need instead of loading the full CLI tree.

## Direct Entry Points

Defined in `pyproject.toml` `[project.scripts]`:

- `devops` -> `stackops.scripts.python.devops:main`. Reference: [`devops`](commands/command--devops.md)
- `cloud` -> `stackops.scripts.python.cloud:main`. Reference: [`cloud`](commands/command--cloud.md)
- `fire` -> `stackops.scripts.python.fire_jobs:main`. Reference: [`fire`](commands/command--fire.md)
- `agents` -> `stackops.scripts.python.agents:main`. Reference: [`agents`](commands/command--agents.md)
- `terminal` -> `stackops.scripts.python.terminal:main`. Reference: [`terminal`](commands/command--terminal.md)
- `preview` -> `stackops.scripts.python.preview:main`. Reference: [`preview`](commands/command--preview.md)
- `utils` -> `stackops.scripts.python.utils:main`. Reference: [`utils`](commands/command--utils.md)
- `stackops` -> `stackops.scripts.python.stackops_entry:main`. Reference: [`stackops`](commands/command--stackops.md)
- `seek` -> `stackops.scripts.python.seek:main`. Reference: [`seek`](commands/command--seek.md)

## Top-Level Command References

- [`stackops`](commands/command--stackops.md) - umbrella dispatcher and root source.
- [`devops`](commands/command--devops.md) - group with 8 immediate child commands.
- [`cloud`](commands/command--cloud.md) - group with 4 immediate child commands.
- [`terminal`](commands/command--terminal.md) - group with 10 immediate child commands.
- [`agents`](commands/command--agents.md) - group with 10 immediate child commands.
- [`utils`](commands/command--utils.md) - group with 3 immediate child commands.
- [`seek`](commands/command--seek.md) - group with 1 immediate child command.
- [`fire`](commands/command--fire.md) - command with no child commands.
- [`preview`](commands/command--preview.md) - command with no child commands.

## Important Nuances

- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.
- Callback groups are invoked as the group command itself when their command reference has no children.
- The generated graph stores aliases on each node. Use `src/stackops/scripts/python/graph/cli_graph.json` when alias details matter.
- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.
