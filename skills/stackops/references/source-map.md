# StackOps Source Map

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-27.

Use this map as a root source index. For command-level source details, inspect Typer registrations and verify the live command with `--help`.

## Root Entrypoints

- Umbrella entrypoint: `src/stackops/scripts/python/stackops_entry.py`
- `devops` -> `src/stackops/scripts/python/stackops_entry.py` -> `stackops.scripts.python.devops.get_app` via `devops`
- `cloud` -> `src/stackops/scripts/python/stackops_entry.py` -> `stackops.scripts.python.cloud.get_app` via `cloud`
- `terminal` -> `src/stackops/scripts/python/stackops_entry.py` -> `stackops.scripts.python.terminal.get_app` via `terminal`
- `agents` -> `src/stackops/scripts/python/stackops_entry.py` -> `stackops.scripts.python.agents.get_app` via `agents`
- `utils` -> `src/stackops/scripts/python/stackops_entry.py` -> `stackops.scripts.python.utils.get_app` via `utils`
- `seek` -> `src/stackops/scripts/python/stackops_entry.py` -> `stackops.scripts.python.seek.get_app` via `seek`
- `fire` -> `src/stackops/scripts/python/stackops_entry.py` -> `fire`
- `preview` -> `src/stackops/scripts/python/stackops_entry.py` -> `preview`

## Debugging and Validation Workflow

1. Start from the relevant root entrypoint above.
2. Run `UV_CACHE_DIR=/tmp/uv-cache uv run <entrypoint> --help` and then repeat with each discovered command segment.
3. Inspect the Typer registration source only after the live help identifies the command path.
4. For broad graph debugging, inspect `src/stackops/scripts/python/graph/cli_graph.json`.
5. After changing command names or registrations, run `UV_CACHE_DIR=/tmp/uv-cache uv run devops self build-assets update-skill-refs`.
