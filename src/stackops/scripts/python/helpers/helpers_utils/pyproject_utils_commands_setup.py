from pathlib import Path
from typing import Annotated, Literal

import typer

from stackops.scripts.python.helpers.helpers_utils.pyproject_utils_helpers import (
    TypeHintDependencyMode,
    normalize_init_project_groups,
    normalize_init_project_libraries,
    resolve_pyproject_root,
)


def upgrade_packages(
    root: Annotated[
        str,
        typer.Argument(
            help="Project root or any path inside the project."
        ),
    ] = ".",
    clean_group: Annotated[
        list[str] | None,
        typer.Option(
            "--clean-group",
            "-c",
            help="Capture all dependencies in pyproject_init.sh, then empty the specified dependency group or optional-dependency extra. Repeat for multiple groups. If a name exists in both tables, qualify it as dependency-group:name or optional-dependency:name.",
        ),
    ] = None,
    clean_all_groups: Annotated[
        bool,
        typer.Option(
            "--clean-all-groups",
            "-C",
            help="Capture all dependencies in pyproject_init.sh, then empty every dependency group and optional-dependency extra.",
        ),
    ] = False,
    delete_venv: Annotated[
        bool,
        typer.Option(
            "--delete-venv",
            "-D",
            help="Delete the project's .venv directory after generating pyproject_init.sh.",
        ),
    ] = False,
) -> None:
    import subprocess

    from stackops.scripts.python.helpers.helpers_utils.upgrade_packages import (
        clean_dependency_groups,
        delete_project_venv,
        generate_uv_add_commands,
    )

    try:
        project_root = resolve_pyproject_root(Path(root))
        selected_clean_groups = [] if clean_group is None else clean_group
        generate_uv_add_commands(
            pyproject_path=project_root / "pyproject.toml",
            output_path=project_root / "pyproject_init.sh",
        )
        if clean_all_groups or selected_clean_groups:
            clean_dependency_groups(
                project_root=project_root,
                group_names=selected_clean_groups,
                clean_all_groups=clean_all_groups,
            )
        if delete_venv:
            delete_project_venv(project_root=project_root)
    except ValueError as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from error
    except FileNotFoundError as error:
        typer.echo(f"Error: Required file or command was not found: {error}", err=True)
        raise typer.Exit(code=1) from error
    except subprocess.CalledProcessError as error:
        typer.echo(
            f"Error: uv remove failed with exit code {error.returncode}.",
            err=True,
        )
        raise typer.Exit(code=error.returncode) from error


def type_hint(
    path: Annotated[str, typer.Argument(..., help="Path to file/project dir to type hint.")] = ".",
    dependency: Annotated[
        TypeHintDependencyMode,
        typer.Option(..., "--dependency", "-d", help="Generated file is self contained or performs imports"),
    ] = "self-contained",
) -> None:
    path_resolved = Path(path).expanduser().resolve()
    if path_resolved.exists() is False:
        typer.echo(f"Error: The provided path '{path}' does not exist.", err=True)
        raise typer.Exit(code=1)
    if path_resolved.is_file():
        modules = [path_resolved]
    else:
        if path_resolved.joinpath("pyproject.toml").exists() is False:
            typer.echo("Error: Provided directory path is not a project root (missing pyproject.toml).", err=True)
            raise typer.Exit(code=1)
        modules = [file for file in path_resolved.rglob("dtypes.py") if ".venv" not in file.parts]
    if len(modules) == 0:
        typer.echo("Error: No dtypes.py files were found under the provided project root.", err=True)
        raise typer.Exit(code=1)
    typer.echo(
        f"Error: Type-hint generation is not available for dependency mode '{dependency}' because the generator implementation is missing.",
        err=True,
    )
    raise typer.Exit(code=1)


def init_project(
    name: Annotated[str | None, typer.Option("--name", "-n", help="Name of the project.")] = None,
    tmp_dir: Annotated[bool, typer.Option("--tmp-dir", "-t", help="Use a temporary directory for the project initialization.")] = False,
    python: Annotated[
        Literal["3.11", "3.12", "3.13", "3.14"],
        typer.Option("--python", "-p", help="Python sub version for the uv virtual environment."),
    ] = "3.13",
    libraries: Annotated[
        str | None,
        typer.Option("--libraries", "-l", help="Additional packages to include in the uv virtual environment (space separated)."),
    ] = None,
    group: Annotated[
        str | None,
        typer.Option("--group", "-g", help="Comma-separated package group keys: p=plot, t/types=typing stubs, l=linting, i=interactive, d=data."),
    ] = "p,t,l,i,d",
) -> None:
    from stackops.scripts.python.helpers.helpers_utils.python_init import init_project as impl

    try:
        normalized_group = normalize_init_project_groups(group=group)
    except ValueError as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from error
    normalized_libraries = normalize_init_project_libraries(libraries=libraries)
    impl(
        name=name,
        tmp_dir=tmp_dir,
        python=python,
        libraries=normalized_libraries,
        group=normalized_group,
    )
