from typing import Annotated, Literal

import typer


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
    from stackops.scripts.python.helpers.helpers_utils.python_env import build_virtualenv_activation_line
    groups_packages_lines = "\n".join(
        [f"uv add --group {group_name} {' '.join(packages)}" for group_name, packages in total_packages.items()]
    )   
    script = f"""
{starting_code}
{packages_add_line}
{groups_packages_lines}
{build_virtualenv_activation_line(repo_root.joinpath(".venv"))}
{agents_line}
ls
"""
    from stackops.utils.code import exit_then_run_shell_script, run_shell_script
    exit_then_run_shell_script(script)
    _ = exit_then_run_shell_script, run_shell_script
