# StackOps Command Reference: `devops self explore-cli`

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-21.

This page expands exactly one level below `devops self explore-cli`. Follow child links one command segment at a time.

## Current Command

- Path: `devops self explore-cli`
- Kind: `group`
- Source: `src/stackops/scripts/python/helpers/helpers_devops/cli_self.py` -> `stackops.scripts.python.graph.visualize.cli_graph_app.get_app` via `explore-cli`
- Help: `🧭 <x> Explore the StackOps CLI graph.`

## Help Commands

- `UV_CACHE_DIR=/tmp/uv-cache uv run devops self explore-cli --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run stackops devops self explore-cli --help`

## Immediate Children

- [`devops self explore-cli search`](command--devops--self--explore-cli--search.md) - command with no child commands. Help: `🔎 <s> Search CLI graph entries and show the selected command summary.`.
- [`devops self explore-cli tree`](command--devops--self--explore-cli--tree.md) - command with no child commands. Help: `🌳 <t> Render a rich tree view in the terminal.`.
- [`devops self explore-cli dot`](command--devops--self--explore-cli--dot.md) - command with no child commands. Help: `🧩 <d> Export the graph as Graphviz DOT.`.
- [`devops self explore-cli view`](command--devops--self--explore-cli--view.md) - command with no child commands. Help: `📊 <v> Render a Plotly hierarchy chart.`.
- [`devops self explore-cli tui`](command--devops--self--explore-cli--tui.md) - command with no child commands. Help: `📚 <u> NAVIGATE command structure with TUI`.

## Notes

- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.
- Callback groups are invoked as the group command itself when their command reference has no children.
- The generated graph stores aliases on each node. Use `src/stackops/scripts/python/graph/cli_graph.json` when alias details matter.
- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.
