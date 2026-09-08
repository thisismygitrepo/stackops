import shlex
from pathlib import Path
from typing import Annotated

import typer

from stackops.secrets.paths import SECRETS_DOFILE
from stackops.utils.cli_utils.alias_markers import apply_alias_markers
from stackops.utils.cloud.onedrive.accounts import add_account as add_defined_account
from stackops.utils.cloud.onedrive.accounts import list_accounts as list_defined_accounts
from stackops.utils.cloud.onedrive.auth import authenticate as authenticate_account
from stackops.utils.cloud.onedrive.file_ops import delete_item as delete_remote_item
from stackops.utils.cloud.onedrive.file_ops import download_file as download_remote_file
from stackops.utils.cloud.onedrive.file_ops import upload_file as upload_local_file
from stackops.utils.cloud.onedrive.errors import run_cli
from stackops.utils.cloud.onedrive.items import list_items as list_remote_items
from stackops.utils.cloud.onedrive.items import search_items as search_remote_items
from stackops.utils.cloud.onedrive.items import show_status as show_account_status
from stackops.utils.cloud.onedrive.output import print_table


ACCOUNT_NAME_HELP = "OneDrive CLI account name. Run 'cloud onedrive accounts' to list configured names. Omit to use the only configured account or enter it interactively."


def resolve_account_name(account_name: str | None) -> str:
    if account_name is not None:
        return account_name
    accounts = run_cli(lambda: list_defined_accounts(SECRETS_DOFILE))
    if len(accounts) == 1:
        return accounts[0].account_name
    return str(typer.prompt("OneDrive account name"))


def add_account(
    account_name: Annotated[
        str | None,
        typer.Argument(help="Unique name for this OneDrive account. Omit to enter it interactively."),
    ] = None,
    client_id: Annotated[
        str | None,
        typer.Option("--client-id", help="Microsoft Application (client) ID. Omit to enter it interactively."),
    ] = None,
) -> None:
    resolved_account_name = str(typer.prompt("OneDrive account name")) if account_name is None else account_name
    resolved_client_id = str(typer.prompt("Microsoft Application (client) ID")) if client_id is None else client_id
    run_cli(lambda: add_defined_account(secrets_path=SECRETS_DOFILE, account_name=resolved_account_name, client_id=resolved_client_id))
    typer.echo(f"Added OneDrive CLI account {resolved_account_name!r} to {SECRETS_DOFILE}.")
    typer.echo(f"Next: cloud onedrive auth {shlex.quote(resolved_account_name)}")


def show_accounts() -> None:
    accounts = run_cli(lambda: list_defined_accounts(SECRETS_DOFILE))
    if not accounts:
        typer.echo("No OneDrive CLI accounts are defined.")
        return
    print_table(
        headers=("ACCOUNT", "AUTHENTICATION"),
        rows=((account.account_name, account.authentication) for account in accounts),
    )


def authenticate(account_name: Annotated[str | None, typer.Argument(help=ACCOUNT_NAME_HELP)] = None) -> None:
    resolved = resolve_account_name(account_name)
    run_cli(lambda: authenticate_account(resolved))


def show_status(account_name: Annotated[str | None, typer.Argument(help=ACCOUNT_NAME_HELP)] = None) -> None:
    resolved = resolve_account_name(account_name)
    run_cli(lambda: show_account_status(resolved))


def list_items(
    remote_path: Annotated[str, typer.Argument(help="Remote folder path.")] = "/",
    account_name: Annotated[str | None, typer.Argument(help=ACCOUNT_NAME_HELP)] = None,
) -> None:
    resolved = resolve_account_name(account_name)
    run_cli(lambda: list_remote_items(resolved, remote_path))


def search_items(
    query: Annotated[str, typer.Argument(help="Text to search for.")],
    output_json: Annotated[bool, typer.Option("--json", "-j", help="Output JSON.")] = False,
    account_name: Annotated[str | None, typer.Argument(help=ACCOUNT_NAME_HELP)] = None,
) -> None:
    resolved = resolve_account_name(account_name)
    run_cli(lambda: search_remote_items(resolved, query, output_json))


def download_file(
    remote_path: Annotated[str, typer.Argument(help="Remote file path.")],
    local_path: Annotated[Path, typer.Argument(help="New local file path.")],
    account_name: Annotated[str | None, typer.Argument(help=ACCOUNT_NAME_HELP)] = None,
) -> None:
    resolved = resolve_account_name(account_name)
    run_cli(lambda: download_remote_file(resolved, remote_path, local_path))


def upload_file(
    local_path: Annotated[Path, typer.Argument(help="Existing local file path.")],
    remote_path: Annotated[str, typer.Argument(help="Remote target path.")],
    overwrite: Annotated[bool, typer.Option("--overwrite", "-o", help="Replace an existing remote item.")] = False,
    account_name: Annotated[str | None, typer.Argument(help=ACCOUNT_NAME_HELP)] = None,
) -> None:
    resolved = resolve_account_name(account_name)
    run_cli(lambda: upload_local_file(resolved, local_path, remote_path, overwrite))


def delete_item(
    remote_path: Annotated[str, typer.Argument(help="Remote item path.")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip the confirmation prompt.")] = False,
    account_name: Annotated[str | None, typer.Argument(help=ACCOUNT_NAME_HELP)] = None,
) -> None:
    resolved = resolve_account_name(account_name)
    run_cli(lambda: delete_remote_item(resolved, remote_path, yes))


def config_path() -> None:
    typer.echo(SECRETS_DOFILE)


def get_app() -> typer.Typer:
    app = typer.Typer(add_completion=False, help="Access OneDrive through Microsoft Graph.", no_args_is_help=True, pretty_exceptions_enable=False)

    app.command("auth", short_help="Authenticate with Microsoft.")(authenticate)
    app.command("a", hidden=True)(authenticate)
    app.command("status", short_help="Show account and storage status.")(show_status)
    app.command("t", hidden=True)(show_status)
    app.command("accounts", short_help="List defined OneDrive CLI accounts.")(show_accounts)
    app.command("r", hidden=True)(show_accounts)
    app.command("ls", short_help="List a remote folder.")(list_items)
    app.command("l", hidden=True)(list_items)
    app.command("search", short_help="Search the drive.")(search_items)
    app.command("s", hidden=True)(search_items)
    app.command("download", short_help="Download a remote file.")(download_file)
    app.command("w", hidden=True)(download_file)
    app.command("upload", short_help="Upload a local file.")(upload_file)
    app.command("u", hidden=True)(upload_file)
    app.command("delete", short_help="Move an item to the recycle bin.")(delete_item)
    app.command("d", hidden=True)(delete_item)
    app.command("config-path", short_help="Print the global StackOps secrets path.")(config_path)
    app.command("c", hidden=True)(config_path)
    app.command("add", short_help="Add a OneDrive CLI account. Prompt for omitted values.")(add_account)
    app.command("A", hidden=True)(add_account)

    return apply_alias_markers(app)
