from typing import Annotated

import typer

from stackops.scripts.python.helpers.helpers_devops.vault_constants import BitwardenCopyField

DEFAULT_BITWARDEN_LOGIN_NAME = "bitwarden"
BITWARDEN_SEARCH_EPILOG = """Examples:
  devops vault bitwarden search github
  devops vault bitwarden search github --copy password
  devops vault bitwarden search --interactive --copy totp
  devops vault bitwarden search --load github-token
  devops vault bitwarden search --all-matches --json mail

Search lists matching items without secret values and does nothing else.
Add --copy/-C to put one field on the system clipboard, --load/-L to define the item's variables in the calling shell, or --show/-w to print credentials.
The name must identify one item; use --interactive to pick one, --id for an exact item, or --all-matches for every match.
Use --json to print the selected items as JSON, including values.
"""
BITWARDEN_LOAD_EPILOG = """Examples:
  devops vault bitwarden load github-token
  devops vault bitwarden load --command 'gh auth status' github-token
  devops vault bitwarden load --interactive

Each custom field of the item becomes one environment variable: the field name is the variable name.
A linked custom field takes the login's username or password as its value.
Load prepares the variables for the calling shell, or with --command runs one program with them.
The name must identify one item; use --interactive to pick one, --id for an exact item, or --all-matches for every match.
"""


def _raise_typer_exit(exc: Exception) -> None:
    code = getattr(exc, "code", 1)
    raise typer.Exit(code=code if isinstance(code, int) else 1) from exc


def search(
    name: Annotated[str | None, typer.Argument(help="Item name or substring; omit with --id, --interactive, or --all-matches.")] = None,
    copy: Annotated[
        BitwardenCopyField | None,
        typer.Option(
            "--copy",
            "-C",
            case_sensitive=False,
            help="Copy one field of the selected item to the system clipboard: password, username, or totp. The clipboard is cleared soon after, unless something else was copied by then.",
        ),
    ] = None,
    load_environment: Annotated[
        bool,
        typer.Option("--load", "-L", help="After listing, define the selected item's custom fields as environment variables in the calling shell, as devops vault bitwarden load does."),
    ] = False,
    interactive: Annotated[bool, typer.Option("--interactive", "-i", help="Choose the item with a TV fuzzy picker. The name pre-filters the list.")] = False,
    all_matches: Annotated[bool, typer.Option("--all-matches", "-a", help="Select every matching item; allows omitting the name to list the whole vault.")] = False,
    item_id: Annotated[str | None, typer.Option("--id", "-I", help="Select one exact Bitwarden item ID instead of searching by name.")] = None,
    json_output: Annotated[
        bool, typer.Option("--json", "-j", help="Print the selected items as a JSON array, including secret values and notes. Cannot be combined with --copy, --load, --show, or --interactive.")
    ] = False,
    raw_output: Annotated[bool, typer.Option("--raw", "-r", help="Print the selected items as JSON exactly as returned by bw, including secret values.")] = False,
    show: Annotated[bool, typer.Option("--show", "-w", help="Show the selected item's credentials in the terminal (insecure).")] = False,
    no_totp: Annotated[bool, typer.Option("--no-totp", "-o", help="Skip fetching TOTP codes for --json and --show.")] = False,
    fresh: Annotated[bool, typer.Option("--fresh", "-f", help="Bypass the local search cache and query Bitwarden directly.")] = False,
    sync: Annotated[bool, typer.Option("--sync", "-y", help="Sync the vault with the server before searching and bypass the local search cache.")] = False,
    silent: Annotated[bool, typer.Option("--silent", "-q", help="Suppress progress and hints; only results are printed.")] = False,
) -> None:
    """Inspect Bitwarden (`bw`) items without exposing secrets; copying, loading and showing are explicit."""
    from stackops.scripts.python.helpers.helpers_devops import vault, vault_search

    try:
        vault_search.search(
            vault_search.ItemQuery(name=name, item_id=item_id, interactive=interactive, all_matches=all_matches, fresh=fresh, sync=sync, silent=silent),
            json_output=json_output,
            raw_output=raw_output,
            copy_field=copy,
            load_environment=load_environment,
            show=show,
            use_totp=not no_totp,
        )
    except vault.VaultExit as exc:
        _raise_typer_exit(exc)


def load(
    name: Annotated[str | None, typer.Argument(help="Item name or substring; omit with --id, --interactive, or --all-matches.")] = None,
    command: Annotated[str | None, typer.Option("--command", "-c", help="Run a quoted command with the selected environment. Parsed as arguments, without a shell.")] = None,
    interactive: Annotated[bool, typer.Option("--interactive", "-i", help="Choose the item with a TV fuzzy picker. The name pre-filters the list.")] = False,
    all_matches: Annotated[
        bool, typer.Option("--all-matches", "-a", help="Select every matching item. Loading fails if items assign different values to one environment variable.")
    ] = False,
    item_id: Annotated[str | None, typer.Option("--id", "-I", help="Select one exact Bitwarden item ID instead of searching by name.")] = None,
    fresh: Annotated[bool, typer.Option("--fresh", "-f", help="Bypass the local search cache and query Bitwarden directly.")] = False,
    sync: Annotated[bool, typer.Option("--sync", "-y", help="Sync the vault with the server before searching and bypass the local search cache.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Print the selected items and env var keys without secret values.")] = False,
) -> None:
    """Load a Bitwarden item's custom fields into environment variables."""
    from stackops.scripts.python.helpers.helpers_devops import vault, vault_search

    try:
        vault_search.load(
            vault_search.ItemQuery(name=name, item_id=item_id, interactive=interactive, all_matches=all_matches, fresh=fresh, sync=sync, silent=not verbose),
            command=command,
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


def export_session() -> None:
    """Define the saved BW_SESSION in the calling shell."""
    from stackops.scripts.python.helpers.helpers_devops import vault

    try:
        vault.export_session()
    except vault.VaultExit as exc:
        _raise_typer_exit(exc)


def sync() -> None:
    """Sync the Bitwarden vault with the server and refresh cached search results."""
    from stackops.scripts.python.helpers.helpers_devops import vault

    try:
        vault.sync()
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
        name="bitwarden",
        help="🔐 <b> Manage Bitwarden credentials and vault sessions.",
        no_args_is_help=True,
        add_help_option=True,
        add_completion=False,
        context_settings={"help_option_names": ["-h", "--help"]},
    )
    app.command(
        "search", no_args_is_help=True, help="🔎 <s> Inspect matching Bitwarden items; add --copy or --load to also deliver them.", epilog=BITWARDEN_SEARCH_EPILOG
    )(search)
    app.command("s", no_args_is_help=True, help="Alias for search.", epilog=BITWARDEN_SEARCH_EPILOG, hidden=True)(search)

    app.command("load", no_args_is_help=True, help="🔐 <L> Load a Bitwarden item's custom fields into environment variables.", epilog=BITWARDEN_LOAD_EPILOG)(load)
    app.command("L", no_args_is_help=True, help="Alias for load.", epilog=BITWARDEN_LOAD_EPILOG, hidden=True)(load)

    app.command(
        "login-and-unlock",
        no_args_is_help=False,
        help="🔑 <l> Log in with Bitwarden API credentials from StackOps secrets, unlock the vault, and persist BW_SESSION locally.",
    )(login_and_unlock)
    app.command("l", no_args_is_help=False, help="Alias for login-and-unlock.", hidden=True)(login_and_unlock)

    app.command(
        "export-session",
        help="🔓 <e> Define the saved BW_SESSION in the calling shell, the way load defines variables.",
    )(export_session)
    app.command("e", help="Alias for export-session.", hidden=True)(export_session)

    app.command("sync", help="🔄 <S> Sync the Bitwarden vault with the server and refresh cached searches.")(sync)
    app.command("S", help="Alias for sync.", hidden=True)(sync)

    app.command("clean-cache", help="🧹 <c> Remove encrypted vault cache stored under ~/tmp_results.")(clean_cache)
    app.command("c", help="Alias for clean-cache.", hidden=True)(clean_cache)

    return app
