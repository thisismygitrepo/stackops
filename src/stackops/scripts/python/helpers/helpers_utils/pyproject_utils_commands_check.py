from pathlib import Path
from typing import Annotated

import typer



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
    latest: Annotated[
        bool,
        typer.Option(
            "--latest",
            "-l",
            help="Resolve and report the latest compatible lint and type-check tool versions for this run.",
        ),
    ] = False,
    tools: Annotated[
        str | None,
        typer.Option(
            "--tools",
            "-t",
            help="One tool or a comma-separated list: pyright, mypy, pylint, pyrefly, ty, ruff. Omit to run all tools.",
        ),
    ] = None,
) -> None:
    import subprocess
    import sys

    import stackops.scripts.python.ai.scripts as ai_scripts
    from stackops.scripts.python.ai.scripts.models_config import parse_type_check_tools
    from stackops.scripts.python.helpers.helpers_utils.pyproject_utils_helpers import (
        DEFAULT_TYPE_CHECK_EXCLUDED_DIRECTORIES,
        build_type_check_environment,
        resolve_pyproject_root,
        resolve_type_check_excluded_directories,
    )
    from stackops.utils.path_reference import get_path_reference_path

    try:
        selected_tools = parse_type_check_tools(tools)
        repo_root = resolve_pyproject_root(Path(repo))
        explicit_excluded_directories = [] if exclude is None else exclude
        (
            resolved_explicit_excluded_directories,
            skipped_explicit_excluded_directories,
        ) = resolve_type_check_excluded_directories(
            repo_root=repo_root,
            excluded_directories=explicit_excluded_directories,
        )
        if len(skipped_explicit_excluded_directories) > 0:
            skipped_paths = ", ".join(
                f"'{excluded_directory}'"
                for excluded_directory in skipped_explicit_excluded_directories
            )
            raise ValueError(
                f"Excluded directories must exist inside '{repo_root}': {skipped_paths}."
            )
    except ValueError as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from error
    excluded_directories = tuple(
        dict.fromkeys(
            (
                *DEFAULT_TYPE_CHECK_EXCLUDED_DIRECTORIES,
                *resolved_explicit_excluded_directories,
            )
        )
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

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "stackops.scripts.python.ai.scripts.lint_and_type_check",
        ],
        cwd=repo_root,
        check=False,
        env=build_type_check_environment(
            excluded_directories=excluded_directories,
            latest=latest,
            selected_tools=selected_tools,
        ),
    )
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
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Print scan context and detailed rich audit tables.")] = False,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Print reference mappings and validation diagnostics as JSON.")] = False,
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
        if json_output:
            typer.echo(f"Reference audit failed: {error}", err=True)
            raise typer.Exit(code=1) from error
        console.print(Panel(f"❌ {error}", title="Reference Audit Error", border_style="red", expand=False))
        raise typer.Exit(code=1) from error

    if json_output:
        import json
        from dataclasses import asdict

        typer.echo(json.dumps({**asdict(audit), "passed": not audit.has_failures(), "resolved_reference_count": audit.resolved_reference_count()}, indent=2, default=str))
        if audit.has_failures():
            raise typer.Exit(code=1)
        return
    print_reference_test_summary(console=console, audit=audit)
    if audit.has_failures():
        if verbose:
            print_reference_test_verbose_details(console=console, audit=audit)
        else:
            console.print(Panel(format_path_reference_audit(audit=audit), title="❌ Failure Details", border_style="red", expand=False))
        raise typer.Exit(code=1)
    if verbose:
        print_reference_test_verbose_details(console=console, audit=audit)
