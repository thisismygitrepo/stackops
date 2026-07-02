from pathlib import Path
from typing import Annotated

import typer


def _resolve_directory(directory: str | None) -> Path:
    if directory is None:
        directory = Path.cwd().as_posix()
        typer.echo(f"📁 Using directory: {directory}")
    return Path(directory).expanduser().absolute().resolve()


def _resolve_spec_path(specs_path: str | Path | None) -> Path:
    from stackops.scripts.python.helpers.helpers_repos.spec_store import resolve_repos_spec_path

    resolved_spec_path = resolve_repos_spec_path(specs_path=specs_path)
    if not resolved_spec_path.exists():
        typer.echo(
            f"❌ Specification file not found: {resolved_spec_path}. Run devops repos register first, or provide another file using --specs-path."
        )
        raise typer.Exit(code=1)
    if not resolved_spec_path.is_file():
        typer.echo(f"❌ Specification path is not a file: {resolved_spec_path}")
        raise typer.Exit(code=1)
    return resolved_spec_path


def _prompt_capture_options(directory: str | None, specs_path: str | None) -> tuple[str, str]:
    from stackops.scripts.python.helpers.helpers_devops.register_interactive import ask_text, confirm_summary

    from stackops.scripts.python.helpers.helpers_repos.spec_store import DEFAULT_REPOS_SPEC_PATH

    directory_default = directory or Path.cwd().as_posix()
    specs_path_default = specs_path or DEFAULT_REPOS_SPEC_PATH.as_posix()
    prompted_directory = ask_text(
        "Repository directory",
        help_text="Directory to scan for Git repositories. Existing records under this root are refreshed.",
        default=directory_default,
    )
    prompted_specs_path = ask_text(
        "Specification path",
        help_text="repos.json file to create or update. Records outside the scanned root are preserved.",
        default=specs_path_default,
    )
    assert prompted_directory is not None
    assert prompted_specs_path is not None
    confirm_summary("Repository Register Review", [f"directory: {prompted_directory}", f"specs_path: {prompted_specs_path}"])
    return prompted_directory, prompted_specs_path


def action(
    directory: Annotated[str | None, typer.Argument(help="📁 Directory containing repo(s).")] = None,
    recursive: Annotated[bool, typer.Option("--recursive", "-r", help="🔍 Recurse into nested repositories.")] = False,
    auto_uv_sync: Annotated[bool, typer.Option("--uv-sync", "-u", help="Run uv sync automatically after pulls.")] = False,
    pull: Annotated[bool, typer.Option("--pull", "-P", help="↓ Pull changes across repositories.")] = False,
    commit: Annotated[bool, typer.Option("--commit", "-c", help="💾 Commit changes across repositories.")] = False,
    push: Annotated[bool, typer.Option("--push", "-p", help="🚀 Push changes across repositories.")] = False,
) -> None:
    """🔄 Run pull/commit/push actions across repositories based on flags."""
    if not pull and not commit and not push:
        typer.echo("❌ No action selected. Use at least one of --pull, --commit, or --push.", err=True)
        raise SystemExit(1)
    repos_root = _resolve_directory(directory)
    from stackops.scripts.python.helpers.helpers_repos.action import perform_git_operations

    perform_git_operations(repos_root=repos_root, pull=pull, commit=commit, push=push, recursive=recursive, auto_uv_sync=auto_uv_sync)


def capture(
    directory: Annotated[str | None, typer.Argument(help="📁 Directory containing repo(s).")] = None,
    specs_path: Annotated[
        str | None, typer.Option("--specs-path", "-s", help="Path to repos.json specification file.")
    ] = None,
    interactive: Annotated[bool, typer.Option("--interactive", "-i", help="Prompt for register fields one step at a time.")] = False,
) -> None:
    """📝 Record repositories into a repos.json specification."""
    from stackops.scripts.python.helpers.helpers_repos.record import main_record as record_repos

    if interactive:
        directory, specs_path = _prompt_capture_options(directory=directory, specs_path=specs_path)
    save_path = record_repos(repos_root_str=directory, specs_path=specs_path)
    print(f"\n✅ Saved repository specification to {save_path}")


def clone(
    specs_path: Annotated[
        str | None, typer.Option("--specs-path", "-s", help="Path to repos.json specification file.")
    ] = None,
    checkout_to_commit: Annotated[
        bool, typer.Option("--checkout-to-commit", "-c", help="Check out specific commits listed in the specification.")
    ] = False,
    checkout_to_branch: Annotated[
        bool, typer.Option("--checkout-to-branch", "-b", help="Check out the branch recorded in the specification.")
    ] = False,
) -> None:
    """📥 Clone repositories described by a repos.json specification."""
    if checkout_to_commit and checkout_to_branch:
        typer.echo("❌ Choose only one checkout mode: --checkout-to-commit or --checkout-to-branch.")
        raise typer.Exit(code=1)

    checkout_branch_flag = checkout_to_branch
    checkout_commit_flag = checkout_to_commit
    spec_path_self_managed = _resolve_spec_path(specs_path)
    from stackops.scripts.python.helpers.helpers_repos.clone import clone_repos

    results = clone_repos(
        spec_path=spec_path_self_managed, preferred_remote=None, checkout_branch_flag=checkout_branch_flag, checkout_commit_flag=checkout_commit_flag
    )
    if any(status == "failed" for status, _message in results):
        raise typer.Exit(code=1)


def checkout_command(
    specs_path: Annotated[
        str | None, typer.Option("--specs-path", "-s", help="Path to repos.json specification file.")
    ] = None,
) -> None:
    """🔀 Check out specific commits listed in the specification."""
    clone(specs_path=specs_path, checkout_to_commit=True, checkout_to_branch=False)


def checkout_to_branch_command(
    specs_path: Annotated[
        str | None, typer.Option("--specs-path", "-s", help="Path to repos.json specification file.")
    ] = None,
) -> None:
    """🔀 Check out the branch recorded in the specification."""
    clone(specs_path=specs_path, checkout_to_commit=False, checkout_to_branch=True)


def get_app() -> typer.Typer:
    from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync import main as secure_repo_main
    from stackops.scripts.python.helpers.helpers_devops.cli_repos_viz import (
        analyze_repo_development,
        count_lines_in_repo,
        gource_viz,
    )

    repos_apps = typer.Typer(help="📁 <r> Manage development repositories", no_args_is_help=True, add_help_option=True, add_completion=False)

    repos_apps.command(name="sync", help="📥 <s> Clone repositories described by a repos.json specification")(clone)
    repos_apps.command(name="s", help="Clone repositories described by a repos.json specification", hidden=True)(clone)

    repos_apps.command(name="register", help="📝 <r> Record repositories into a repos.json specification")(capture)
    repos_apps.command(name="r", help="Record repositories into a repos.json specification", hidden=True)(capture)

    repos_apps.command(name="action", help="🔄 <a> Run pull/commit/push actions across repositories", no_args_is_help=True)(action)
    repos_apps.command(name="a", help="Run pull/commit/push actions across repositories", hidden=True, no_args_is_help=True)(action)
    repos_apps.command(name="analyze", help="📊 <z> Analyze repository development over time")(analyze_repo_development)
    repos_apps.command(name="z", help="Analyze repository development over time", hidden=True)(analyze_repo_development)

    repos_apps.command(name="guard", help="🔐 <g> Securely sync git repository to/from cloud with encryption")(secure_repo_main)
    repos_apps.command(name="g", help="Securely sync git repository to/from cloud with encryption", hidden=True)(secure_repo_main)

    repos_apps.command(name="viz", help="🎬 <v> Visualize repository activity using Gource")(gource_viz)
    repos_apps.command(name="v", help="Visualize repository activity using Gource", hidden=True)(gource_viz)

    repos_apps.command(name="count-lines", help="📄 <c> Count python lines of code in current repo + historical edits.")(count_lines_in_repo)
    repos_apps.command(name="c", help="Count python lines of code in current repo + historical edits.", hidden=True)(count_lines_in_repo)

    return repos_apps
