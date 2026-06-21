# StackOps Source Map

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-21.

Use this map as the root source index. Command-level source details live in the linked one-level command references.

## Root Entrypoints

- Umbrella entrypoint: `src/stackops/scripts/python/stackops_entry.py`. Reference: [`stackops`](commands/command--stackops.md)
- `devops` -> `src/stackops/scripts/python/stackops_entry.py` -> `stackops.scripts.python.devops.get_app` via `devops`. Reference: [`devops`](commands/command--devops.md)
- `cloud` -> `src/stackops/scripts/python/stackops_entry.py` -> `stackops.scripts.python.cloud.get_app` via `cloud`. Reference: [`cloud`](commands/command--cloud.md)
- `terminal` -> `src/stackops/scripts/python/stackops_entry.py` -> `stackops.scripts.python.terminal.get_app` via `terminal`. Reference: [`terminal`](commands/command--terminal.md)
- `agents` -> `src/stackops/scripts/python/stackops_entry.py` -> `stackops.scripts.python.agents.get_app` via `agents`. Reference: [`agents`](commands/command--agents.md)
- `utils` -> `src/stackops/scripts/python/stackops_entry.py` -> `stackops.scripts.python.utils.get_app` via `utils`. Reference: [`utils`](commands/command--utils.md)
- `seek` -> `src/stackops/scripts/python/stackops_entry.py` -> `stackops.scripts.python.seek.get_app` via `seek`. Reference: [`seek`](commands/command--seek.md)
- `fire` -> `src/stackops/scripts/python/stackops_entry.py` -> `fire`. Reference: [`fire`](commands/command--fire.md)
- `preview` -> `src/stackops/scripts/python/stackops_entry.py` -> `preview`. Reference: [`preview`](commands/command--preview.md)

## Debugging and Validation Workflow

1. Open the command reference for the current command segment.
2. Confirm command registration from the current page source route.
3. Follow only the next child reference when a deeper command segment is needed.
4. Validate help surface locally with `UV_CACHE_DIR=/tmp/uv-cache uv run <command> --help`.
5. If command names change, follow the `devops` reference chain to the generated-reference maintenance command.
