from typing import Annotated

import typer

DEFAULT_BITWARDEN_LOGIN_NAME = "bitwarden"


def _raise_typer_exit(exc: Exception) -> None:
    code = getattr(exc, "code", 1)
    raise typer.Exit(code=code if isinstance(code, int) else 1) from exc


def search(
    name: Annotated[str, typer.Argument(..., help="Name (or part of the name) of the credential to retrieve")],
    copy: Annotated[
        str,
        typer.Option(
            "--copy",
            "-c",
            show_default=True,
            help="Which field to copy to clipboard (password, username, totp, none)",
            show_choices=True,
            case_sensitive=False,
        ),
    ] = "password",
    sync: Annotated[bool, typer.Option("--sync", "-S", help="Sync vault with server before searching and bypass the local search cache")] = False,
    show: Annotated[bool, typer.Option("--show", "-s", help="Show credentials in terminal (insecure)")] = False,
    use_totp: Annotated[bool, typer.Option("--totp/--no-totp", "-t/-T", help="Attempt to fetch TOTP if present")] = True,
    username_slot: Annotated[int, typer.Option("--username-slot", "-u", help="Clipboard slot for username")] = 0,
    password_slot: Annotated[int, typer.Option("--password-slot", "-p", help="Clipboard slot for password")] = 1,
    totp_slot: Annotated[int, typer.Option("--totp-slot", "-P", help="Clipboard slot for TOTP")] = 2,
    json_slot: Annotated[int, typer.Option("--json-slot", "-J", help="Clipboard slot for full JSON result")] = 3,
    silent: Annotated[bool, typer.Option("--silent", "-q", help="Suppress all progress/status output; only the final result is printed")] = False,
    json_output: Annotated[bool, typer.Option("--json", "--json-output", "-j", help="Output selected credentials as JSON (includes notes)")] = False,
    raw_output: Annotated[bool, typer.Option("--raw", "-r", help="Output raw search results JSON exactly as returned by bw")] = False,
    fresh: Annotated[bool, typer.Option("--fresh", "-f", help="Bypass cache and query Bitwarden directly")] = False,
) -> None:
    """Retrieve credentials from Bitwarden (`bw`) and optionally copy them to the clipboard."""
    from stackops.scripts.python.helpers.helpers_devops import vault

    try:
        vault.search(
            name=name,
            copy=copy,
            sync=sync,
            show=show,
            use_totp=use_totp,
            username_slot=username_slot,
            password_slot=password_slot,
            totp_slot=totp_slot,
            json_slot=json_slot,
            silent=silent,
            json_output=json_output,
            raw_output=raw_output,
            fresh=fresh,
        )
    except vault.VaultExit as exc:
        _raise_typer_exit(exc)


def login_and_unlock(
    account_name: Annotated[
        str | None,
        typer.Option("--account-name", "-a", help="Optional StackOps secrets accountName that stores the Bitwarden credentials."),
    ] = None,
    login_name: Annotated[
        str, typer.Option("--login-name", "-n", help="StackOps secrets login name that stores the Bitwarden API credentials.", show_default=True)
    ] = DEFAULT_BITWARDEN_LOGIN_NAME,
) -> None:
    """Authenticate with Bitwarden and persist a local BW_SESSION token."""
    from stackops.scripts.python.helpers.helpers_devops import vault

    try:
        vault.login_and_unlock(account_name=account_name, login_name=login_name)
    except vault.VaultExit as exc:
        _raise_typer_exit(exc)


def clean_cache() -> None:
    """Remove cached vault data under ~/tmp_results."""
    from stackops.scripts.python.helpers.helpers_devops import vault

    try:
        vault.clean_cache()
    except vault.VaultExit as exc:
        _raise_typer_exit(exc)


def get_app() -> typer.Typer:
    app = typer.Typer(
        name="vault",
        help="🔐 <v> Search Bitwarden credentials and manage login/unlock session state.",
        no_args_is_help=True,
        add_help_option=True,
        add_completion=False,
    )
    app.command("search", no_args_is_help=True, help="<s> Retrieve credentials from Bitwarden CLI and optionally copy them to the clipboard.")(search)
    app.command("s", no_args_is_help=True, help="Alias for search.", hidden=True)(search)

    app.command(
        "login-and-unlock",
        no_args_is_help=False,
        help="<l> Log in with Bitwarden API credentials from StackOps secrets, unlock the vault, and persist BW_SESSION locally.",
    )(login_and_unlock)
    app.command("l", no_args_is_help=False, help="Alias for login-and-unlock.", hidden=True)(login_and_unlock)

    app.command("clean-cache", help="<c> Remove encrypted vault cache stored under ~/tmp_results.")(clean_cache)
    app.command("c", help="Alias for clean-cache.", hidden=True)(clean_cache)

    return app
