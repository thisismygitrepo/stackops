from typing import Annotated

import typer

from stackops.scripts.python.helpers.helpers_fire_command.fire_jobs_args_helper import FireJobArgs, parse_fire_args_from_context
from stackops.utils.cli_utils.alias_markers import apply_alias_markers


def _launch_job(ctx: typer.Context, args: FireJobArgs) -> None:
    from stackops.scripts.python.helpers.helpers_fire_command.fire_jobs_impl import route

    fire_args = parse_fire_args_from_context(ctx)
    try:
        route(args, fire_args)
    except Exception as error:
        typer.echo(f"""❌ Fire error: {error}""", err=True)
        raise typer.Exit(code=1) from error


def run(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="File, directory, or partial script name to run")] = ".",
    function: Annotated[str | None, typer.Argument(help="Python function to run; pass its arguments after --")] = None,
    frozen: Annotated[bool, typer.Option("--frozen", "-F", help="Use the existing uv lockfile without updating it")] = False,
    cmd: Annotated[bool, typer.Option("--cmd", "-B", help="Launch asynchronously in a Windows cmd window")] = False,
    interactive: Annotated[bool, typer.Option("--interactive", "-i", help="Run interactively using IPython")] = False,
    debug: Annotated[bool, typer.Option("--debug", "-d", help="Run with the Python debugger")] = False,
    choose_function: Annotated[bool, typer.Option("--choose-function", "-c", help="Choose a function or shell lines interactively")] = False,
    loop: Annotated[bool, typer.Option("--loop", "-l", help="Rerun after completion or interruption")] = False,
    module: Annotated[bool, typer.Option("--module", "-m", help="Run the selected Python file as a module")] = False,
    script: Annotated[bool, typer.Option("--script", "-s", help="Generate a script that imports and calls the function")] = False,
    optimized: Annotated[bool, typer.Option("--optimized", "-O", help="Run Python with -OO optimization")] = False,
    jit: Annotated[bool, typer.Option("--jit", "-J", help="Enable CPython experimental JIT with PYTHON_JIT=1")] = False,
    root_repo: Annotated[bool, typer.Option("--root-repo", "-r", help="Resolve and search from the repository root")] = False,
    path_export: Annotated[bool, typer.Option("--path-export", "-P", help="Add the repository root to PYTHONPATH")] = False,
    git_pull: Annotated[bool, typer.Option("--git-pull", "-g", help="Pull the git repository before running")] = False,
    watch: Annotated[bool, typer.Option("--watch", "-w", help="Restart when source files change")] = False,
) -> None:
    args = FireJobArgs(
        mode="run", path=path, function=function, frozen=frozen, cmd=cmd, interactive=interactive,
        debug=debug, choose_function=choose_function, loop=loop, module=module, script=script,
        optimized=optimized, jit=jit, root_repo=root_repo, path_export=path_export,
        git_pull=git_pull, watch=watch,
    )
    _launch_job(ctx, args)


def streamlit(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Python file, directory, or partial app name")] = ".",
    frozen: Annotated[bool, typer.Option("--frozen", "-F", help="Use the existing uv lockfile without updating it")] = False,
    jit: Annotated[bool, typer.Option("--jit", "-J", help="Enable CPython experimental JIT with PYTHON_JIT=1")] = False,
    root_repo: Annotated[bool, typer.Option("--root-repo", "-r", help="Resolve and search from the repository root")] = False,
    hold_directory: Annotated[bool, typer.Option("--hold-directory", "-D", help="Keep the current directory when launching the app")] = False,
    path_export: Annotated[bool, typer.Option("--path-export", "-P", help="Add the repository root to PYTHONPATH")] = False,
    git_pull: Annotated[bool, typer.Option("--git-pull", "-g", help="Pull the git repository before launching")] = False,
    watch: Annotated[bool, typer.Option("--watch", "-w", help="Restart when source files change")] = False,
) -> None:
    args = FireJobArgs(
        mode="streamlit", path=path, frozen=frozen, jit=jit, root_repo=root_repo,
        hold_directory=hold_directory, path_export=path_export, git_pull=git_pull, watch=watch,
    )
    _launch_job(ctx, args)


def jupyter(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Python file, notebook, directory, or partial filename")] = ".",
    frozen: Annotated[bool, typer.Option("--frozen", "-F", help="Use the existing uv lockfile without updating it")] = False,
    jit: Annotated[bool, typer.Option("--jit", "-J", help="Enable CPython experimental JIT with PYTHON_JIT=1")] = False,
    root_repo: Annotated[bool, typer.Option("--root-repo", "-r", help="Resolve and search from the repository root")] = False,
    path_export: Annotated[bool, typer.Option("--path-export", "-P", help="Add the repository root to PYTHONPATH")] = False,
    git_pull: Annotated[bool, typer.Option("--git-pull", "-g", help="Pull the git repository before launching")] = False,
    watch: Annotated[bool, typer.Option("--watch", "-w", help="Restart when source files change")] = False,
) -> None:
    args = FireJobArgs(
        mode="jupyter", path=path, frozen=frozen, jit=jit, root_repo=root_repo,
        path_export=path_export, git_pull=git_pull, watch=watch,
    )
    _launch_job(ctx, args)


def marimo(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Python file, directory, or partial notebook name")] = ".",
    frozen: Annotated[bool, typer.Option("--frozen", "-F", help="Use the existing uv lockfile without updating it")] = False,
    jit: Annotated[bool, typer.Option("--jit", "-J", help="Enable CPython experimental JIT with PYTHON_JIT=1")] = False,
    root_repo: Annotated[bool, typer.Option("--root-repo", "-r", help="Resolve and search from the repository root")] = False,
) -> None:
    args = FireJobArgs(mode="marimo", path=path, frozen=frozen, jit=jit, root_repo=root_repo)
    _launch_job(ctx, args)


def get_app() -> typer.Typer:
    app = typer.Typer(
        help="🔥 Run scripts, apps, and notebooks", no_args_is_help=True, add_completion=False,
        context_settings={"help_option_names": ["-h", "--help"]},
    )
    run_context = {"allow_extra_args": True, "allow_interspersed_args": True}
    app.command(name="run", help="🚀 <r> Run a script or Python function", context_settings=run_context)(run)
    app.command(name="r", hidden=True, context_settings=run_context)(run)
    app.command(name="streamlit", help="📊 <s> Launch a Streamlit app")(streamlit)
    app.command(name="s", hidden=True)(streamlit)
    app.command(name="jupyter", help="📓 <j> Open a file in JupyterLab")(jupyter)
    app.command(name="j", hidden=True)(jupyter)
    app.command(name="marimo", help="📒 <m> Edit a Marimo notebook")(marimo)
    app.command(name="m", hidden=True)(marimo)
    return apply_alias_markers(app)


def main() -> None:
    app = get_app()
    app()


if __name__ == "__main__":
    main()
