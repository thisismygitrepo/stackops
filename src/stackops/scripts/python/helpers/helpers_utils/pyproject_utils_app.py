import json
import os
import subprocess
from pathlib import Path
from typing import Annotated, Literal, TypeAlias

import typer

import stackops.scripts.python.ai.scripts as ai_scripts
from stackops.scripts.python.helpers.helpers_utils import test_runtime as test_runtime_module
from stackops.scripts.python.helpers.helpers_utils import type_fix as type_fix_module
from stackops.utils.path_reference import get_path_reference_path


ProjectPythonVersion: TypeAlias = Literal["3.11", "3.12", "3.13", "3.14"]
TypeHintDependencyMode: TypeAlias = Literal["self-contained", "import"]
InitProjectGroupKey: TypeAlias = Literal["p", "t", "types", "l", "i", "d"]
TYPE_CHECK_EXCLUDES_ENV_VAR = "STACKOPS_TYPE_CHECK_EXCLUDES"
DEFAULT_TYPE_CHECK_EXCLUDED_DIRECTORIES: tuple[str, ...] = (
    "tests",
    ".github",
    ".codex",
    ".ai",
    ".links",
    ".venv",
)
INIT_PROJECT_GROUP_KEYS: tuple[InitProjectGroupKey, ...] = (
    "p",
    "t",
    "types",
    "l",
    "i",
    "d",
)


def _normalize_init_project_groups(group: str | None) -> str | None:
    if group is None:
        return None
    group_keys = [group_key.strip() for group_key in group.split(",")]
    normalized_group_keys = [
        group_key for group_key in group_keys if group_key != ""
    ]
    invalid_group_keys = [
        group_key
        for group_key in normalized_group_keys
        if group_key not in INIT_PROJECT_GROUP_KEYS
    ]
    if len(invalid_group_keys) > 0:
        invalid_groups = ", ".join(invalid_group_keys)
        valid_groups = ", ".join(INIT_PROJECT_GROUP_KEYS)
        raise ValueError(
            f"Unknown package group(s): {invalid_groups}. Valid groups: {valid_groups}."
        )
    seen_group_keys: set[str] = set()
    unique_group_keys: list[str] = []
    for group_key in normalized_group_keys:
        if group_key in seen_group_keys:
            continue
        seen_group_keys.add(group_key)
        unique_group_keys.append(group_key)
    if len(unique_group_keys) == 0:
        return None
    return ",".join(unique_group_keys)


def _normalize_init_project_libraries(libraries: str | None) -> str | None:
    if libraries is None:
        return None
    libraries_stripped = libraries.strip()
    if libraries_stripped == "":
        return None
    return libraries_stripped


def _resolve_pyproject_root(path: Path) -> Path:
    path_resolved = path.expanduser().resolve()
    if path_resolved.exists() is False:
        raise ValueError(f"The provided path '{path}' does not exist.")
    search_root = path_resolved if path_resolved.is_dir() else path_resolved.parent
    for current in [search_root, *search_root.parents]:
        if current.joinpath("pyproject.toml").exists():
            return current
    raise ValueError(
        f"Could not find pyproject.toml at or above '{path_resolved}'."
    )


def _resolve_type_check_excluded_directory(
    repo_root: Path, excluded_directory: str
) -> str | None:
    candidate_path = Path(excluded_directory).expanduser()
    if candidate_path.is_absolute() is False:
        candidate_path = repo_root.joinpath(candidate_path)
    candidate_path_absolute = Path(os.path.abspath(candidate_path))
    if candidate_path_absolute.is_dir() is False:
        return None
    try:
        relative_directory = candidate_path_absolute.relative_to(repo_root)
    except ValueError as error:
        raise ValueError(
            f"Excluded directory '{excluded_directory}' must be inside '{repo_root}'."
        ) from error
    if relative_directory == Path("."):
        raise ValueError("Excluded directory cannot be the repository root.")
    return relative_directory.as_posix()


def _resolve_type_check_excluded_directories(
    repo_root: Path, excluded_directories: list[str] | None
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if excluded_directories is None:
        return (), ()
    normalized_directories: list[str] = []
    skipped_directories: list[str] = []
    seen_directories: set[str] = set()
    for excluded_directory in excluded_directories:
        normalized_directory = _resolve_type_check_excluded_directory(
            repo_root=repo_root, excluded_directory=excluded_directory
        )
        if normalized_directory is None:
            skipped_directories.append(excluded_directory)
            continue
        if normalized_directory in seen_directories:
            continue
        seen_directories.add(normalized_directory)
        normalized_directories.append(normalized_directory)
    return tuple(normalized_directories), tuple(skipped_directories)


def _build_type_check_environment(
    excluded_directories: tuple[str, ...],
) -> dict[str, str]:
    environment = os.environ.copy()
    environment[TYPE_CHECK_EXCLUDES_ENV_VAR] = json.dumps(
        list(excluded_directories)
    )
    return environment


def type_check(
    repo: Annotated[
        str,
        typer.Argument(
            help="Repository root or any path inside the repository to lint and type check."
        ),
    ] = ".",
    exclude: Annotated[
        list[str] | None,
        typer.Option(
            "--exclude",
            "-x",
            help="Additional directory to exclude from lint and type checking. Relative values are resolved from the repository root. Repeat for multiple directories.",
        ),
    ] = None,
) -> None:
    if exclude is None:
        exclude = list(DEFAULT_TYPE_CHECK_EXCLUDED_DIRECTORIES)
    else:
        exclude = [*DEFAULT_TYPE_CHECK_EXCLUDED_DIRECTORIES, *exclude]
    try:
        repo_root = _resolve_pyproject_root(Path(repo))
        (
            excluded_directories,
            skipped_excluded_directories,
        ) = _resolve_type_check_excluded_directories(
            repo_root=repo_root, excluded_directories=exclude
        )
    except ValueError as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from error
    for skipped_excluded_directory in skipped_excluded_directories:
        typer.echo(
            f"Warning: Skipping excluded path '{skipped_excluded_directory}' because it is not an existing directory.",
            err=True,
        )

    script_path = get_path_reference_path(
        ai_scripts, ai_scripts.LINT_AND_TYPE_CHECK_PATH_REFERENCE
    )
    if script_path.exists() is False:
        typer.echo(
            f"Error: StackOps type-check script not found at '{script_path}'.",
            err=True,
        )
        raise typer.Exit(code=1)

    try:
        completed = subprocess.run(
            ["uv", "run", str(script_path)],
            cwd=repo_root,
            check=False,
            env=_build_type_check_environment(excluded_directories),
        )
    except FileNotFoundError as error:
        typer.echo("Error: uv is required but was not found on PATH.", err=True)
        raise typer.Exit(code=1) from error
    if completed.returncode != 0:
        raise typer.Exit(code=completed.returncode)

def reference_test(
    repo: Annotated[
        str,
        typer.Argument(
            help="Repository root or any path inside the repository."
        ),
    ] = ".",
    search_root: Annotated[
        str | None,
        typer.Option(
            "--search-root",
            "-s",
            help="Directory to scan for package __init__.py files. Relative values are resolved from the repository root.",
        ),
    ] = None,
    verbose: Annotated[bool, typer.Option("--verbose", help="Print scan context and detailed rich audit tables.")] = False,
) -> None:
    from rich.panel import Panel

    from stackops.scripts.python.helpers.helpers_utils.path_reference_validation import (
        audit_repository_path_references,
        build_reference_test_console,
        format_path_reference_audit,
        print_reference_test_summary,
        print_reference_test_verbose_details,
    )

    console = build_reference_test_console()
    search_root_path = None if search_root is None else Path(search_root)
    try:
        audit = audit_repository_path_references(repo_path=Path(repo), search_root=search_root_path)
    except ValueError as error:
        console.print(Panel(f"❌ {error}", title="Reference Audit Error", border_style="red", expand=False))
        raise typer.Exit(code=1) from error

    print_reference_test_summary(console=console, audit=audit)
    if audit.has_failures():
        if verbose:
            print_reference_test_verbose_details(console=console, audit=audit)
        else:
            console.print(Panel(format_path_reference_audit(audit=audit), title="❌ Failure Details", border_style="red", expand=False))
        raise typer.Exit(code=1)
    if verbose:
        print_reference_test_verbose_details(console=console, audit=audit)


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
            help="Empty the specified dependency group or optional-dependency extra before regenerating pyproject_init.sh. Repeat for multiple groups.",
        ),
    ] = None,
) -> None:
    from stackops.utils.upgrade_packages import clean_dependency_groups, generate_uv_add_commands

    try:
        project_root = _resolve_pyproject_root(Path(root))
        if clean_group:
            clean_dependency_groups(project_root=project_root, group_names=clean_group)
        generate_uv_add_commands(
            pyproject_path=project_root / "pyproject.toml",
            output_path=project_root / "pyproject_init.sh",
        )
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
        ProjectPythonVersion,
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
    from stackops.scripts.python.helpers.helpers_utils.python import init_project as impl

    try:
        normalized_group = _normalize_init_project_groups(group=group)
    except ValueError as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from error
    normalized_libraries = _normalize_init_project_libraries(libraries=libraries)
    impl(
        name=name,
        tmp_dir=tmp_dir,
        python=python,
        libraries=normalized_libraries,
        group=normalized_group,
    )


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
    pyproject_app.command(name="type-check", no_args_is_help=False, help="🧪 <c> Run the lint-and-type-check suite for a repository.")(type_check)
    pyproject_app.command(name="c", no_args_is_help=False, hidden=True)(type_check)
    pyproject_app.add_typer(type_fix_module.get_app(), name="type-fix", help="🛠 <f> Create and run the type-fix workflow from ./.ai/linters issues files.")
    pyproject_app.add_typer(type_fix_module.get_app(), name="f", hidden=True)

    pyproject_app.add_typer(
        test_runtime_module.get_app(),
        name="test-runtime",
        help="🧪 <R> Create and run the runtime-test workflow for Python files under the current directory.",
    )
    pyproject_app.add_typer(test_runtime_module.get_app(), name="tr", hidden=True)
    pyproject_app.command(name="test-reference", no_args_is_help=False, help="🔎 <r> Validate _PATH_REFERENCE targets in a repository.")(reference_test)
    pyproject_app.command(name="r", no_args_is_help=False, hidden=True)(reference_test)
    return pyproject_app
