from pathlib import Path
from typing import Annotated

import typer

from stackops.scripts.python.helpers.helpers_devops import cli_config_secrets_actions as secret_actions
from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_candidates import (
    SecretSelectors,
    resolve_candidate,
)
from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_support import (
    SECRETS_SCHEMA_FILENAME,
    SecretsSource,
    WritableSecretsSource,
    candidate_source_path,
    clean_optional_selector,
    clean_selector_values,
    echo_jq_login_entry_hint,
    echo_verbose_selection,
    fail,
    load_secret_candidates_from_sources,
    load_secret_stats_from_sources,
    render_secret_stats,
    resolve_secret_sources,
    resolve_single_secret_source,
)

SECRETS_HELP = "Manage StackOps secrets files and define env vars."
SECRETS_SEARCH_HELP = "Define env vars from StackOps secrets files."
SECRETS_STATS_HELP = "Show aggregate StackOps secrets inventory stats without printing secret values."
SECRETS_SUBSET_HELP = "Create a StackOps secrets subset and choose output conflicts with --on-conflict."
SECRETS_SEARCH_EPILOG = """Examples:
  devops config secrets search aws dev iam-access-key
  devops config secrets s github personal-access-token
  devops config secrets s AWS_ACCESS_KEY_ID
  devops config secrets search --interactive
  devops config secrets s -i aws
  devops config secrets search --verbose aws dev iam-access-key
  devops config secrets search --name aws-dev --tag iam-access-key
  devops config secrets search --name aws-dev --tag session-token
  devops config secrets search --source global bitwarden
  devops config secrets s --source g bitwarden
  devops config secrets search --source both github token
  devops config secrets s --source b github token
  devops config secrets s -i -P github
  devops config secrets search --path ~/private/team-secrets.json aws dev

Terms are case-insensitive substring matches. All terms must match somewhere across login
name/tags/accountName, secret name/tags/scopes, metadata, or env var keys.
Use search --interactive/-i to choose from matching logins with the TV fuzzy picker.
After interactive selection, StackOps prints a jq command for the selected login entry.
Use search --preview-secrets/-P with --interactive/-i to include secret values in the picker preview.
Use search --verbose/-v to print the selected bundle and env var keys without secret values.
Use search --source to choose the local file (local/l), global source-of-truth file (global/g), or both (both/b). Defaults to both.
With both, missing source files are warned and skipped as long as at least one source exists.
Exact selectors are case-sensitive and can be combined with terms for script-stable matching. Selector short aliases:
--secret-name/-N, --login-tag/-l, --secret-tag/-T, --scope/-S.
"""


def search(
    terms: Annotated[
        list[str] | None,
        typer.Argument(
            help=(
                "Case-insensitive terms used to select one secret bundle. All terms must match across login name/tags/accountName, "
                "secret name/tags/scopes, metadata, or env var keys."
            )
        ),
    ] = None,
    secrets_path: Annotated[
        Path | None,
        typer.Option(
            "--path", "-p", help="Override the local secrets JSON file path. Defaults to .stackops/secrets/secrets.json in the current directory."
        ),
    ] = None,
    secrets_source: Annotated[
        SecretsSource,
        typer.Option(
            "--source",
            "-s",
            case_sensitive=False,
            help="Secrets file source to read: local/l, global/g, or both/b. --path overrides the local source.",
        ),
    ] = "both",
    interactive: Annotated[
        bool,
        typer.Option("--interactive", "-i", help="Choose the secret bundle with a TV fuzzy picker. Terms and exact selectors pre-filter the list."),
    ] = False,
    preview_secrets: Annotated[
        bool, typer.Option("--preview-secrets", "-P", help="Include secret values in the interactive TV preview. Only applies with --interactive/-i.")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Print the selected secret bundle and env var keys without secret values.")
    ] = False,
    login_name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="Exact login name at entries[].name to require. Use with --tag/--key when a login has multiple secrets."),
    ] = None,
    secret_name: Annotated[str | None, typer.Option("--secret-name", "-N", help="Exact entries[].secrets[].name value to require.")] = None,
    tags: Annotated[
        list[str] | None, typer.Option("--tag", "--tags", "-t", help="Exact login or secret tag to require. Repeat for multiple tags.")
    ] = None,
    login_tags: Annotated[
        list[str] | None, typer.Option("--login-tag", "-l", help="Exact login tag at entries[].tags to require. Repeat for multiple tags.")
    ] = None,
    secret_tags: Annotated[
        list[str] | None, typer.Option("--secret-tag", "-T", help="Exact entries[].secrets[].tags value to require. Repeat for multiple tags.")
    ] = None,
    scopes: Annotated[
        list[str] | None, typer.Option("--scope", "-S", help="Exact entries[].secrets[].scopes value to require. Repeat for multiple scopes.")
    ] = None,
    keys: Annotated[
        list[str] | None, typer.Option("--key", "-k", help="Exact env var key in keyValues to require. Repeat for multiple keys.")
    ] = None,
) -> None:
    """🔐 <S> Define env vars from StackOps secrets files."""
    if preview_secrets and not interactive:
        fail("--preview-secrets only applies with --interactive/-i.")

    secret_sources = resolve_secret_sources(secrets_path=secrets_path, secrets_source=secrets_source)
    candidates = load_secret_candidates_from_sources(secret_sources)
    selectors = SecretSelectors(
        login_name=clean_optional_selector(login_name),
        secret_name=clean_optional_selector(secret_name),
        tags=clean_selector_values(tags),
        login_tags=clean_selector_values(login_tags),
        secret_tags=clean_selector_values(secret_tags),
        scopes=clean_selector_values(scopes),
        keys=clean_selector_values(keys),
    )
    candidate = resolve_candidate(candidates=candidates, terms=terms, selectors=selectors, interactive=interactive, preview_secrets=preview_secrets)
    selected_source_path = candidate_source_path(candidate=candidate, secret_sources=secret_sources)
    if interactive:
        echo_jq_login_entry_hint(candidate=candidate, secrets_path=selected_source_path)
    secret_actions.validate_env_names(candidate.key_values)
    secret_actions.write_env_handoff(candidate.key_values)
    if verbose:
        echo_verbose_selection(candidate=candidate, secrets_path=selected_source_path)

    names = ", ".join(candidate.key_values)
    msg = typer.style("✅ Success: ", fg=typer.colors.GREEN) + f"Prepared {len(candidate.key_values)} env variable(s)"
    if names:
        msg += f": {names}"
    else:
        msg += "."
    typer.echo(msg)


def stats(
    secrets_path: Annotated[
        Path | None,
        typer.Option(
            "--path", "-p", help="Override the local secrets JSON file path. Defaults to .stackops/secrets/secrets.json in the current directory."
        ),
    ] = None,
    secrets_source: Annotated[
        SecretsSource,
        typer.Option(
            "--source",
            "-s",
            case_sensitive=False,
            help="Secrets file source to read: local/l, global/g, or both/b. --path overrides the local source.",
        ),
    ] = "both",
    details: Annotated[
        bool,
        typer.Option("--details", "-d", help="Show top non-secret labels such as tags and scopes. Secret values are never printed."),
    ] = False,
    show_paths: Annotated[
        bool,
        typer.Option("--show-paths", "-P", help="Include secrets file paths in the source table."),
    ] = False,
    top: Annotated[
        int,
        typer.Option("--top", "-t", min=1, max=50, help="Number of tag/scope labels to show with --details."),
    ] = 8,
) -> None:
    """📊 <t> Show aggregate StackOps secrets inventory stats without printing secret values."""
    secret_sources = resolve_secret_sources(secrets_path=secrets_path, secrets_source=secrets_source)
    stats_rows = load_secret_stats_from_sources(secret_sources=secret_sources, show_paths=show_paths)
    render_secret_stats(stats_rows=stats_rows, details=details, show_paths=show_paths, top=top)


def subset(
    output_path: Annotated[
        Path,
        typer.Argument(help="Output secrets JSON path. Default mode creates a new file and refuses existing paths."),
    ],
    secrets_path: Annotated[
        Path | None,
        typer.Option(
            "--path", "-p", help="Override the local source secrets JSON file path. Defaults to .stackops/secrets/secrets.json in the current directory."
        ),
    ] = None,
    secrets_source: Annotated[
        WritableSecretsSource,
        typer.Option(
            "--source",
            "-s",
            case_sensitive=False,
            help="Source secrets file to read: local/l or global/g. --path overrides the local source.",
        ),
    ] = "local",
    on_conflict: Annotated[
        secret_actions.SubsetOutputConflictOption,
        typer.Option(
            "--on-conflict",
            "-o",
            case_sensitive=False,
            help="How to handle an existing output path: throw-error/t, overwrite/o, or append/a.",
        ),
    ] = "throw-error",
    preview_secrets: Annotated[
        bool,
        typer.Option("--preview-secrets", "-P", help="Include secret values in the interactive TV preview."),
    ] = False,
) -> None:
    """📦 <u> Create a StackOps secrets subset and choose output conflicts with --on-conflict."""
    secret_source = resolve_single_secret_source(secrets_path=secrets_path, secrets_source=secrets_source)
    resolved_output_path = _resolve_output_path(output_path)
    resolved_on_conflict = secret_actions.resolve_subset_output_conflict_action(on_conflict=on_conflict)
    secret_actions.subset_secrets_file(
        source_path=secret_source.path,
        output_path=resolved_output_path,
        on_conflict=resolved_on_conflict,
        preview_secrets=preview_secrets,
    )


def add(
    secrets_path: Annotated[
        Path | None,
        typer.Option(
            "--path", "-p", help="Override the local secrets JSON file path. Defaults to .stackops/secrets/secrets.json in the current directory."
        ),
    ] = None,
    secrets_source: Annotated[
        WritableSecretsSource,
        typer.Option(
            "--source",
            "-s",
            case_sensitive=False,
            help="Secrets file source to update: local/l or global/g. --path overrides the local source.",
        ),
    ] = "local",
    create: Annotated[
        bool,
        typer.Option("--create", "-c", help=f"Allow creating a missing secrets JSON file and {SECRETS_SCHEMA_FILENAME}."),
    ] = False,
) -> None:
    """➕ <a> Append a new login entry to a StackOps secrets file."""
    secret_source = resolve_single_secret_source(secrets_path=secrets_path, secrets_source=secrets_source)
    secret_actions.add_secrets_entry(secrets_path=secret_source.path, create=create)


def edit(
    secrets_path: Annotated[
        Path | None,
        typer.Option(
            "--path", "-p", help="Override the local secrets JSON file path. Defaults to .stackops/secrets/secrets.json in the current directory."
        ),
    ] = None,
    secrets_source: Annotated[
        WritableSecretsSource,
        typer.Option(
            "--source",
            "-s",
            case_sensitive=False,
            help="Secrets file source to edit: local/l or global/g. --path overrides the local source.",
        ),
    ] = "local",
    create: Annotated[
        bool,
        typer.Option("--create", "-c", help=f"Allow creating a missing secrets JSON file and {SECRETS_SCHEMA_FILENAME}."),
    ] = False,
    editor: Annotated[str, typer.Option("--editor", "-E", help="Editor to use. Defaults to hx.")] = "hx",
) -> None:
    """📝 <e> Open a StackOps secrets file for editing."""
    secret_source = resolve_single_secret_source(secrets_path=secrets_path, secrets_source=secrets_source)
    secret_actions.edit_secrets_file(secrets_path=secret_source.path, editor=editor, create=create)


def get_app() -> typer.Typer:
    app = typer.Typer(
        name="secrets",
        help=f"🔐 <S> {SECRETS_HELP}",
        no_args_is_help=True,
        add_help_option=True,
        add_completion=False,
    )
    app.command("search", no_args_is_help=True, help=f"🔎 <s> {SECRETS_SEARCH_HELP}", epilog=SECRETS_SEARCH_EPILOG)(search)
    app.command("s", no_args_is_help=True, help="Alias for search.", epilog=SECRETS_SEARCH_EPILOG, hidden=True)(search)

    app.command("stats", no_args_is_help=False, help=f"📊 <t> {SECRETS_STATS_HELP}")(stats)
    app.command("t", no_args_is_help=False, help="Alias for stats.", hidden=True)(stats)

    app.command("subset", no_args_is_help=True, help=f"📦 <u> {SECRETS_SUBSET_HELP}")(subset)
    app.command("u", no_args_is_help=True, help="Alias for subset.", hidden=True)(subset)

    app.command("add", no_args_is_help=False, help="➕ <a> Append a new login entry to a StackOps secrets file.")(add)
    app.command("a", no_args_is_help=False, help="Alias for add.", hidden=True)(add)

    app.command("edit", no_args_is_help=False, help="📝 <e> Open a StackOps secrets file for editing.")(edit)
    app.command("e", no_args_is_help=False, help="Alias for edit.", hidden=True)(edit)

    return app


def _resolve_output_path(output_path: Path) -> Path:
    expanded_path = output_path.expanduser()
    if expanded_path.is_absolute():
        return expanded_path
    return Path.cwd() / expanded_path
