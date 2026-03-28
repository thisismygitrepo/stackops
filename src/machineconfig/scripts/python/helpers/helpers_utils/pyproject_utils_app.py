from pathlib import Path
from typing import Annotated, Literal, TypeAlias

import typer


ProjectPythonVersion: TypeAlias = Literal["3.11", "3.12", "3.13", "3.14"]
TypeHintDependencyMode: TypeAlias = Literal["self-contained", "import"]


def upgrade_packages(
    root: Annotated[str, typer.Argument(help="Root directory of the project")] = ".",
    clean_group: Annotated[
        list[str] | None,
        typer.Option(
            "--clean-group",
            "-c",
            help="Empty the specified dependency group or optional-dependency extra before regenerating pyproject_init.sh. Repeat for multiple groups.",
        ),
    ] = None,
) -> None:
    from machineconfig.utils.upgrade_packages import clean_dependency_groups, generate_uv_add_commands

    root_resolved = Path(root).expanduser().resolve()
    if clean_group:
        clean_dependency_groups(project_root=root_resolved, group_names=clean_group)
    generate_uv_add_commands(pyproject_path=root_resolved / "pyproject.toml", output_path=root_resolved / "pyproject_init.sh")


def type_hint(
    path: Annotated[str, typer.Argument(..., help="Path to file/project dir to type hint.")] = ".",
    dependency: Annotated[
        TypeHintDependencyMode,
        typer.Option(..., "--dependency", "-d", help="Generated file is self contained or performs imports"),
    ] = "self-contained",
) -> None:
    from machineconfig.type_hinting.typedict.generators import generate_names_file

    path_resolved = Path(path).resolve()
    if not path_resolved.exists():
        typer.echo(f"Error: The provided path '{path}' does not exist.", err=True)
        raise typer.Exit(code=1)
    if path_resolved.is_file():
        modules = [path_resolved]
    else:
        if not (path_resolved / "pyproject.toml").exists():
            typer.echo("Error: Provided directory path is not a project root (missing pyproject.toml).", err=True)
            raise typer.Exit(code=1)
        modules = [file for file in path_resolved.rglob("dtypes.py") if ".venv" not in str(file)]
    for input_file in modules:
        print(f"Worked on: {input_file}")
        output_file = input_file.parent.joinpath(f"{input_file.stem}_names.py")
        generated_file = generate_names_file(input_file, output_file, search_paths=None, dependency=dependency)
        print(f"Generated: {generated_file}")


def init_project(
    name: Annotated[str | None, typer.Option("--name", "-n", help="Name of the project.")] = None,
    tmp_dir: Annotated[bool, typer.Option("--tmp-dir", "-t", help="Use a temporary directory for the project initialization.")] = False,
    python: Annotated[
        ProjectPythonVersion,
        typer.Option("--python", "-p", help="Python sub version for the uv virtual environment."),
    ] = "3.13",
    libraries: Annotated[
        str | None,
        typer.Option("--libraries", "-l", help="Additional packages to include in the uv virtual environment (space separated)."),
    ] = None,
    group: Annotated[
        str | None,
        typer.Option("--group", "-g", help="group of packages names (no separation) p:plot, t:types, l:linting, i:interactive, d:data"),
    ] = "p,t,l,i,d",
) -> None:
    from machineconfig.scripts.python.helpers.helpers_utils.python import init_project as impl

    impl(name=name, tmp_dir=tmp_dir, python=python, libraries=libraries, group=group)


def get_app() -> typer.Typer:
    pyproject_app = typer.Typer(help="🐍 <p> Pyproject bootstrap and typing utilities", no_args_is_help=True, add_help_option=True, add_completion=False)
    pyproject_app.command(
        name="init-project",
        no_args_is_help=False,
        help="✦ <i> Initialize a project with a uv virtual environment and install dev packages.",
    )(init_project)
    pyproject_app.command(name="i", no_args_is_help=False, hidden=True)(init_project)
    pyproject_app.command(name="upgrade-packages", no_args_is_help=False, help="↑ <a> Upgrade project dependencies.")(upgrade_packages)
    pyproject_app.command(name="a", no_args_is_help=False, hidden=True)(upgrade_packages)
    pyproject_app.command(name="up", no_args_is_help=False, hidden=True)(upgrade_packages)
    pyproject_app.command(name="type-hint", no_args_is_help=True, help="✐ <t> Type hint a file or project directory.")(type_hint)
    pyproject_app.command(name="t", no_args_is_help=True, hidden=True)(type_hint)
    return pyproject_app
