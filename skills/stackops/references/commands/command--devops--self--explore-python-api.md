# StackOps Command Reference: `devops self explore-python-api`

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-21.

This page expands exactly one level below `devops self explore-python-api`. Follow child links one command segment at a time.

## Current Command

- Path: `devops self explore-python-api`
- Kind: `group`
- Source: `src/stackops/scripts/python/helpers/helpers_devops/cli_self.py` -> `stackops.scripts.python.graph.visualize.python_api_graph_app.get_app` via `explore-python-api`
- Help: `🧭 <p> Explore the StackOps Python API graph.`

## Help Commands

- `UV_CACHE_DIR=/tmp/uv-cache uv run devops self explore-python-api --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run stackops devops self explore-python-api --help`

## Immediate Children

- [`devops self explore-python-api search`](command--devops--self--explore-python-api--search.md) - command with no child commands. Help: `🔎 <s> Search Python API entries and show the selected import summary.`.
- [`devops self explore-python-api tree`](command--devops--self--explore-python-api--tree.md) - command with no child commands. Help: `🌳 <t> Render a rich tree view in the terminal.`.
- [`devops self explore-python-api dot`](command--devops--self--explore-python-api--dot.md) - command with no child commands. Help: `🧩 <d> Export the graph as Graphviz DOT.`.
- [`devops self explore-python-api view`](command--devops--self--explore-python-api--view.md) - command with no child commands. Help: `📊 <v> Render a Plotly hierarchy chart.`.
- [`devops self explore-python-api dump`](command--devops--self--explore-python-api--dump.md) - command with no child commands. Help: `📦 <j> Write the generated Python API graph JSON.`.
- [`devops self explore-python-api explain-filter`](command--devops--self--explore-python-api--explain-filter.md) - command with no child commands. Help: `🧪 <f> Explain how API files and members are selected.`.

## Notes

- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.
- Callback groups are invoked as the group command itself when their command reference has no children.
- The generated graph stores aliases on each node. Use `src/stackops/scripts/python/graph/cli_graph.json` when alias details matter.
- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.
