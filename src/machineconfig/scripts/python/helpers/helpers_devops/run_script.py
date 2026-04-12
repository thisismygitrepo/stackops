

"""run python/shell scripts from pre-defined directorys, or, run command/file in the machineconfig environment

Recursively Searched Predefined Directories:


* 'private' : $HOME/dotfiles/scripts

* 'public'  : $HOME/.config/machineconfig/scripts

* 'library' : $MACHINECONFIG_LIBRARY_ROOT/jobs/scripts

* 'dynamic' : fetched from GitHub repository on the fly (relies on latest commit, rather than the version currently installed)

* 'custom'  : custom directories from comma separated entry 'scripts' under 'general' section @ ~/dotfiles/machineconfig/defaults.ini

"""


import typer
import platform
from pathlib import Path
from typing import Annotated, Literal


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
                  name: Annotated[str, typer.Argument(help="Name of script to run, e.g., 'a' for a.py, or command to execute")] = "",
                  where: Annotated[Literal["all", "a", "private", "p", "public", "b", "library", "l", "dynamic", "d", "custom", "c"], typer.Option("--where", "-w", help="Where to look for the script")] = "all",
                  interactive: Annotated[bool, typer.Option(..., "--interactive", "-i", help="Interactive selection of scripts to run")] = False,
                  command: Annotated[bool | None, typer.Option(..., "--command", "-c", help="Run as command")] = False,
                  list_scripts: Annotated[bool, typer.Option(..., "--list", "-l", help="List available scripts in all locations")] = False,
                ) -> None:
    if command:
        from machineconfig.utils.code import exit_then_run_shell_script

        exit_then_run_shell_script(script=name, strict=False)
        return
    if list_scripts:
        from machineconfig.scripts.python.helpers.helpers_search.script_help import list_available_scripts
        list_available_scripts(where=where)
        return
    if not interactive and not name:
        typer.echo("❌ ERROR: You must provide a script name or use --interactive option to select a script.")
        raise typer.Exit(code=1)
    target_file: Path | None = None
    if where in ["dynamic", "d"]:
        # src/machineconfig/jobs/scripts/python_scripts/a.py
        if "." in name:
            resolved_names: list[str] = [name]
        else:
            resolved_names = [f"{name}{a_suffix}" for a_suffix in [".py", ".sh", "", ".ps1", ".bat", ".cmd"]]
        urls = [f"""https://raw.githubusercontent.com/thisismygitrepo/machineconfig/refs/heads/main/src/machineconfig/jobs/scripts_dynamic/{a_resolved_name}""" for a_resolved_name in resolved_names]
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
        if name.endswith(".py"):
            import machineconfig
            import subprocess
            import sys
            subprocess.run([sys.executable, name], cwd=machineconfig.__path__[0], check=True)
            return
        if Path(name).suffix in [".sh", ".ps1", ".bat", ".cmd", ""]:
            target_file = Path(name)
        else:
            print(f"❌ Error: File '{name}' is not a recognized script type. Supported types are {'.py', '.sh', '.ps1', '.bat', '.cmd', ''}.")
            raise typer.Exit(code=1)

    from machineconfig.utils.source_of_truth import DEFAULTS_PATH, SCRIPTS_ROOT_PRIVATE, SCRIPTS_ROOT_PUBLIC, SCRIPTS_ROOT_LIBRARY

    def get_custom_roots() -> list[Path]:
        custom_roots: list[Path] = []
        if DEFAULTS_PATH.is_file():
            from configparser import ConfigParser
            config = ConfigParser()
            config.read(DEFAULTS_PATH)
            if config.has_section("general") and config.has_option("general", "scripts"):
                custom_dirs = config.get("general", "scripts").split(",")
                for custom_dir in custom_dirs:
                    custom_path = Path(custom_dir.strip()).expanduser().resolve()
                    if custom_path.is_dir():
                        custom_roots.append(custom_path)
        return custom_roots

    roots: list[Path] = []
    match where:
        case "all" | "a":
            roots = [SCRIPTS_ROOT_PRIVATE, SCRIPTS_ROOT_PUBLIC, SCRIPTS_ROOT_LIBRARY] + get_custom_roots()
        case "private" | "p":
            roots = [SCRIPTS_ROOT_PRIVATE]
        case "public" | "b":
            roots = [SCRIPTS_ROOT_PUBLIC]
        case "library" | "l":
            roots = [SCRIPTS_ROOT_LIBRARY]
        case "dynamic" | "d":
            roots = []
        case "custom" | "c":
            roots = get_custom_roots()

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
            typer.echo(typer.style(f"Warning: Could not find script '{name}'. Checked {len(potential_matches)} candidate files, trying interactively:", fg=typer.colors.YELLOW))
            from machineconfig.utils.options import choose_from_options
            options = [str(p) for p in potential_matches]
            chosen_file_part = choose_from_options(options, multi=False, msg="Select the script to run:", tv=True, preview="bat")
            if chosen_file_part is None:
                typer.echo(typer.style("❌ Selection cancelled.", fg=typer.colors.YELLOW))
                raise typer.Exit(code=1)
            target_file = Path(chosen_file_part)

    typer.echo(typer.style(f"✅ Found script at: {target_file}", fg=typer.colors.GREEN))
    if target_file.suffix == ".py":
        from machineconfig.utils.code import get_uv_command_executing_python_file, exit_then_run_shell_script
        shell_script = get_uv_command_executing_python_file(python_file=str(target_file), uv_project_dir=None, uv_with=None, prepend_print=False)
        exit_then_run_shell_script(script=shell_script)
    else:
        from machineconfig.utils.code import exit_then_run_shell_file
        exit_then_run_shell_file(script_path=str(target_file), strict=True)


def copy_script_to_local(ctx: typer.Context,
                         name: Annotated[str, typer.Argument(help="Name of the temporary python script to copy, e.g., 'a' for a.py")],
                         alias: Annotated[str | None, typer.Option("--alias", "-a", help="Whether to create call it a different name locally")] = None
                         ) -> None:
    """
    Copy a temporary python script stored in machineconfig/scripts/python/helpers/tmp_py_scripts to the local machine.
    """
    url = f"""https://raw.githubusercontent.com/thisismygitrepo/machineconfig/refs/heads/main/src/machineconfig/scripts/python/helpers/tmp_py_scripts/{name}.py"""
    import requests
    response = requests.get(url, timeout=30)
    if response.status_code != 200:
        typer.echo(ctx.get_help())
        typer.echo()
        typer.echo(typer.style(f"❌ ERROR: Could not fetch script '{name}.py' from repository. Status Code: {response.status_code}", fg=typer.colors.RED, bold=True))
        raise typer.Exit(code=1)
    script_content = response.text
    from machineconfig.utils.source_of_truth import CONFIG_ROOT
    local_path = CONFIG_ROOT.joinpath(f"scripts_python/{alias or name}.py")
    local_path.write_text(script_content, encoding="utf-8")
    typer.echo(typer.style(f"✅ Script '{name}.py' has been copied to '{local_path}'.", fg=typer.colors.GREEN))


def get_app():
    app = typer.Typer(
        name="run-tmp-script",
        help="Helper to run temporary python scripts stored in machineconfig/scripts/python/helpers/tmp_py_scripts",
        no_args_is_help=True,
    )
    from machineconfig.jobs.scripts_dynamic import a
    app.command()(a.main)
    return app
