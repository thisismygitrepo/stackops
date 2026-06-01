"""Fast-loading CLI entry point using lazy imports.

Submodules are only imported when their commands are actually invoked, not at startup.
This makes `stackops --help` much faster by avoiding loading heavy dependencies.
"""
from collections.abc import Callable
from typing import Annotated

import typer
from stackops.scripts.python.enums import BACKENDS_LOOSE


def _run_nested_app(ctx: typer.Context, app_factory: Callable[[], typer.Typer]) -> None:
    nested_result: object = app_factory()(ctx.args, standalone_mode=not ctx.args)
    if isinstance(nested_result, int):
        raise typer.Exit(code=nested_result)


def fire(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Path to the Python file to run")] = ".",
    function: Annotated[str | None, typer.Argument(help="Function to run")] = None,
    ve: Annotated[str, typer.Option("--ve", "-v", help="Virtual environment name")] = "",
    cmd: Annotated[bool, typer.Option("--cmd", "-B", help="Create a cmd fire command to launch the job asynchronously")] = False,
    debug: Annotated[bool, typer.Option("--debug", "-d", help="Enable debug mode")] = False,
    choose_function: Annotated[bool, typer.Option("--choose-function", "-c", help="Choose function interactively")] = False,
    loop: Annotated[bool, typer.Option("--loop", "-l", help="Infinite recursion (runs again after completion/interruption)")] = False,

    interactive: Annotated[bool, typer.Option("--interactive", "-i", help="Whether to run the job interactively using IPython")] = False,
    jupyter: Annotated[bool, typer.Option("--jupyter", "-j", help="Open in a jupyter notebook")] = False,
    marimo: Annotated[bool, typer.Option("--marimo", "-M", help="Open in a marimo notebook")] = False,
    streamlit: Annotated[bool, typer.Option("--streamlit", "-S", help="Run as streamlit app")] = False,

    module: Annotated[bool, typer.Option("--module", "-m", help="Launch the main file")] = False,
    script: Annotated[bool, typer.Option("--script", "-s", help="Launch as a script without fire")] = False,
    optimized: Annotated[bool, typer.Option("--optimized", "-O", help="Run the optimized version of the function")] = False,
    root_repo: Annotated[bool, typer.Option("--root-repo", "-r", help="Resolve and search from the repository root")] = False,
    remote: Annotated[bool, typer.Option("--remote", "-R", help="Launch on a remote machine")] = False,
    holdDirectory: Annotated[bool, typer.Option("--holdDirectory", "-D", help="Hold current directory and avoid cd'ing to the script directory")] = False,
    PathExport: Annotated[bool, typer.Option("--PathExport", "-P", help="Augment the PYTHONPATH with repo root")] = False,
    git_pull: Annotated[bool, typer.Option("--git-pull", "-g", help="Start by pulling the git repo")] = False,
    watch: Annotated[bool, typer.Option("--watch", "-w", help="Watch the file for changes")] = False,
) -> None:
    """Fire and manage jobs."""
    from stackops.scripts.python.fire_jobs import fire as fire_impl
    fire_impl(ctx=ctx, path=path, function=function, ve=ve, cmd=cmd, interactive=interactive, debug=debug,
              choose_function=choose_function, loop=loop, jupyter=jupyter, marimo=marimo, module=module,
              script=script, optimized=optimized, root_repo=root_repo,
              remote=remote, streamlit=streamlit, holdDirectory=holdDirectory,
              PathExport=PathExport, git_pull=git_pull, watch=watch)


def croshell(
    path: Annotated[str | None, typer.Argument(help="path of file to read.")] = None,
    project_path: Annotated[str | None, typer.Option("--project", "-p", help="specify uv project to use")] = None,
    uv_with: Annotated[str | None, typer.Option("--uv-with", "-w", help="specify uv with packages to use")] = None,
    backend: Annotated[BACKENDS_LOOSE, typer.Option("--backend", "-b", help="specify the backend to use")] = "ipython",
    interactive: Annotated[bool, typer.Option("--interactive", "-i", help="select the backend interactively")] = False,
    profile: Annotated[str | None, typer.Option("--profile", "-r", help="ipython profile to use, defaults to default profile.")] = None,
    stackops_project: Annotated[bool, typer.Option("--self", "-s", help="specify stackops project to use.")] = False,
    frozen: Annotated[bool, typer.Option("--frozen", "-f", help="freeze the environment (no package changes allowed)")] = False,
) -> None:
    """Cross-shell command execution."""
    from stackops.scripts.python.croshell import croshell as croshell_impl
    croshell_impl(
        path=path,
        project_path=project_path,
        uv_with=uv_with,
        backend=backend,
        interactive=interactive,
        profile=profile,
        stackops_project=stackops_project,
        frozen=frozen,
    )


def devops(ctx: typer.Context) -> None:
    """<d> DevOps related commands."""
    from stackops.scripts.python.devops import get_app as get_app_devops

    _run_nested_app(ctx, get_app_devops)


def cloud(ctx: typer.Context) -> None:
    """<c> Cloud management commands."""
    from stackops.scripts.python.cloud import get_app as get_app_cloud

    _run_nested_app(ctx, get_app_cloud)


def terminal(ctx: typer.Context) -> None:
    """<t> Terminal and layout management."""
    from stackops.scripts.python.terminal import get_app as get_app_terminal

    _run_nested_app(ctx, get_app_terminal)


def agents(ctx: typer.Context) -> None:
    """<a> 🤖 AI Agents management commands."""
    from stackops.scripts.python.agents import get_app as get_app_agents

    _run_nested_app(ctx, get_app_agents)


def utils(ctx: typer.Context) -> None:
    """<u> Utility commands."""
    from stackops.scripts.python.utils import get_app as get_app_utils

    _run_nested_app(ctx, get_app_utils)


def seek(ctx: typer.Context) -> None:
    """<s> Search across files, text matches, and code symbols."""
    from stackops.scripts.python.seek import get_app as get_app_seek

    _run_nested_app(ctx, get_app_seek)



def get_app() -> typer.Typer:
    app = typer.Typer(help="StackOps CLI - Manage your machine configurations and workflows", no_args_is_help=True, add_help_option=True, add_completion=False)

    ctx_settings: dict[str, object] = {"allow_extra_args": True, "allow_interspersed_args": True, "ignore_unknown_options": True, "help_option_names": []}

    app.command(name="devops", help="<d> DevOps related commands", context_settings=ctx_settings)(devops)
    app.command(name="d", hidden=True, context_settings=ctx_settings)(devops)
    app.command(name="cloud", help="<c> Cloud management commands", context_settings=ctx_settings)(cloud)
    app.command(name="c", hidden=True, context_settings=ctx_settings)(cloud)
    app.command(name="terminal", help="<t> Terminal and layout management", context_settings=ctx_settings)(terminal)
    app.command(name="t", hidden=True, context_settings=ctx_settings)(terminal)
    app.command(name="agents", help="<a> 🤖 AI Agents management commands", context_settings=ctx_settings)(agents)
    app.command(name="a", hidden=True, context_settings=ctx_settings)(agents)
    app.command(name="utils", help="<u> Utility commands", context_settings=ctx_settings)(utils)
    app.command(name="u", hidden=True, context_settings=ctx_settings)(utils)
    app.command(name="seek", help="<s> Search across files, text matches, and code symbols", context_settings=ctx_settings)(seek)
    app.command(name="s", hidden=True, context_settings=ctx_settings)(seek)

    app.command(name="fire", help="<f> Fire and manage jobs", no_args_is_help=False, context_settings={"allow_extra_args": True, "allow_interspersed_args": False})(fire)
    app.command(name="f", hidden=True, no_args_is_help=False, context_settings={"allow_extra_args": True, "allow_interspersed_args": False})(fire)
    app.command("croshell", no_args_is_help=False, help="<r> Cross-shell command execution")(croshell)
    app.command("r", no_args_is_help=False, hidden=True)(croshell)

    return app


def main() -> None:
    app = get_app()
    app()


if __name__ == "__main__":
    main()
