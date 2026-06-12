

"""run python/shell scripts from pre-defined directorys, or, run command/file in the stackops environment

Recursively Searched Predefined Directories:


* 'private' : stackops.utils.source_of_truth.SCRIPTS_ROOT_PRIVATE

* 'repo'    : <current-git-repo>/.stackops/scripts

* 'public'  : $HOME/.config/stackops/scripts

* 'library' : $STACKOPS_LIBRARY_ROOT/jobs/scripts

* 'dynamic' : fetched from GitHub repository on the fly (relies on latest commit, rather than the version currently installed)

"""


import shlex
import typer
import platform
from pathlib import Path
from typing import Annotated

from stackops.scripts.python.helpers.helpers_search.script_help import SCRIPT_SOURCE


IGNORED_SCRIPT_MATCH_DIR_NAMES: frozenset[str] = frozenset({
    "__pycache__",
    ".git",
    ".ipynb_checkpoints",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "node_modules",
})


def _quote_script_arg_posix(arg: str) -> str:
    return shlex.quote(arg)


def _quote_script_arg_powershell(arg: str) -> str:
    return "'" + arg.replace("'", "''") + "'"


def _quote_script_args(args: list[str]) -> str:
    match platform.system():
        case "Windows":
            return " ".join(_quote_script_arg_powershell(arg) for arg in args)
        case _:
            return shlex.join(args)


def _append_forwarded_args(shell_script: str, forwarded_args: list[str]) -> str:
    if len(forwarded_args) == 0:
        return shell_script
    return f"{shell_script.rstrip()} {_quote_script_args(args=forwarded_args)}"


def _get_shell_script_invoking_file(script_path: Path, forwarded_args: list[str]) -> str:
    quoted_args = _quote_script_args(args=forwarded_args)
    match platform.system():
        case "Windows":
            command_parts = ["&", _quote_script_arg_powershell(str(script_path))]
        case "Linux" | "Darwin":
            command_parts = ["source", _quote_script_arg_posix(str(script_path))]
        case platform_name:
            raise NotImplementedError(f"Platform {platform_name} not supported.")
    if quoted_args != "":
        command_parts.append(quoted_args)
    return " ".join(command_parts)


def _get_supported_script_suffixes(name: str) -> tuple[str, ...]:
    if "." in name:
        return (Path(name).suffix,)

    match platform.system():
        case "Windows":
            return (".py", ".bat", ".cmd", ".ps1")
        case "Darwin" | "Linux":
            return ("", ".py", ".sh")
        case _:
            return (".py",)


def _is_supported_script_match(file_path: Path, root: Path, supported_suffixes: frozenset[str]) -> bool:
    if not file_path.is_file() or file_path.name == "__init__.py":
        return False

    relative_parts = file_path.relative_to(root).parts
    if any(part in IGNORED_SCRIPT_MATCH_DIR_NAMES for part in relative_parts[:-1]):
        return False

    return file_path.suffix in supported_suffixes


def run_py_script(ctx: typer.Context,
                  name: Annotated[
                      str,
                      typer.Argument(
                          help="Name of script to run, e.g., 'system_compute_analyzer' for system_compute_analyzer.py, or command to execute"
                      ),
                  ] = "",
                  source: Annotated[SCRIPT_SOURCE, typer.Option("--source", "-s", help="Source to look for the script")] = "all",
                  interactive: Annotated[bool, typer.Option(..., "--interactive", "-i", help="Interactive selection of scripts to run")] = False,
                  command: Annotated[bool | None, typer.Option(..., "--command", "-c", help="Run as command")] = False,
                  list_scripts: Annotated[bool, typer.Option(..., "--list", "-l", help="List available scripts in all locations")] = False,
                  *,
                  forwarded_args: list[str],
                ) -> None:
    if command:
        if not name:
            typer.echo("❌ ERROR: You must provide a command to run when using --command.")
            raise typer.Exit(code=1)
        from stackops.utils.code import exit_then_run_shell_script

        exit_then_run_shell_script(script=_append_forwarded_args(shell_script=name, forwarded_args=forwarded_args), strict=False)
        return
    if list_scripts:
        from stackops.scripts.python.helpers.helpers_search.script_help import list_available_scripts
        list_available_scripts(source=source)
        return
    if not interactive and not name:
        typer.echo("❌ ERROR: You must provide a script name or use --interactive option to select a script.")
        raise typer.Exit(code=1)
    target_file: Path | None = None
    if source in ["dynamic", "d"]:
        # src/stackops/jobs/scripts_dynamic/system_compute_analyzer.py
        if "." in name:
            resolved_names: list[str] = [name]
        else:
            resolved_names = [f"{name}{a_suffix}" for a_suffix in [".py", ".sh", "", ".ps1", ".bat", ".cmd"]]
        urls = [f"""https://raw.githubusercontent.com/thisismygitrepo/stackops/refs/heads/main/src/stackops/jobs/scripts_dynamic/{a_resolved_name}""" for a_resolved_name in resolved_names]
        for a_url in urls:
            try:
                print(f"Fetching temporary script from {a_url} ...")
                import requests
                response = requests.get(a_url, timeout=30)
                if response.status_code != 200:
                    print(f"❌ ERROR: Could not fetch script '{name}.py' from repository. Status Code: {response.status_code}")
                    raise RuntimeError(f"Could not fetch script '{name}.py' from repository.")
                script_content = response.text
                target_file = Path.home().joinpath("tmp_results", "tmp_scripts", "python", f"{name}.py")
                target_file.parent.mkdir(parents=True, exist_ok=True)
                target_file.write_text(script_content, encoding="utf-8")
            except Exception as _e:
                pass


    if target_file is None and Path(name).is_file():
        direct_target_file = Path(name).resolve()
        if direct_target_file.suffix in [".py", ".sh", ".ps1", ".bat", ".cmd", ""]:
            target_file = direct_target_file
        else:
            print(f"❌ Error: File '{name}' is not a recognized script type. Supported types are {'.py', '.sh', '.ps1', '.bat', '.cmd', ''}.")
            raise typer.Exit(code=1)

    from stackops.utils.repos.stackops_paths import current_repo_stackops_path, require_current_repo_stackops_path
    from stackops.utils.source_of_truth import SCRIPTS_ROOT_PRIVATE, SCRIPTS_ROOT_PUBLIC, SCRIPTS_ROOT_LIBRARY

    roots: list[Path] = []
    match source:
        case "all" | "a":
            roots = [SCRIPTS_ROOT_PRIVATE, SCRIPTS_ROOT_PUBLIC, SCRIPTS_ROOT_LIBRARY]
            repo_scripts = current_repo_stackops_path(path_kind="scripts")
            if repo_scripts is not None:
                roots = [repo_scripts] + roots
        case "repo" | "r":
            roots = [require_current_repo_stackops_path(path_kind="scripts")]
        case "private" | "p":
            roots = [SCRIPTS_ROOT_PRIVATE]
        case "public" | "b":
            roots = [SCRIPTS_ROOT_PUBLIC]
        case "library" | "l":
            roots = [SCRIPTS_ROOT_LIBRARY]
        case "dynamic" | "d":
            roots = []

    suffixes = _get_supported_script_suffixes(name=name)
    exact_names = [name] if "." in name else [f"{name}{a_suffix}" for a_suffix in suffixes]
    supported_suffixes = frozenset(suffixes)

    # Finding target file
    potential_matches: list[Path] = []
    seen_matches: set[Path] = set()
    if target_file is None:
        for a_root in roots:
            for exact_name in exact_names:
                exact_path = a_root.joinpath(exact_name)
                if _is_supported_script_match(file_path=exact_path, root=a_root, supported_suffixes=supported_suffixes):
                    target_file = exact_path
                    break  # perfect match
            if target_file is not None:
                break
            for a_file in sorted(a_root.rglob(f"*{name}*")):
                if not _is_supported_script_match(file_path=a_file, root=a_root, supported_suffixes=supported_suffixes):
                    continue
                if a_file in seen_matches:
                    continue
                potential_matches.append(a_file)
                seen_matches.add(a_file)

    if target_file is None:
        if len(potential_matches) == 1:
            target_file = potential_matches[0]
        elif len(potential_matches) == 0:
            typer.echo(ctx.get_help())
            typer.echo()
            typer.echo(typer.style(f"❌ ERROR: Could not find script '{name}'.", fg=typer.colors.RED, bold=True))
            typer.echo("Searched in:")
            for r in roots:
                typer.echo(f"  - {r}")
            raise typer.Exit(code=1)
        else:
            typer.echo(typer.style(f"❌ ERROR: Found {len(potential_matches)} scripts matching '{name}'.", fg=typer.colors.RED, bold=True))
            for candidate in potential_matches:
                typer.echo(f"  - {candidate}")
            if not interactive:
                typer.echo("Re-run with --interactive to choose one explicitly.")
                raise typer.Exit(code=1)
            from stackops.utils.options_utils.options import choose_from_options
            options = [str(p) for p in potential_matches]
            chosen_file_part = choose_from_options(options, multi=False, msg="Select the script to run:", tv=True, preview="bat")
            if chosen_file_part is None:
                typer.echo(typer.style("❌ Selection cancelled.", fg=typer.colors.YELLOW))
                raise typer.Exit(code=1)
            target_file = Path(chosen_file_part)

    typer.echo(typer.style(f"✅ Found script at: {target_file}", fg=typer.colors.GREEN))
    if target_file.suffix == ".py":
        from stackops.utils.code import get_uv_command_executing_python_file, exit_then_run_shell_script
        shell_script = get_uv_command_executing_python_file(python_file=str(target_file), uv_project_dir=None, uv_with=None, prepend_print=False)
        shell_script = _append_forwarded_args(shell_script=shell_script, forwarded_args=forwarded_args)
        exit_then_run_shell_script(script=shell_script)
    else:
        from stackops.utils.code import exit_then_run_shell_script
        shell_script = _get_shell_script_invoking_file(script_path=target_file, forwarded_args=forwarded_args)
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


def _run_system_compute_analyzer() -> None:
    from stackops.jobs.scripts_dynamic import system_compute_analyzer

    system_compute_analyzer.main()


def get_app() -> typer.Typer:
    app = typer.Typer(
        name="dynamic-scripts",
        help="Helper to run dynamic scripts stored in stackops/jobs/scripts_dynamic",
        no_args_is_help=True,
    )
    app.command(name="system-compute-analyzer")(_run_system_compute_analyzer)
    return app
