

from pathlib import Path
from typing import Annotated, Literal, TypeAlias, get_args

import typer


PlotlyView: TypeAlias = Literal["sunburst", "treemap", "icicle"]


def tree(
    show_help: Annotated[bool, typer.Option("--show-help/--no-show-help", help="Include help text in labels")] = True,
    show_aliases: Annotated[bool, typer.Option("--show-aliases/--no-show-aliases", help="Include aliases in labels")] = False,
    max_depth: Annotated[int | None, typer.Option("--max-depth", "-d", help="Limit depth of the tree")] = None,
) -> None:
    """Render a rich tree view in the terminal."""
    def func(show_help: bool, show_aliases: bool, max_depth: int | None) -> None:
        from stackops.scripts.python.graph.visualize.rich_tree import render_tree

        render_tree(show_help=show_help, show_aliases=show_aliases, max_depth=max_depth)

    from stackops.utils.ssh_utils.abc import STACKOPS_VERSION
    from stackops.utils.code import get_shell_script_running_lambda_function, exit_then_run_shell_script

    if Path.home().joinpath("code", "stackops").exists():
        uv_with: list[str] = ["plotly", "kaleido"]
        uv_project_dir = str(Path.home().joinpath("code", "stackops"))
    else:
        uv_with = [STACKOPS_VERSION, "plotly", "kaleido"]
        uv_project_dir = None

    shell_script, _pyfile = get_shell_script_running_lambda_function(
        lambda: func(
            show_help=show_help,
            show_aliases=show_aliases,
            max_depth=max_depth,
        ),
        uv_with=uv_with,
        uv_project_dir=uv_project_dir,
    )
    exit_then_run_shell_script(str(shell_script), strict=False)


def dot(
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Write DOT output to a file")] = None,
    include_help: Annotated[bool, typer.Option("--include-help/--no-include-help", help="Include help text in labels")] = True,
    max_depth: Annotated[int | None, typer.Option("--max-depth", "-d", help="Limit depth of the graph")] = None,
) -> None:
    """Export the graph as Graphviz DOT."""
    def func(output_str: str | None, include_help: bool, max_depth: int | None) -> None:
        from pathlib import Path
        from stackops.scripts.python.graph.visualize.dot_export import render_dot

        output_path = Path(output_str) if output_str else None
        dot_text = render_dot(max_depth=max_depth, include_help=include_help)

        if output_path is None:
            print(dot_text)
        else:
            output_path.write_text(dot_text, encoding="utf-8")
            print(f"Wrote {output_path}")

    from stackops.utils.ssh_utils.abc import STACKOPS_VERSION
    from stackops.utils.code import get_shell_script_running_lambda_function, exit_then_run_shell_script

    if Path.home().joinpath("code", "stackops").exists():
        uv_with: list[str] = ["plotly", "kaleido"]
        uv_project_dir = str(Path.home().joinpath("code", "stackops"))
    else:
        uv_with = [STACKOPS_VERSION]
        uv_project_dir = None

    shell_script, _pyfile = get_shell_script_running_lambda_function(
        lambda: func(
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
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Write HTML or image output")] = None,
    max_depth: Annotated[int | None, typer.Option("--max-depth", "-d", help="Limit depth of the graph")] = None,
    template: Annotated[str, typer.Option("--template", help="Plotly template name")] = "plotly_dark",
    height: Annotated[int, typer.Option("--height", help="Image height (for static output)")] = 900,
    width: Annotated[int, typer.Option("--width", help="Image width (for static output)")] = 1200,
) -> None:
    """Render a Plotly hierarchy chart."""
    from stackops.utils.ssh_utils.abc import STACKOPS_VERSION
    from stackops.scripts.python.graph.visualize.plotly_views import use_render_plotly

    if Path.home().joinpath("code", "stackops").exists():
        uv_with: list[str] | None = None
        uv_project_dir = str(Path.home().joinpath("code/stackops"))
    else:
        uv_with = [STACKOPS_VERSION]
        uv_project_dir = None

    use_render_plotly(
        view=view,
        output=str(output) if output else None,
        height=height,
        width=width,
        template=template,
        max_depth=max_depth,
        path=None,
        uv_with=uv_with,
        uv_project_dir=uv_project_dir,
    )


def navigate():
    """📚 NAVIGATE command structure with TUI"""
    from stackops.utils.ssh_utils.abc import STACKOPS_VERSION
    # import stackops.scripts.python.graph.visualize.helpers_navigator as navigator
    # path = Path(navigator.__file__).resolve().parent.joinpath("devops_navigator.py")
    # from stackops.utils.code import exit_then_run_shell_script
    # if Path.home().joinpath("code", "stackops").exists():
    #     executable = f"""--project "{str(Path.home().joinpath("code/stackops"))}" --with textual"""
    # else:
    #     executable = f"""--with "{STACKOPS_VERSION},textual" """
    # exit_then_run_shell_script(f"""uv run {executable} {path}""")
    def func():
        from stackops.scripts.python.graph.visualize.helpers_navigator.devops_navigator import main as main_devops_navigator
        main_devops_navigator()
    from stackops.utils.code import get_shell_script_running_lambda_function, exit_then_run_shell_script
    if Path.home().joinpath("code", "stackops").exists():
        uv_with = ["textual"]
        uv_project_dir = str(Path.home().joinpath("code/stackops"))
    else:
        uv_with = [STACKOPS_VERSION, "textual"]
        uv_project_dir = None
    shell_script, _pyfile = get_shell_script_running_lambda_function(lambda: func(),
            uv_with=uv_with, uv_project_dir=uv_project_dir)
    exit_then_run_shell_script(str(shell_script), strict=False)


def search(
    graph_path: Annotated[Path | None, typer.Option("--graph-path", "-g", help="Path to cli_graph.json")] = None,
    show_json: Annotated[
        bool,
        typer.Option("--show-json", help="Print the selected cli_graph.json entry instead of running '<command> --help'."),
    ] = False,
) -> None:
    """🔎 Search cli_graph.json entries and run --help for the selected command or group."""
    def func(graph_path_str: str | None, show_json: bool) -> None:
        from stackops.scripts.python.graph.visualize.graph_paths import DEFAULT_GRAPH_PATH
        from stackops.scripts.python.graph.visualize.cli_graph_search import search_cli_graph

        graph_file = Path(graph_path_str) if graph_path_str else DEFAULT_GRAPH_PATH
        return_code = search_cli_graph(graph_path=graph_file, show_json=show_json)
        if return_code != 0:
            raise typer.Exit(code=return_code)
            

    from stackops.utils.ssh_utils.abc import STACKOPS_VERSION
    from stackops.utils.code import get_shell_script_running_lambda_function, exit_then_run_shell_script

    if Path.home().joinpath("code", "stackops").exists():
        uv_with = []
        uv_project_dir = str(Path.home().joinpath("code/stackops"))
    else:
        uv_with = [STACKOPS_VERSION]
        uv_project_dir = None
    shell_script, _pyfile = get_shell_script_running_lambda_function(
        lambda: func(graph_path_str=str(graph_path) if graph_path else None, show_json=show_json),
        uv_with=uv_with,
        uv_project_dir=uv_project_dir,
    )
    exit_then_run_shell_script(str(shell_script), strict=False)


def get_app() -> typer.Typer:
    cli_app = typer.Typer(
        help="🧭 <g> Visualize the StackOps CLI graph in multiple formats.",
        no_args_is_help=True,
        add_help_option=True,
        add_completion=False,
    )
    cli_app.command(name="search", no_args_is_help=False, help="🔎 <s> Search CLI graph entries and run the selected command help.")(search)
    cli_app.command(name="s", no_args_is_help=False, help="Search CLI graph entries and run the selected command help.", hidden=True)(search)
    cli_app.command(name="tree", no_args_is_help=False, help="🌳 <t> Render a rich tree view in the terminal.")(tree)
    cli_app.command(name="t", no_args_is_help=False, help="Render a rich tree view in the terminal.", hidden=True)(tree)
    cli_app.command(name="dot", no_args_is_help=False, help="🧩 <d> Export the graph as Graphviz DOT.")(dot)
    cli_app.command(name="d", no_args_is_help=False, help="Export the graph as Graphviz DOT.", hidden=True)(dot)
    cli_app.command(name="view", no_args_is_help=False, help="📊 <v> Render a Plotly hierarchy chart.")(chart)
    cli_app.command(name="v", no_args_is_help=False, help="Render a Plotly hierarchy chart.", hidden=True)(chart)
    cli_app.command(name="tui", no_args_is_help=False, help="📚 <u> NAVIGATE command structure with TUI")(navigate)
    cli_app.command(name="u", no_args_is_help=False, help="NAVIGATE command structure with TUI", hidden=True)(navigate)
    return cli_app


def main() -> None:
    app = get_app()
    app()


if __name__ == "__main__":
    main()
