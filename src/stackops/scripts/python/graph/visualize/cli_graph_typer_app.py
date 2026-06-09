from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typer


def build_cli_graph_app() -> "typer.Typer":
    from pathlib import Path
    from typing import Annotated, Literal

    import typer

    from stackops.scripts.python.graph.visualize.cli_graph_app import (
        chart as run_chart_command,
        dot as run_dot_command,
        navigate as run_navigate_command,
        search as run_search_command,
        tree as run_tree_command,
    )

    plotly_views = ("sunburst", "treemap", "icicle")

    def tree(
        show_help: Annotated[bool, typer.Option("--no-show-help", "-H", help="Hide help text in labels")] = True,
        show_aliases: Annotated[bool, typer.Option("--show-aliases", "-a", help="Include aliases in labels")] = False,
        max_depth: Annotated[int | None, typer.Option("--max-depth", "-d", min=0, help="Limit depth of the tree")] = None,
    ) -> None:
        run_tree_command(show_help=show_help, show_aliases=show_aliases, max_depth=max_depth)

    def dot(
        output: Annotated[Path | None, typer.Option("--output", "-o", help="Write DOT output to a file")] = None,
        include_help: Annotated[bool, typer.Option("--no-include-help", "-H", help="Hide help text in labels")] = True,
        max_depth: Annotated[int | None, typer.Option("--max-depth", "-d", help="Limit depth of the graph")] = None,
    ) -> None:
        run_dot_command(output=output, include_help=include_help, max_depth=max_depth)

    def chart(
        view: Annotated[
            Literal["sunburst", "treemap", "icicle"], typer.Argument(help=f"""Plotly chart view. Choose from {", ".join(plotly_views)}.""")
        ] = "sunburst",
        output: Annotated[Path | None, typer.Option("--output", "-o", help="Write HTML or image output")] = None,
        max_depth: Annotated[int | None, typer.Option("--max-depth", "-d", min=0, help="Limit depth of the graph")] = None,
        template: Annotated[str, typer.Option("--template", "-t", help="Plotly template name")] = "plotly_dark",
        height: Annotated[int, typer.Option("--height", "-H", help="Image height (for static output)")] = 900,
        width: Annotated[int, typer.Option("--width", "-w", help="Image width (for static output)")] = 1200,
    ) -> None:
        run_chart_command(view=view, output=output, max_depth=max_depth, template=template, height=height, width=width)

    def navigate() -> None:
        run_navigate_command()

    def search(
        graph_path: Annotated[Path | None, typer.Option("--graph-path", "-g", help="Path to cli_graph.json")] = None,
        json_output: Annotated[
            bool, typer.Option("--json", "-j", help="Print the selected cli_graph.json entry instead of the rendered summary.")
        ] = False,
    ) -> None:
        run_search_command(graph_path=graph_path, json_output=json_output)

    cli_app = typer.Typer(
        help="🧭 <g> Visualize the StackOps CLI graph in multiple formats.", no_args_is_help=True, add_help_option=True, add_completion=False
    )
    cli_app.command(name="search", no_args_is_help=False, help="🔎 <s> Search CLI graph entries and show the selected command summary.")(search)
    cli_app.command(name="s", no_args_is_help=False, help="Search CLI graph entries and show the selected command summary.", hidden=True)(search)
    cli_app.command(name="tree", no_args_is_help=False, help="🌳 <t> Render a rich tree view in the terminal.")(tree)
    cli_app.command(name="t", no_args_is_help=False, help="Render a rich tree view in the terminal.", hidden=True)(tree)
    cli_app.command(name="dot", no_args_is_help=False, help="🧩 <d> Export the graph as Graphviz DOT.")(dot)
    cli_app.command(name="d", no_args_is_help=False, help="Export the graph as Graphviz DOT.", hidden=True)(dot)
    cli_app.command(name="view", no_args_is_help=False, help="📊 <v> Render a Plotly hierarchy chart.")(chart)
    cli_app.command(name="v", no_args_is_help=False, help="Render a Plotly hierarchy chart.", hidden=True)(chart)
    cli_app.command(name="tui", no_args_is_help=False, help="📚 <u> NAVIGATE command structure with TUI")(navigate)
    cli_app.command(name="u", no_args_is_help=False, help="NAVIGATE command structure with TUI", hidden=True)(navigate)
    return cli_app
