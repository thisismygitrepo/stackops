from pathlib import Path
from typing import Annotated

import typer

from stackops.scripts.python.helpers.helpers_devops import cli_subset_support
from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_constants import SecretsSource, WritableSecretsSource

SECRETS_HELP = "Manage StackOps secrets JSON files and define env vars."
SECRETS_SEARCH_HELP = "Inspect matching secret bundles without loading environment variables."
SECRETS_LOAD_HELP = "Load matching secret bundles into environment variables."
SECRETS_STATS_HELP = "Show aggregate StackOps secrets inventory stats without printing secret values."
SECRETS_SUBSET_HELP = "Create a StackOps secrets subset and choose output conflicts with --on-conflict."
SECRETS_SEARCH_EPILOG = """Examples:
  devops vault search github personal-access-token
  devops vault search --interactive
  devops vault search --all-matches --json mail

Search displays bundle labels and environment keys without loading them; use devops vault load to define them.
Use --json to print matching secrets JSON, including values.
Use --all-matches to select every matching bundle.
Terms are case-insensitive substring matches; exact selectors are case-sensitive.
Use --interactive to select a bundle and --preview-secrets to show values in its preview.
When --source is omitted, --custom-path takes precedence; otherwise project is preferred over user.
The project file is .stackops/secrets/secrets.json at the repository root.
Use --source project/p, user/u, or all/a to select sources explicitly.
"""
SECRETS_LOAD_EPILOG = """Examples:
  devops vault load --name aws-dev --tag iam-access-key
  devops vault load --source user github token
  devops vault load --all-matches --source all cloudf

Load prepares environment variables for the calling shell.
Use --all-matches to select every matching bundle. Loading rejects conflicting values.
Terms are case-insensitive substring matches; exact selectors are case-sensitive.
Use --interactive to select a bundle and --preview-secrets to show values in its preview.
When --source is omitted, --custom-path takes precedence; otherwise project is preferred over user.
The project file is .stackops/secrets/secrets.json at the repository root.
Use --source project/p, user/u, or all/a to select sources explicitly.
"""


def stats(
    custom_path: Annotated[
        Path | None,
        typer.Option(
            "--custom-path", "-p", help="Use only this secrets JSON file, overriding --source."
        ),
    ] = None,
    secrets_source: Annotated[
        SecretsSource,
        typer.Option(
            "--source",
            "-s",
            case_sensitive=False,
            help="Secrets file source to read: project/p, user/u, or all/a. Ignored when --custom-path is provided.",
        ),
    ] = "all",
    details: Annotated[
        bool, typer.Option("--details", "-d", help="Show top non-secret labels such as tags and scopes. Secret values are never printed.")
    ] = False,
    show_paths: Annotated[bool, typer.Option("--show-paths", "-P", help="Include secrets file paths in the source table.")] = False,
    top: Annotated[int, typer.Option("--top", "-t", min=1, max=50, help="Number of tag/scope labels to show with --details.")] = 8,
) -> None:
    """📊 <t> Show aggregate StackOps secrets inventory stats without printing secret values."""
    from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_support import (
        load_secret_stats_from_sources,
        render_secret_stats,
        resolve_secret_sources,
    )

    secret_sources = resolve_secret_sources(secrets_path=custom_path, secrets_source=secrets_source)
    stats_rows = load_secret_stats_from_sources(secret_sources=secret_sources, show_paths=show_paths)
    render_secret_stats(stats_rows=stats_rows, details=details, show_paths=show_paths, top=top)


def subset(
    output_path: Annotated[Path, typer.Argument(help="Output secrets JSON path. Default mode creates a new file and refuses existing paths.")],
    custom_path: Annotated[
        Path | None,
        typer.Option(
            "--custom-path",
            "-p",
            help="Use only this secrets JSON file, overriding --source.",
        ),
    ] = None,
    secrets_source: Annotated[
        WritableSecretsSource,
        typer.Option(
            "--source", "-s", case_sensitive=False, help="Source secrets file to read: project/p or user/u. Ignored when --custom-path is provided."
        ),
    ] = "project",
    on_conflict: Annotated[
        cli_subset_support.SubsetOutputConflictOption,
        typer.Option(
            "--on-conflict", "-c", case_sensitive=False, help="How to handle an existing output path: throw-error/t, overwrite/o, or append/a."
        ),
    ] = "throw-error",
    preview_secrets: Annotated[bool, typer.Option("--preview-secrets", "-P", help="Include secret values in the interactive TV preview.")] = False,
) -> None:
    """📦 <u> Create a StackOps secrets subset and choose output conflicts with --on-conflict."""
    from stackops.scripts.python.helpers.helpers_devops import cli_config_secrets_actions as secret_actions
    from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_support import resolve_single_secret_source

    secret_source = resolve_single_secret_source(secrets_path=custom_path, secrets_source=secrets_source)
    resolved_output_path = cli_subset_support.resolve_subset_output_path(output_path)
    resolved_on_conflict = cli_subset_support.SUBSET_OUTPUT_CONFLICT_ACTIONS[on_conflict]
    secret_actions.subset_secrets_file(
        source_path=secret_source.path, output_path=resolved_output_path, on_conflict=resolved_on_conflict, preview_secrets=preview_secrets
    )


def add(
    custom_path: Annotated[
        Path | None,
        typer.Option(
            "--custom-path", "-p", help="Use only this secrets JSON file, overriding --source."
        ),
    ] = None,
    secrets_source: Annotated[
        WritableSecretsSource,
        typer.Option(
            "--source", "-s", case_sensitive=False, help="Secrets file source to update: project/p or user/u. Ignored when --custom-path is provided."
        ),
    ] = "project",
    create: Annotated[
        bool, typer.Option("--create", "-c", help="Allow creating a missing secrets JSON file and its schema.")
    ] = False,
) -> None:
    """➕ <a> Append a new login entry to a StackOps secrets file."""
    from stackops.scripts.python.helpers.helpers_devops import cli_config_secrets_actions as secret_actions
    from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_support import resolve_single_secret_source

    secret_source = resolve_single_secret_source(secrets_path=custom_path, secrets_source=secrets_source)
    secret_actions.add_secrets_entry(secrets_path=secret_source.path, create=create)


def get_app() -> typer.Typer:
    from stackops.scripts.python.helpers.helpers_devops import cli_vault
    from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_files import init_secrets, path_secrets, validate_secrets
    from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_search import load, search

    app = typer.Typer(
        name="vault", help=f"🔐 <v> {SECRETS_HELP}", no_args_is_help=True, add_help_option=True, add_completion=False,
        context_settings={"help_option_names": ["-h", "--help"]},
    )
    app.command("search", no_args_is_help=True, help=f"🔎 <s> {SECRETS_SEARCH_HELP}", epilog=SECRETS_SEARCH_EPILOG)(search)
    app.command("s", no_args_is_help=True, help="Alias for search.", epilog=SECRETS_SEARCH_EPILOG, hidden=True)(search)

    app.command("load", no_args_is_help=True, help=f"🔐 <l> {SECRETS_LOAD_HELP}", epilog=SECRETS_LOAD_EPILOG)(load)
    app.command("l", no_args_is_help=True, hidden=True)(load)

    app.command("stats", no_args_is_help=False, help=f"📊 <t> {SECRETS_STATS_HELP}")(stats)
    app.command("t", no_args_is_help=False, help="Alias for stats.", hidden=True)(stats)

    app.command("subset", no_args_is_help=True, help=f"📦 <u> {SECRETS_SUBSET_HELP}")(subset)
    app.command("u", no_args_is_help=True, help="Alias for subset.", hidden=True)(subset)

    app.command("add", no_args_is_help=False, help="➕ <a> Append a new login entry to a StackOps secrets file.")(add)
    app.command("a", no_args_is_help=False, help="Alias for add.", hidden=True)(add)

    app.command("path", help="📍 <p> Print secrets file and schema paths as JSON.")(path_secrets)
    app.command("p", hidden=True)(path_secrets)
    app.command("init", help="🆕 <i> Create a missing secrets file and its schema without opening an editor.")(init_secrets)
    app.command("i", hidden=True)(init_secrets)
    app.command("validate", help="✅ <v> Validate a secrets file without opening an editor.")(validate_secrets)
    app.command("v", hidden=True)(validate_secrets)

    app.add_typer(cli_vault.get_app(), name="bitwarden")
    app.add_typer(cli_vault.get_app(), name="k", hidden=True)

    return app
