from pathlib import Path
from typing import Annotated, Literal, TypeAlias, get_args

import typer

from stackops.scripts.python.graph.visualize.cli_graph_app import resolve_uv_context


PlotlyView: TypeAlias = Literal["sunburst", "treemap", "icicle"]


def _filter_explanation() -> str:
    return """Python API graph filter:

- Start from docs/api, not the raw source tree.
- Include modules named by mkdocstrings directives such as `::: stackops.utils.code`.
- Include explicit docs import examples such as `from stackops.utils.code import run_shell_script`.
- Do not expand wildcard prose mentions automatically.
- Parse selected modules with AST and include public top-level classes, functions, async functions, and uppercase constants.
- If a selected module defines `__all__`, use it to narrow include-all member selection.
- Skip private names and common CLI wiring names such as `main`, `get_app`, `app`, and `cli_app`.
"""


def materialize_python_api_graph_path(graph_path_str: str | None) -> str:
    if graph_path_str:
        return graph_path_str

    from stackops.scripts.python.graph.python_api_graph import write_python_api_graph_temp

    return str(write_python_api_graph_temp())


def explain_filter() -> None:
    """Explain how Python API modules and members are selected."""
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel

    Console().print(Panel(Markdown(_filter_explanation()), title="Python API Filter", border_style="cyan"))


def tree(
    graph_path: Annotated[Path | None, typer.Option("--graph-path", "-g", help="Use an existing Python API graph JSON file.")] = None,
    show_help: Annotated[bool, typer.Option("--no-show-help", "-H", help="Hide help text in labels")] = True,
    max_depth: Annotated[int | None, typer.Option("--max-depth", "-d", min=0, help="Limit depth of the tree")] = None,
) -> None:
    """Render a rich tree view in the terminal."""

    def func(graph_path_str: str | None, show_help: bool, max_depth: int | None) -> None:
        from stackops.scripts.python.graph.visualize.rich_tree import render_tree
        from stackops.scripts.python.graph.visualize.python_api_graph_app import materialize_python_api_graph_path

        render_tree(path=materialize_python_api_graph_path(graph_path_str), show_help=show_help, show_aliases=False, max_depth=max_depth)

    from stackops.utils.code import exit_then_run_shell_script, get_shell_script_running_lambda_function

    uv_with, uv_project_dir = resolve_uv_context(local_uv_with=[], external_uv_with=[])
    shell_script, _pyfile = get_shell_script_running_lambda_function(
        lambda: func(graph_path_str=str(graph_path) if graph_path else None, show_help=show_help, max_depth=max_depth),
        uv_with=uv_with,
        uv_project_dir=uv_project_dir,
    )
    exit_then_run_shell_script(str(shell_script), strict=False)


def dot(
    graph_path: Annotated[Path | None, typer.Option("--graph-path", "-g", help="Use an existing Python API graph JSON file.")] = None,
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Write DOT output to a file")] = None,
    include_help: Annotated[bool, typer.Option("--no-include-help", "-H", help="Hide help text in labels")] = True,
    max_depth: Annotated[int | None, typer.Option("--max-depth", "-d", help="Limit depth of the graph")] = None,
) -> None:
    """Export the graph as Graphviz DOT."""

    def func(graph_path_str: str | None, output_str: str | None, include_help: bool, max_depth: int | None) -> None:
        from pathlib import Path

        from stackops.scripts.python.graph.visualize.dot_export import render_dot
        from stackops.scripts.python.graph.visualize.python_api_graph_app import materialize_python_api_graph_path

        dot_text = render_dot(path=materialize_python_api_graph_path(graph_path_str), max_depth=max_depth, include_help=include_help)
        if output_str is None:
            print(dot_text)
        else:
            output_path = Path(output_str)
            output_path.write_text(dot_text, encoding="utf-8")
            print(f"Wrote {output_path}")

    from stackops.utils.code import exit_then_run_shell_script, get_shell_script_running_lambda_function

    uv_with, uv_project_dir = resolve_uv_context(local_uv_with=[], external_uv_with=[])
    shell_script, _pyfile = get_shell_script_running_lambda_function(
        lambda: func(
            graph_path_str=str(graph_path) if graph_path else None,
            output_str=str(output) if output else None,
            include_help=include_help,
            max_depth=max_depth,
        ),
        uv_with=uv_with,
        uv_project_dir=uv_project_dir,
    )
    exit_then_run_shell_script(str(shell_script), strict=False)


def chart(
    view: Annotated[
        PlotlyView,
        typer.Argument(help=f"""Plotly chart view. Choose from {", ".join(get_args(PlotlyView))}."""),
    ] = "sunburst",
    graph_path: Annotated[Path | None, typer.Option("--graph-path", "-g", help="Use an existing Python API graph JSON file.")] = None,
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Write HTML or image output")] = None,
    max_depth: Annotated[int | None, typer.Option("--max-depth", "-d", min=0, help="Limit depth of the graph")] = None,
    template: Annotated[str, typer.Option("--template", "-t", help="Plotly template name")] = "plotly_dark",
    height: Annotated[int, typer.Option("--height", "-H", help="Image height (for static output)")] = 900,
    width: Annotated[int, typer.Option("--width", "-w", help="Image width (for static output)")] = 1200,
) -> None:
    """Render a Plotly hierarchy chart."""
    graph_file = materialize_python_api_graph_path(str(graph_path) if graph_path else None)

    from stackops.scripts.python.graph.visualize.plotly_views import use_render_plotly

    uv_with, uv_project_dir = resolve_uv_context(local_uv_with=None, external_uv_with=[])
    use_render_plotly(
        view=view,
        output=str(output) if output else None,
        height=height,
        width=width,
        template=template,
        max_depth=max_depth,
        path=graph_file,
        uv_with=uv_with,
        uv_project_dir=uv_project_dir,
        title=f"Python API Graph - {view.title()}",
        item_label="Import",
    )


def search(
    graph_path: Annotated[Path | None, typer.Option("--graph-path", "-g", help="Use an existing Python API graph JSON file.")] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", "-j", help="Print the selected graph entry instead of the rendered summary."),
    ] = False,
) -> None:
    """Search Python API entries and show the selected import summary."""

    def func(graph_path_str: str | None, json_output: bool) -> None:
        from pathlib import Path

        import typer

        from stackops.scripts.python.graph.visualize.python_api_graph_app import materialize_python_api_graph_path
        from stackops.scripts.python.graph.visualize.python_api_graph_search import search_python_api_graph

        graph_file = Path(materialize_python_api_graph_path(graph_path_str))
        return_code = search_python_api_graph(graph_path=graph_file, json_output=json_output)
        if return_code != 0:
            raise typer.Exit(code=return_code)

    from stackops.utils.code import exit_then_run_shell_script, get_shell_script_running_lambda_function

    uv_with, uv_project_dir = resolve_uv_context(local_uv_with=[], external_uv_with=[])
    shell_script, _pyfile = get_shell_script_running_lambda_function(
        lambda: func(graph_path_str=str(graph_path) if graph_path else None, json_output=json_output),
        uv_with=uv_with,
        uv_project_dir=uv_project_dir,
    )
    exit_then_run_shell_script(str(shell_script), strict=False)


def dump(
    output: Annotated[Path, typer.Argument(help="Write the Python API graph JSON to this path.")],
) -> None:
    """Write the generated Python API graph JSON."""
    from stackops.scripts.python.graph.python_api_graph import write_python_api_graph_json

    written = write_python_api_graph_json(output=output)
    typer.echo(f"Wrote {written}")


def get_app() -> typer.Typer:
    cli_app = typer.Typer(
        help="🧭 <p> Visualize the StackOps Python API graph in multiple formats.",
        no_args_is_help=True,
        add_help_option=True,
        add_completion=False,
    )
    cli_app.command(name="search", no_args_is_help=False, help="🔎 <s> Search Python API entries and show the selected import summary.")(search)
    cli_app.command(name="s", no_args_is_help=False, help="Search Python API entries and show the selected import summary.", hidden=True)(search)
    cli_app.command(name="tree", no_args_is_help=False, help="🌳 <t> Render a rich tree view in the terminal.")(tree)
    cli_app.command(name="t", no_args_is_help=False, help="Render a rich tree view in the terminal.", hidden=True)(tree)
    cli_app.command(name="dot", no_args_is_help=False, help="🧩 <d> Export the graph as Graphviz DOT.")(dot)
    cli_app.command(name="d", no_args_is_help=False, help="Export the graph as Graphviz DOT.", hidden=True)(dot)
    cli_app.command(name="view", no_args_is_help=False, help="📊 <v> Render a Plotly hierarchy chart.")(chart)
    cli_app.command(name="v", no_args_is_help=False, help="Render a Plotly hierarchy chart.", hidden=True)(chart)
    cli_app.command(name="dump", no_args_is_help=True, help="📦 <j> Write the generated Python API graph JSON.")(dump)
    cli_app.command(name="j", no_args_is_help=True, help="Write the generated Python API graph JSON.", hidden=True)(dump)
    cli_app.command(name="explain-filter", no_args_is_help=False, help="🧪 <f> Explain how API files and members are selected.")(explain_filter)
    cli_app.command(name="f", no_args_is_help=False, help="Explain how API files and members are selected.", hidden=True)(explain_filter)
    return cli_app


def main() -> None:
    app = get_app()
    app()


if __name__ == "__main__":
    main()
