import os
from pathlib import Path
from typing import Annotated, Literal, TypedDict, cast

import typer

from stackops.utils.ssh_utils.abc import STACKOPS_VERSION


ENV_SUMMARY_LIMIT = 96


def _truncate_text(text: str, limit: int) -> tuple[str, int]:
    length = len(text)
    if length <= limit:
        return text, 0
    return text[:limit], length - limit


def _format_env_label(env_key: str, env_value: str) -> str:
    sanitized_value = env_value.replace("\n", "\\n").replace("\t", "\\t")
    preview, remainder = _truncate_text(sanitized_value, ENV_SUMMARY_LIMIT)
    summary = preview if preview else "<empty>"
    if remainder > 0:
        summary = f"{summary}... (+{remainder} chars)"
    return f"{env_key} = {summary}"


def _format_env_preview(env_key: str, env_value: str) -> str:
    value_text = env_value if env_value else "<empty>"
    return f"{env_key}\n\n{value_text}"


def _format_path_preview(path_entry: str) -> str:
    from stackops.scripts.python.helpers.helper_env.path_manager_backend import get_directory_contents

    path_obj = Path(path_entry)
    if path_obj.exists():
        entry_type = "directory" if path_obj.is_dir() else "file"
    else:
        entry_type = "missing"
    content_lines = get_directory_contents(path_entry, max_items=30)
    contents = "\n".join(content_lines)
    return (
        f"{path_entry}\n\n"
        f"Exists: {path_obj.exists()}\n"
        f"Type: {entry_type}\n\n"
        f"{contents}"
    )


def _build_env_selection_data() -> tuple[dict[str, str], dict[str, str]]:
    options_to_preview: dict[str, str] = {}
    options_to_output: dict[str, str] = {}
    for env_key, env_value in sorted(os.environ.items(), key=lambda pair: pair[0].lower()):
        label = _format_env_label(env_key, env_value)
        options_to_preview[label] = _format_env_preview(env_key, env_value)
        options_to_output[label] = env_value
    return options_to_preview, options_to_output


def _build_path_selection_data() -> tuple[dict[str, str], dict[str, str]]:
    from stackops.scripts.python.helpers.helper_env.path_manager_backend import get_path_entries

    options_to_preview: dict[str, str] = {}
    options_to_output: dict[str, str] = {}
    for idx, path_entry in enumerate(get_path_entries(), start=1):
        path_obj = Path(path_entry)
        status = "OK" if path_obj.exists() else "MISSING"
        label = f"{idx:03d} [{status}] {path_entry}"
        options_to_preview[label] = _format_path_preview(path_entry)
        options_to_output[label] = path_entry
    return options_to_preview, options_to_output


def _choose_with_tv(which: Literal["PATH", "p", "ENV", "e"]) -> tuple[bool, str | None]:
    from stackops.utils.installer_utils.installer_locator_utils import check_tool_exists

    if not check_tool_exists("tv"):
        return False, None

    from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview

    try:
        options_to_preview: dict[str, str]
        options_to_output: dict[str, str]
        preview_size_percent: float
        if which in {"PATH", "p"}:
            options_to_preview, options_to_output = _build_path_selection_data()
            preview_size_percent = 60.0
        else:
            options_to_preview, options_to_output = _build_env_selection_data()
            preview_size_percent = 50.0

        selected_label = choose_from_dict_with_preview(
            options_to_preview_mapping=options_to_preview,
            extension="txt",
            multi=False,
            preview_size_percent=preview_size_percent,
        )
    except Exception:
        return False, None

    if selected_label is None:
        return True, None
    return True, options_to_output.get(selected_label)


def _run_textual_env(which: Literal["PATH", "p", "ENV", "e"]) -> None:
    from stackops.scripts.python.helpers import helper_env as navigator

    if which in {"PATH", "p"}:
        path = Path(navigator.__file__).resolve().parent.joinpath("path_manager_tui.py")
    else:
        path = Path(navigator.__file__).resolve().parent.joinpath("env_manager_tui.py")
    from stackops.utils.code import run_shell_script, get_uv_command_executing_python_script

    uv_with = ["textual"]
    uv_project_dir = None
    if not Path.home().joinpath("code/stackops").exists():
        uv_with.append(STACKOPS_VERSION)
    else:
        uv_project_dir = str(Path.home().joinpath("code/stackops"))
    run_shell_script(
        get_uv_command_executing_python_script(python_script=path.read_text(encoding="utf-8"), uv_with=uv_with, uv_project_dir=uv_project_dir)[0],
        display_script=True,
        clean_env=False,
    )


def tui_env(which: Annotated[Literal["PATH", "p", "ENV", "e"], typer.Argument(help="Which environment variable to display.")] = "ENV", tui: bool = False) -> None:
    """📚 Navigate PATH and environment variables."""
    if tui:
        _run_textual_env(which=which)
        return

    used_tv, selected_value = _choose_with_tv(which=which)
    if selected_value is not None:
        typer.echo(selected_value)
        return
    if used_tv:
        return

    typer.echo("tv picker unavailable. Falling back to the Textual TUI.", err=True)
    _run_textual_env(which=which)


def init_project(
    name: Annotated[str | None, typer.Option("--name", "-n", help="Name of the project.")] = None,
    tmp_dir: Annotated[bool, typer.Option("--tmp-dir", "-t", help="Use a temporary directory for the project initialization.")] = False,
    python: Annotated[
        Literal["3.11", "3.12", "3.13", "3.14"], typer.Option("--python", "-p", help="Python sub version for the uv virtual environment.")
    ] = "3.13",
    libraries: Annotated[
        str | None, typer.Option("--libraries", "-l", help="Additional packages to include in the uv virtual environment (space separated).")
    ] = None,
    group: Annotated[
        str | None, typer.Option("--group", "-g", help="group of packages names (no separation) p:plot, t:types, l:linting, i:interactive, d:data")
    ] = "p,t,l,i,d",
) -> None:
    if libraries is not None:
        packages_add_line = f"uv add {libraries}"
    else:
        packages_add_line = ""
    from pathlib import Path

    if not tmp_dir:
        repo_root = Path.cwd()
        if not (repo_root / "pyproject.toml").exists():
            typer.echo(f"❌ Error: pyproject.toml not found in {repo_root}", err=True)
            raise typer.Exit(code=1)
        starting_code = ""
        agents_line = ""
    else:
        agents_line = """agents make-config"""
        if name is not None:
            from stackops.utils.accessories import randstr

            repo_root = Path.home().joinpath(f"tmp_results/tmp_projects/{name}")
        else:
            from stackops.utils.accessories import randstr

            repo_root = Path.home().joinpath(f"tmp_results/tmp_projects/{randstr(6)}")
        repo_root.mkdir(parents=True, exist_ok=True)
        print(f"Using temporary directory for project initialization: {repo_root}")
        starting_code = f"""
cd {repo_root}
uv init --python {python}
uv venv
"""
    print(f"Adding group `{group}` with common data science and plotting packages...")
    total_packages: dict[str, list[str]] = {}
    if group is not None:
        packages = group.split(",")
        if "t" in packages or "types" in packages:
            total_packages["types"] = [
                "types-python-dateutil",
                "types-pyyaml",
                "types-requests",
                "types-tqdm",
                "types-mysqlclient",
                "types-paramiko",
                "types-pytz",
                "types-sqlalchemy",
                "types-toml",
                "types-urllib3",
            ]
        if "l" in packages:
            total_packages["linting"] = ["mypy", "pyright", "ruff", "pylint", "pyrefly", "cleanpy", "ipdb", "pudb"]
        if "i" in packages:
            total_packages["interactive"] = ["ipython", "ipykernel", "jupyterlab", "nbformat", "marimo"]
        if "p" in packages:
            total_packages["plot"] = ["python-magic", "matplotlib", "plotly", "kaleido"]
        if "d" in packages:
            total_packages["data"] = ["numpy", "pandas", "polars", "duckdb-engine", "sqlalchemy", "psycopg2-binary", "pyarrow", "tqdm", "openpyxl"]
    from stackops.utils.ve import get_ve_activate_line
    groups_packages_lines = "\n".join(
        [f"uv add --group {group_name} {' '.join(packages)}" for group_name, packages in total_packages.items()]
    )   
    script = f"""
{starting_code}
{packages_add_line}
{groups_packages_lines}
{get_ve_activate_line(ve_root=str(repo_root.joinpath(".venv")))}
{agents_line}
ls
"""
    from stackops.utils.code import exit_then_run_shell_script, run_shell_script
    exit_then_run_shell_script(script)
    _ = exit_then_run_shell_script, run_shell_script
    # run_shell_script(script)
    # if tempdir:
    #     from stackops.scripts.python.ai.initai import add_ai_configs
    #     add_ai_configs(repo_root=repo_root)


def edit_file_with_hx(
    path: Annotated[str | None, typer.Argument(..., help="The root directory of the project to edit, or a file path.")] = None,
) -> None:
    from pathlib import Path

    if path is None:
        root_path = Path.cwd()
        print(f"No path provided. Using current working directory: {root_path}")
    else:
        root_path = Path(path).expanduser().resolve()
        print(f"Using provided path: {root_path}")
    from stackops.utils.accessories import get_repo_root

    repo_root = get_repo_root(root_path)
    if repo_root is not None and repo_root.joinpath("pyproject.toml").exists():
        code = f"""
cd {repo_root}
uv add --dev pylsp-mypy python-lsp-server[mypy] pyright ruff-lsp  # for helix editor.
source ./.venv/bin/activate
"""
    else:
        code = ""
    if root_path.is_file():
        code += f"hx {root_path}"
    else:
        code += "hx"
    from stackops.utils.code import exit_then_run_shell_script

    exit_then_run_shell_script(code)


class MachineSpecs(TypedDict):
    system: Literal["Windows", "Linux", "Darwin"]
    distro: str
    home_dir: str
    hostname: str
    release: str
    version: str
    machine: str
    processor: str
    python_version: str
    user: str


def get_machine_specs(hardware: Annotated[bool, typer.Option(..., "--hardware", "-h", help="Show compute capability")] = False) -> MachineSpecs:
    """Write print and return the local machine specs."""
    if hardware:
        from stackops.scripts.python.helpers.helpers_utils.specs import main
        main()
        import sys
        sys.exit()

    import platform
    from stackops.utils.code import get_uv_command

    uv_cmd = get_uv_command(platform=platform.system())
    command = f"""{uv_cmd} run --with distro python -c "import distro; print(distro.name(pretty=True))" """
    import subprocess
    from pathlib import Path
    import socket
    import os

    distro = "Unknown"
    try:
        distro_process = subprocess.run(command, shell=True, capture_output=True, text=True, check=False)
        detected_distro = distro_process.stdout.strip()
        if distro_process.returncode == 0 and detected_distro:
            distro = detected_distro
    except OSError:
        pass
    system = platform.system()
    if system not in {"Windows", "Linux", "Darwin"}:
        system = "Linux"
    specs: MachineSpecs = {
        "system": cast(Literal["Windows", "Linux", "Darwin"], system),
        "distro": distro,
        "home_dir": str(Path.home()),
        "hostname": socket.gethostname(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor() or "Unknown",
        "python_version": platform.python_version(),
        "user": os.getenv("USER") or os.getenv("USERNAME") or "Unknown",
    }
    print(specs)
    from stackops.utils.source_of_truth import CONFIG_ROOT

    path = CONFIG_ROOT.joinpath("machine_specs.json")
    CONFIG_ROOT.mkdir(parents=True, exist_ok=True)
    import json

    path.write_text(json.dumps(specs, indent=4), encoding="utf-8")
    return specs


if __name__ == "__main__":
    get_machine_specs()
