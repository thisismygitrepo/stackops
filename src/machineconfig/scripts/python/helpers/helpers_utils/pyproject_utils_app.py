from pathlib import Path
from typing import Annotated, Literal, TypeAlias

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from machineconfig.utils.path_reference_validation import EXCLUDED_DIR_NAMES, PathReferenceAudit, audit_repository_path_references, format_path_reference_audit


ProjectPythonVersion: TypeAlias = Literal["3.11", "3.12", "3.13", "3.14"]
TypeHintDependencyMode: TypeAlias = Literal["self-contained", "import"]


def _build_reference_test_console() -> Console:
    return Console()


def _repo_relative_path(*, path: Path, repo_root: Path) -> str:
    resolved_path = path.resolve(strict=False)
    resolved_repo_root = repo_root.resolve(strict=False)
    try:
        return resolved_path.relative_to(resolved_repo_root).as_posix()
    except ValueError:
        return resolved_path.as_posix()


def _build_reference_test_summary_table(*, audit: PathReferenceAudit) -> Table:
    table = Table(box=None, show_header=False, pad_edge=False)
    table.add_column("Field", style="bold cyan")
    table.add_column("Value", style="white")
    table.add_row("📦 Repository", str(audit.repo_root))
    table.add_row("🔎 Search Root", str(audit.search_root))
    table.add_row("🧭 Packages", str(audit.scanned_init_files))
    table.add_row("🔗 Declared Targets", str(audit.reference_count))
    table.add_row("✅ Resolved Targets", str(audit.resolved_reference_count()))
    table.add_row("⚠ Invalid Definitions", str(audit.invalid_count()))
    table.add_row("❌ Missing Targets", str(audit.missing_count()))
    return table


def _build_invalid_reference_table(*, audit: PathReferenceAudit) -> Table | None:
    if audit.invalid_count() == 0:
        return None
    table = Table(title="⚠ Invalid Definitions", header_style="bold yellow")
    table.add_column("File", style="cyan")
    table.add_column("Variable", style="magenta")
    table.add_column("Reason", style="white")
    for invalid_reference in audit.invalid_references:
        table.add_row(
            _repo_relative_path(path=invalid_reference.init_file, repo_root=audit.repo_root),
            invalid_reference.variable_name,
            invalid_reference.reason,
        )
    return table


def _build_missing_reference_table(*, audit: PathReferenceAudit) -> Table | None:
    if audit.missing_count() == 0:
        return None
    table = Table(title="❌ Missing Targets", header_style="bold red")
    table.add_column("File", style="cyan")
    table.add_column("Variable", style="magenta")
    table.add_column("Target", style="yellow")
    table.add_column("Resolved Path", style="white")
    for missing_reference in audit.missing_references:
        table.add_row(
            _repo_relative_path(path=missing_reference.init_file, repo_root=audit.repo_root),
            missing_reference.variable_name,
            missing_reference.relative_path,
            missing_reference.resolved_path.as_posix(),
        )
    return table


def _print_reference_test_summary(*, console: Console, audit: PathReferenceAudit) -> None:
    title = "✅ Reference Audit Passed" if not audit.has_failures() else "❌ Reference Audit Failed"
    border_style = "green" if not audit.has_failures() else "red"
    console.print(Panel(_build_reference_test_summary_table(audit=audit), title=title, border_style=border_style, expand=False))


def _print_reference_test_verbose_details(*, console: Console, audit: PathReferenceAudit) -> None:
    excluded_directories = ", ".join(sorted(EXCLUDED_DIR_NAMES))
    console.print(Panel(excluded_directories, title="🧹 Excluded Directories", border_style="blue", expand=False))

    invalid_table = _build_invalid_reference_table(audit=audit)
    if invalid_table is None:
        console.print(Panel("✅ No invalid _PATH_REFERENCE definitions found.", title="⚠ Invalid Definitions", border_style="green", expand=False))
    else:
        console.print(invalid_table)

    missing_table = _build_missing_reference_table(audit=audit)
    if missing_table is None:
        console.print(Panel("✅ No missing _PATH_REFERENCE targets found.", title="❌ Missing Targets", border_style="green", expand=False))
    else:
        console.print(missing_table)


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
    # from machineconfig.type_hinting.typedict.generators import generate_names_file

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
        # generated_file = generate_names_file(input_file, output_file, search_paths=None, dependency=dependency)
        # print(f"Generated: {generated_file}")
        print(f"Generated: {output_file}")


def reference_test(
    repo: Annotated[str, typer.Argument(..., help="Repository root or any path inside the repository.")],
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
    console = _build_reference_test_console()
    search_root_path = None if search_root is None else Path(search_root)
    try:
        audit = audit_repository_path_references(repo_path=Path(repo), search_root=search_root_path)
    except ValueError as error:
        console.print(Panel(f"❌ {error}", title="Reference Audit Error", border_style="red", expand=False))
        raise typer.Exit(code=1) from error

    _print_reference_test_summary(console=console, audit=audit)
    if audit.has_failures():
        if verbose:
            _print_reference_test_verbose_details(console=console, audit=audit)
        else:
            console.print(Panel(format_path_reference_audit(audit=audit), title="❌ Failure Details", border_style="red", expand=False))
        raise typer.Exit(code=1)
    if verbose:
        _print_reference_test_verbose_details(console=console, audit=audit)


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
    pyproject_app.command(name="reference-test", no_args_is_help=True, help="🔎 <r> Validate _PATH_REFERENCE targets in a repository.")(reference_test)
    pyproject_app.command(name="r", no_args_is_help=True, hidden=True)(reference_test)
    return pyproject_app
