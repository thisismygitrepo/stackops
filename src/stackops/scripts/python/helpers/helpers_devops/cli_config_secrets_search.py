from pathlib import Path
from typing import Annotated

import typer

from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_constants import SecretsSource
from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_selection import select_secrets


def search(
    terms: Annotated[
        list[str] | None,
        typer.Argument(
            help=(
                "Case-insensitive terms used to match secret bundles. All terms must match across login name/tags/accountName, "
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
        SecretsSource | None,
        typer.Option(
            "--source",
            "-s",
            case_sensitive=False,
            help=(
                "Secrets file source to read: local/l, global/g, or both/b. "
                "When omitted, --path is used if provided; otherwise local is preferred and global is used when local is absent."
            ),
        ),
    ] = None,
    interactive: Annotated[
        bool,
        typer.Option("--interactive", "-i", help="Choose the secret bundle with a TV fuzzy picker. Terms and exact selectors pre-filter the list."),
    ] = False,
    all_matches: Annotated[
        bool,
        typer.Option(
            "--all-matches",
            "-a",
            help=("Select every matching secret bundle. Loading fails if bundles assign different values to one environment variable."),
        ),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json", "-j", help="Print matching entries as JSON, including secret values, without loading environment variables."
        ),
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
    select_secrets(
        terms=terms, secrets_path=secrets_path, secrets_source=secrets_source,
        interactive=interactive, all_matches=all_matches, json_output=json_output,
        preview_secrets=preview_secrets, verbose=verbose, login_name=login_name,
        secret_name=secret_name, tags=tags, login_tags=login_tags, secret_tags=secret_tags,
        scopes=scopes, keys=keys, load_environment=False,
    )


def load(
    terms: Annotated[
        list[str] | None,
        typer.Argument(
            help=(
                "Case-insensitive terms used to match secret bundles. All terms must match across login name/tags/accountName, "
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
        SecretsSource | None,
        typer.Option(
            "--source",
            "-s",
            case_sensitive=False,
            help=(
                "Secrets file source to read: local/l, global/g, or both/b. "
                "When omitted, --path is used if provided; otherwise local is preferred and global is used when local is absent."
            ),
        ),
    ] = None,
    interactive: Annotated[
        bool,
        typer.Option("--interactive", "-i", help="Choose the secret bundle with a TV fuzzy picker. Terms and exact selectors pre-filter the list."),
    ] = False,
    all_matches: Annotated[
        bool,
        typer.Option(
            "--all-matches",
            "-a",
            help=("Select every matching secret bundle. Loading fails if bundles assign different values to one environment variable."),
        ),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json", "-j", help="Print matching entries as JSON, including secret values, without loading environment variables."
        ),
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
    select_secrets(
        terms=terms, secrets_path=secrets_path, secrets_source=secrets_source,
        interactive=interactive, all_matches=all_matches, json_output=json_output,
        preview_secrets=preview_secrets, verbose=verbose, login_name=login_name,
        secret_name=secret_name, tags=tags, login_tags=login_tags, secret_tags=secret_tags,
        scopes=scopes, keys=keys, load_environment=True,
    )
