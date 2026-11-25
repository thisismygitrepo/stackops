"""Bitwarden session, cache and login helpers.

Features
- Uses StackOps secrets selectors for Bitwarden login credentials
- Hands the session to `bw` through its environment, never on the command line
- Persists the latest Bitwarden session token to a local encrypted file
"""

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Sequence

from rich.console import Console
from rich.markup import escape
from rich.table import Table
from stackops.secrets.models import Login
from stackops.secrets.search import SecretsFileError, search_logins
from stackops.utils.io import GpgCommandError, decrypt_bytes_asymmetric, encrypt_bytes_asymmetric
from stackops.secrets.paths import SECRETS_DOFILE

# Keep the historical pwdmgr cache path so existing saved BW_SESSION tokens keep working.
TMP_RESULTS_ROOT = Path.home() / "tmp_results"
CACHE_PATH = Path.home() / "tmp_results/cache/pwdmgr/cache.json.gpg"
DEFAULT_BITWARDEN_LOGIN_NAME = "bitwarden"
DEFAULT_LOGIN_COMMAND = "devops vault bitwarden login-and-unlock [--account-name <accountName>] [--login-name <login_name>]"
BITWARDEN_SECRET_KEYS: tuple[str, str, str] = ("BW_CLIENTID", "BW_CLIENTSECRET", "BW_PASSWORD")


class VaultExit(Exception):
    """Raised by vault helpers when a CLI wrapper should exit with a status code."""

    def __init__(self, code: int = 1) -> None:
        super().__init__(f"vault command exited with code {code}")
        self.code = code


def load_encrypted_cache() -> dict[str, str]:
    if not CACHE_PATH.exists():
        return {}
    try:
        data = decrypt_bytes_asymmetric(CACHE_PATH.read_bytes())
        loaded = json.loads(data.decode("utf-8"))
        if not isinstance(loaded, dict):
            return {}
        # Only keep str->str pairs
        return {str(k): str(v) for k, v in loaded.items()}
    except (GpgCommandError, RuntimeError, json.JSONDecodeError, UnicodeDecodeError):
        return {}


def save_encrypted_cache(cache: dict[str, str]) -> None:
    data = json.dumps(cache).encode("utf-8")
    try:
        encrypted = encrypt_bytes_asymmetric(data)
    except (GpgCommandError, RuntimeError) as exc:
        err_console.print("[bold red]Could not save vault cache with StackOps GPG encryption.[/bold red]")
        hint = getattr(exc, "hint", None)
        if hint:
            err_console.print(f"[yellow]{hint}[/yellow]")
        raise VaultExit(code=1) from exc
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_bytes(encrypted)


def cache_get(key: str) -> str | None:
    cache = load_encrypted_cache()
    return cache.get(key)


def cache_set(key: str, value: str) -> None:
    cache = load_encrypted_cache()
    cache[key] = value
    save_encrypted_cache(cache)


def purge_cached_searches() -> None:
    """Drop cached `bw list items` results, e.g. after switching Bitwarden accounts."""
    cache = load_encrypted_cache()
    save_encrypted_cache({key: value for key, value in cache.items() if not key.startswith("search::")})


def prune_empty_directories(path: Path, *, stop: Path) -> None:
    """Remove empty cache directories up to, but not including, the stop path."""
    current = path.resolve(strict=False)
    stop = stop.resolve(strict=False)
    while current != stop and stop in current.parents:
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


console = Console()
err_console = Console(stderr=True)


@dataclass
class VaultItem:
    id: str
    name: str
    username: Optional[str]
    password: Optional[str]
    raw: dict[str, Any]


@dataclass
class BitwardenCredentials:
    login_name: str
    account_name: str | None
    client_id: str
    client_secret: str
    password: str


@dataclass
class VaultStatus:
    status: str
    user_email: str | None
    user_id: str | None
    server_url: str | None


def load_session_token_from_cache() -> str | None:
    return cache_get("BW_SESSION")


def persist_session_token_to_cache(session: str) -> None:
    cache_set("BW_SESSION", session)


def bw_environment(session: str | None) -> dict[str, str]:
    """Environment for a bw process; the session travels as BW_SESSION so it never shows in the process list."""
    environment = os.environ.copy()
    if session:
        environment["BW_SESSION"] = session
    return environment


def run_command(args: Sequence[str], *, env: Optional[dict[str, str]] = None, check: bool = False) -> subprocess.CompletedProcess[str]:
    """Run a subprocess command and optionally raise a vault command error."""
    try:
        return subprocess.run(list(args), stdin=subprocess.DEVNULL, capture_output=True, text=True, env=env, check=check)
    except FileNotFoundError as exc:
        err_console.print(f"[bold red]Command not found:[/bold red] {' '.join(args)}")
        raise VaultExit(code=1) from exc
    except subprocess.CalledProcessError as exc:
        err_console.print(f"[bold red]Command failed:[/bold red] {' '.join(args)}")
        if exc.stderr:
            err_console.print("[red]stderr:[/red]", exc.stderr.strip())
        if exc.stdout:
            err_console.print("[red]stdout:[/red]", exc.stdout.strip())
        raise VaultExit(code=1) from exc


def get_vault_status_field(status_payload: dict[str, Any], key: str) -> str | None:
    value = status_payload.get(key)
    if isinstance(value, str) and value:
        return value
    return None


def get_vault_status(session: Optional[str] = None) -> VaultStatus:
    """Return the bw vault status and authenticated account metadata when available."""
    try:
        result = subprocess.run(["bw", "status"], stdin=subprocess.DEVNULL, capture_output=True, text=True, env=bw_environment(session), check=False)
        data = json.loads(result.stdout)
        status = data.get("status")
        return VaultStatus(
            status=status if isinstance(status, str) and status else "unknown",
            user_email=get_vault_status_field(data, "userEmail"),
            user_id=get_vault_status_field(data, "userId"),
            server_url=get_vault_status_field(data, "serverUrl"),
        )
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return VaultStatus(status="unknown", user_email=None, user_id=None, server_url=None)


def get_vault_account_details(vault_status: VaultStatus) -> list[tuple[str, str]]:
    details: list[tuple[str, str]] = []
    if vault_status.user_email:
        details.append(("Account", vault_status.user_email))
    if vault_status.user_id:
        details.append(("User ID", vault_status.user_id))
    return details


def run_bw_command(args: Sequence[str], *, env: Optional[dict[str, str]] = None) -> str:
    """Run a bw CLI command and return stdout (text). Raises VaultExit on failure."""
    return run_command(args, env=env, check=True).stdout


def ensure_vault_accessible(vault_status: VaultStatus) -> None:
    """Raise VaultExit with actionable guidance when the vault cannot serve `bw` queries."""
    status = vault_status.status
    if status == "locked":
        message_lines = ["[bold red]🔒 Vault is locked.[/bold red]"]
        for label, value in get_vault_account_details(vault_status):
            message_lines.append(f"[dim]{label}:[/dim] [bold]{escape(value)}[/bold]")
        message_lines.append(f"[dim]Next:[/dim] Run [bold]{DEFAULT_LOGIN_COMMAND}[/bold] or save a valid session token using the CLI.")
        err_console.print("\n".join(message_lines))
        raise VaultExit(code=1)
    if status == "unauthenticated":
        err_console.print(f"[bold red]🔒 Not logged in to Bitwarden.[/bold red] Run [bold]{DEFAULT_LOGIN_COMMAND}[/bold] first.")
        raise VaultExit(code=1)


def parse_items(raw: str) -> List[VaultItem]:
    """Parse the JSON returned by `bw list items` into VaultItem objects."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        err_console.print("[bold red]Failed to parse JSON from bw output.[/bold red]")
        err_console.print(exc)
        raise VaultExit(code=1) from exc

    items: List[VaultItem] = []
    for it in data:
        login = it.get("login", {}) or {}
        items.append(
            VaultItem(id=it.get("id", ""), name=it.get("name", "<unnamed>"), username=login.get("username"), password=login.get("password"), raw=it)
        )
    return items


def get_item_notes(raw_item: dict[str, Any]) -> Optional[str]:
    """Return item notes when present."""
    notes = raw_item.get("notes")
    return notes if isinstance(notes, str) and notes else None


def load_bitwarden_credentials(login_name: str, account_name: str | None = None) -> BitwardenCredentials:
    """Load one Bitwarden credential bundle from StackOps secrets."""
    try:
        logins = search_logins(path=SECRETS_DOFILE, login_name=login_name, account_name=account_name, keys=BITWARDEN_SECRET_KEYS)
    except SecretsFileError as exc:
        err_console.print("[bold red]Could not load StackOps secrets.[/bold red]")
        err_console.print(str(exc))
        raise VaultExit(code=2) from exc

    selection = _format_bitwarden_secret_selection(login_name=login_name, account_name=account_name)
    if not logins:
        expected_entry: Login = {
            "name": login_name,
            "secrets": [
                {
                    "name": "api-login",
                    "tags": [],
                    "scopes": [],
                    "keyValues": {
                        "BW_CLIENTID": "<bitwarden-client-id>",
                        "BW_CLIENTSECRET": "<bitwarden-client-secret>",
                        "BW_PASSWORD": "<bitwarden-master-password>",
                    },
                }
            ],
        }
        if account_name is not None:
            expected_entry["accountName"] = account_name
        err_console.print(f"[bold red]Bitwarden credentials not found in StackOps secrets.[/bold red] {selection}")
        err_console.print(f"Expected {SECRETS_DOFILE} to contain a login entry shaped like:", markup=False)
        err_console.print(json.dumps(expected_entry, indent=2), markup=False)
        raise VaultExit(code=2)
    if len(logins) > 1:
        _report_ambiguous_bitwarden_bundles(logins=logins, login_name=login_name)
        raise VaultExit(code=2)

    key_values = logins[0]["secrets"][0]["keyValues"]
    missing_keys = [key for key in BITWARDEN_SECRET_KEYS if not key_values.get(key)]
    if missing_keys:
        err_console.print(f"[bold red]Matched StackOps secret is missing required keys.[/bold red] {', '.join(missing_keys)}")
        raise VaultExit(code=2)

    return BitwardenCredentials(
        login_name=login_name,
        account_name=account_name,
        client_id=str(key_values["BW_CLIENTID"]),
        client_secret=str(key_values["BW_CLIENTSECRET"]),
        password=str(key_values["BW_PASSWORD"]),
    )


def _format_bitwarden_secret_selection(*, login_name: str, account_name: str | None) -> str:
    text = f"Login: {login_name}"
    if account_name is not None:
        text += f" Account: {account_name}"
    return text


BITWARDEN_CLIENT_ID_USER_PREFIX = "user."


def extract_user_id(client_id: str) -> str:
    """Extract the Bitwarden user id from a user API key client id (\"user.<userId>\") """
    if not client_id.startswith(BITWARDEN_CLIENT_ID_USER_PREFIX) or len(client_id) <= len(BITWARDEN_CLIENT_ID_USER_PREFIX):
        err_console.print(f'[bold red]BW_CLIENTID in StackOps secrets must be a user API key shaped "{BITWARDEN_CLIENT_ID_USER_PREFIX}<userId>".[/bold red]')
        raise VaultExit(code=2)
    return client_id[len(BITWARDEN_CLIENT_ID_USER_PREFIX):]


def _report_ambiguous_bitwarden_bundles(*, logins: list[Login], login_name: str) -> None:
    """Explain which Bitwarden bundles matched, which email each maps to, and how to disambiguate."""
    vault_status = get_vault_status()
    logged_in_client_id = f"{BITWARDEN_CLIENT_ID_USER_PREFIX}{vault_status.user_id}" if vault_status.user_id else None

    bundles_table = Table(box=None, show_header=True, header_style="bold")
    bundles_table.add_column("Account", style="bold")
    bundles_table.add_column("Email")
    bundles_table.add_column("Description")
    bundles_table.add_column("Bitwarden session")
    for login in logins:
        client_id = str(login["secrets"][0]["keyValues"]["BW_CLIENTID"])
        is_current_login = logged_in_client_id is not None and client_id == logged_in_client_id
        bundles_table.add_row(
            str(login.get("accountName", "-")),
            str(login.get("email", "-")),
            str(login.get("description", "-")),
            "[green]current login[/green]" if is_current_login else "-",
        )

    err_console.print(f"[bold red]Multiple Bitwarden secret bundles matched.[/bold red] Login: {login_name}")
    err_console.print(bundles_table)
    if vault_status.user_email:
        err_console.print(f"bw is currently logged in as [bold]{escape(vault_status.user_email)}[/bold] ({vault_status.status}).")
    account_names = ", ".join(str(login.get("accountName", "-")) for login in logins)
    err_console.print(f"Pick one explicitly, e.g. [bold]devops vault bitwarden login-and-unlock --account-name <accountName>[/bold]. Accounts: {account_names}")


def print_process_output(result: subprocess.CompletedProcess[str], *, stderr: bool = False) -> None:
    """Print captured command output if present."""
    printer = err_console.print if stderr else console.print
    for stream in (result.stdout, result.stderr):
        text = stream.strip()
        if text:
            printer(text)


def sync() -> None:
    """Sync the Bitwarden vault with the server and drop stale cached search results."""
    session = load_session_token_from_cache()
    vault_status = get_vault_status(session)
    ensure_vault_accessible(vault_status)
    if vault_status.status == "unknown":
        console.print("[yellow]⚠️  Could not determine vault status — proceeding anyway.[/yellow]")

    console.print("[blue]🔄 Syncing vault...[/blue]")
    sync_result = run_command(["bw", "sync"], env=bw_environment(session))
    if sync_result.returncode != 0:
        print_process_output(sync_result, stderr=True)
        err_console.print("[bold red]Vault sync failed.[/bold red]")
        raise VaultExit(code=1)

    purge_cached_searches()
    account = escape(vault_status.user_email or vault_status.user_id or "unknown account")
    console.print(f"[green]✅ Vault synced.[/green] Account: [bold]{account}[/bold]. Cached searches were refreshed.")


def login_and_unlock(account_name: str | None = None, *, login_name: str = DEFAULT_BITWARDEN_LOGIN_NAME) -> None:
    """Authenticate with Bitwarden and persist a local BW_SESSION token."""
    credentials = load_bitwarden_credentials(login_name=login_name, account_name=account_name)
    expected_user_id = extract_user_id(credentials.client_id)
    selection = _format_bitwarden_secret_selection(login_name=credentials.login_name, account_name=credentials.account_name)

    env = os.environ.copy()
    env["BW_CLIENTID"] = credentials.client_id
    env["BW_CLIENTSECRET"] = credentials.client_secret
    env["BW_PASSWORD"] = credentials.password
    cached_session = load_session_token_from_cache()
    if cached_session:
        env["BW_SESSION"] = cached_session

    vault_status = get_vault_status(env.get("BW_SESSION"))
    logged_into_target = vault_status.user_id == expected_user_id and vault_status.status in {"locked", "unlocked"}

    if logged_into_target:
        console.print(f"[green]Already logged in.[/green] {selection}")
    else:
        if vault_status.status != "unauthenticated":
            stale_account = vault_status.user_email or vault_status.user_id or "unknown"
            console.print(f"[yellow]Logged in to a different Bitwarden account ({escape(stale_account)}) — logging out.[/yellow]")
            run_bw_command(["bw", "logout"], env=env)
        env.pop("BW_SESSION", None)

        console.print(f"Logging in. {selection}")
        login_result = run_command(["bw", "login", "--apikey"], env=env, check=True)
        print_process_output(login_result)

        post_login_status = get_vault_status(None)
        if post_login_status.user_id != expected_user_id:
            err_console.print(f"[bold red]Bitwarden login did not activate account {expected_user_id}.[/bold red]")
            raise VaultExit(code=1)

        purge_cached_searches()

    unlock_check = run_command(["bw", "unlock", "--check"], env=env)
    if unlock_check.returncode == 0:
        session = env.get("BW_SESSION")
        if not session:
            err_console.print("[bold red]Vault reports as unlocked, but no BW_SESSION value is available to persist.[/bold red]")
            raise VaultExit(code=1)
        persist_session_token_to_cache(session)
        console.print("[green]Vault already unlocked.[/green] Session saved to encrypted cache.")
        return

    console.print("[blue]Unlocking vault...[/blue]")

    session = run_bw_command(["bw", "unlock", "--passwordenv", "BW_PASSWORD", "--raw"], env=env).strip()
    if not session:
        err_console.print("[bold red]bw unlock did not return a session token.[/bold red]")
        raise VaultExit(code=1)

    env["BW_SESSION"] = session
    persist_session_token_to_cache(session)

    unlock_verify = run_command(["bw", "unlock", "--check"], env=env)
    if unlock_verify.returncode != 0:
        print_process_output(unlock_verify, stderr=True)
        err_console.print("[bold red]Bitwarden unlock check failed after bw unlock.[/bold red]")
        raise VaultExit(code=1)

    final_status = get_vault_status(session)
    account = escape(final_status.user_email or final_status.user_id or "unknown account")
    console.print(f"[green]Vault unlocked.[/green] Session saved to encrypted cache. Account: [bold]{account}[/bold]")


def export_session() -> None:
    """Define the cached BW_SESSION in the calling shell through the StackOps shell handoff (validates it first)."""
    from stackops.scripts.python.helpers.helpers_devops import cli_config_secrets_actions as secret_actions

    session = load_session_token_from_cache()
    if not session:
        err_console.print(f"[bold red]No BW_SESSION saved in vault cache.[/bold red] Run [bold]{DEFAULT_LOGIN_COMMAND}[/bold] first.")
        raise VaultExit(code=1)

    vault_status = get_vault_status(session)
    if vault_status.status != "unlocked":
        err_console.print(f"[bold red]Saved BW_SESSION is not a valid unlocked session ({vault_status.status}).[/bold red]")
        err_console.print(f"Run [bold]{DEFAULT_LOGIN_COMMAND}[/bold] to re-authenticate and refresh the cached session.")
        raise VaultExit(code=1)

    secret_actions.write_env_handoff({"BW_SESSION": session}, verbose=False)
    account = escape(vault_status.user_email or "unknown account")
    console.print(f"[green]🔓 BW_SESSION is defined in this shell for account:[/green] [bold]{account}[/bold]")
    if vault_status.server_url:
        console.print(f"[dim]Server:[/dim] {escape(vault_status.server_url)}")


def clean_cache() -> None:
    """Remove cached vault data under ~/tmp_results."""
    if CACHE_PATH.exists():
        CACHE_PATH.unlink()
        prune_empty_directories(CACHE_PATH.parent, stop=TMP_RESULTS_ROOT)
        console.print("[green]Removed cached vault data.[/green] This clears cached search results and any saved BW_SESSION.")
        return

    console.print(f"[yellow]No vault cache file found.[/yellow] [dim]{CACHE_PATH}[/dim]")
