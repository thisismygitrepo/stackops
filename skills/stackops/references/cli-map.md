# StackOps CLI Map

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-23.

Use this as a root index only. Discover command groups, options, defaults, aliases, and help text from the live CLI with `--help`.

This reference intentionally excludes:
- command option listings
- generated per-command reference pages
- short aliases
- hidden alias-only paths
- nested command trees

Do not copy details from this file when `uv run <entrypoint> --help` can provide the current answer.

## Direct Entry Points

Defined in `pyproject.toml` `[project.scripts]`:

- `devops` -> `stackops.scripts.python.devops:main`
- `cloud` -> `stackops.scripts.python.cloud:main`
- `fire` -> `stackops.scripts.python.fire_jobs:main`
- `agents` -> `stackops.scripts.python.agents:main`
- `terminal` -> `stackops.scripts.python.terminal:main`
- `preview` -> `stackops.scripts.python.preview:main`
- `utils` -> `stackops.scripts.python.utils:main`
- `stackops` -> `stackops.scripts.python.stackops_entry:main`
- `seek` -> `stackops.scripts.python.seek:main`

## Top-Level Help

- `UV_CACHE_DIR=/tmp/uv-cache uv run stackops --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run devops --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run cloud --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run terminal --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run agents --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run utils --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run seek --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run fire --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run preview --help`

## Important Nuances

- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.
- Callback groups are invoked as the group command itself; confirm the exact behavior with `--help`.
- The generated graph stores aliases and metadata. Use `src/stackops/scripts/python/graph/cli_graph.json` only when live help or source is insufficient.
- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.
