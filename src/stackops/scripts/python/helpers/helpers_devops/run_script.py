import typer
from pathlib import Path
from typing import Annotated
from typer._completion_classes import completion_init
from typer.completion import install_callback, show_callback

from stackops.scripts.python.helpers.helpers_search.script_help import SCRIPT_SOURCE


def _quote_script_arg_posix(arg: str) -> str:
    import shlex
    return shlex.quote(arg)


def _quote_script_arg_powershell(arg: str) -> str:
    return "'" + arg.replace("'", "''") + "'"


def _quote_script_args(args: list[str]) -> str:
    import platform
    import shlex
    match platform.system():
        case "Windows":
            return " ".join(_quote_script_arg_powershell(arg) for arg in args)
        case _:
            return shlex.join(args)


def _append_forwarded_args(shell_script: str, forwarded_args: list[str]) -> str:
    if len(forwarded_args) == 0:
        return shell_script
    return f"{shell_script.rstrip()} {_quote_script_args(args=forwarded_args)}"


def _get_shell_script_invoking_file(
    script_path: Path,
    forwarded_args: list[str],
    *,
    run_in_subprocess: bool,
) -> str:
    import platform
    quoted_args = _quote_script_args(args=forwarded_args)
    script_suffix = script_path.suffix.casefold()
    match platform.system():
        case "Windows":
            quoted_script_path = _quote_script_arg_powershell(str(script_path))
            if run_in_subprocess and script_suffix == ".ps1":
                command_parts = [
                    "&",
                    "((Get-Process -Id $PID).Path)",
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    quoted_script_path,
                ]
            elif run_in_subprocess and script_suffix == ".sh":
                command_parts = ["bash", "--", quoted_script_path]
            else:
                command_parts = ["&", quoted_script_path]
        case "Linux" | "Darwin":
            quoted_script_path = _quote_script_arg_posix(str(script_path))
            if script_suffix == ".ps1":
                command_parts = ["pwsh", "-NoLogo", "-NoProfile", "-File", quoted_script_path]
            elif run_in_subprocess:
                command_parts = ["bash", "--", quoted_script_path]
            else:
                command_parts = ["source", quoted_script_path]
        case platform_name:
            raise NotImplementedError(f"Platform {platform_name} not supported.")
    if quoted_args != "":
        command_parts.append(quoted_args)
    return " ".join(command_parts)


def run_py_script(
    *,
    ctx: typer.Context,
    name: str,
    source: SCRIPT_SOURCE,
    interactive: bool,
    command: bool,
    run_in_subprocess: bool,
    forwarded_args: list[str],
) -> None:
    if command:
        if not name:
            typer.echo("❌ ERROR: You must provide a command to run when using --command.")
            raise typer.Exit(code=1)
        from stackops.utils.code import exit_then_run_shell_script

        exit_then_run_shell_script(script=_append_forwarded_args(shell_script=name, forwarded_args=forwarded_args), strict=False)
        return
    from stackops.scripts.python.helpers.helpers_devops.script_resolution import resolve_script

    target_file = resolve_script(ctx=ctx, name=name, source=source, interactive=interactive, allow_dynamic=True)
    typer.echo(typer.style(f"✅ Found script at: {target_file}", fg=typer.colors.GREEN))
    if target_file.suffix == ".py":
        from stackops.utils.code import get_uv_command_executing_python_file, exit_then_run_shell_script
        shell_script = get_uv_command_executing_python_file(python_file=str(target_file), uv_project_dir=None, uv_with=None, prepend_print=False)
        shell_script = _append_forwarded_args(shell_script=shell_script, forwarded_args=forwarded_args)
        exit_then_run_shell_script(script=shell_script)
    else:
        from stackops.utils.code import exit_then_run_shell_script
        shell_script = _get_shell_script_invoking_file(
            script_path=target_file,
            forwarded_args=forwarded_args,
            run_in_subprocess=run_in_subprocess,
        )
        exit_then_run_shell_script(script=shell_script, strict=True)


def copy_script_to_local(ctx: typer.Context,
                         name: Annotated[
                             str,
                             typer.Argument(help="Name of the dynamic script to copy, e.g., 'system_compute_analyzer' for system_compute_analyzer.py"),
                         ],
                         alias: Annotated[str | None, typer.Option("--alias", "-a", help="Whether to create call it a different name locally")] = None
                         ) -> None:
    """
    Copy a dynamic script stored in stackops/jobs/scripts_dynamic to the local machine.
    """
    url = f"""https://raw.githubusercontent.com/thisismygitrepo/stackops/refs/heads/main/src/stackops/jobs/scripts_dynamic/{name}.py"""
    import requests
    response = requests.get(url, timeout=30)
    if response.status_code != 200:
        typer.echo(ctx.get_help())
        typer.echo()
        typer.echo(typer.style(f"❌ ERROR: Could not fetch script '{name}.py' from repository. Status Code: {response.status_code}", fg=typer.colors.RED, bold=True))
        raise typer.Exit(code=1)
    script_content = response.text
    from stackops.utils.source_of_truth import CONFIG_ROOT
    local_path = CONFIG_ROOT.joinpath(f"scripts_python/{alias or name}.py")
    local_path.write_text(script_content, encoding="utf-8")
    typer.echo(typer.style(f"✅ Script '{name}.py' has been copied to '{local_path}'.", fg=typer.colors.GREEN))


def _run_system_compute_analyzer(
    _install_completion: Annotated[
        bool, typer.Option("--install-completion", "-I", callback=install_callback, expose_value=False, help="Install completion for the current shell.")
    ] = False,
    _show_completion: Annotated[
        bool, typer.Option("--show-completion", "-S", callback=show_callback, expose_value=False, help="Show completion for the current shell, to copy it or customize the installation.")
    ] = False,
) -> None:
    from stackops.jobs.scripts_dynamic import system_compute_analyzer

    system_compute_analyzer.main()


def get_app() -> typer.Typer:
    completion_init()
    app = typer.Typer(
        name="dynamic-scripts",
        help="Helper to run dynamic scripts stored in stackops/jobs/scripts_dynamic",
        no_args_is_help=True,
        add_completion=False,
        context_settings={"help_option_names": ["-h", "--help"]},
    )
    app.command(name="system-compute-analyzer")(_run_system_compute_analyzer)
    return app
