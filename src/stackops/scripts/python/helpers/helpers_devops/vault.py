"""Bitwarden vault search and login helpers.

Features
- Rich output (pretty printing)
- Optional copy-to-clipboard (via `cb` CLI tool)
- Uses tv fuzzy-finder to disambiguate multiple matches
- Uses StackOps secrets selectors for Bitwarden login credentials
- Safe subprocess usage (no shell=True where possible)
- Persists the latest Bitwarden session token to a local file
"""

import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Sequence

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from stackops.secrets import Login, SecretsFileError, search_logins
from stackops.utils.io import GpgCommandError, decrypt_bytes_asymmetric, encrypt_bytes_asymmetric
from stackops.utils.source_of_truth import SECRETS_DOFILE

# Keep the historical pwdmgr cache path so existing saved BW_SESSION tokens keep working.
TMP_RESULTS_ROOT = Path.home() / "tmp_results"
CACHE_PATH = Path.home() / "tmp_results/cache/pwdmgr/cache.json.gpg"
DEFAULT_BITWARDEN_LOGIN_NAME = "bitwarden"
DEFAULT_LOGIN_COMMAND = "devops vault login-and-unlock [--account-name <accountName>] [--login-name <login_name>]"
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
    else:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_bytes(encrypted)


def cache_get(key: str) -> str | None:
    cache = load_encrypted_cache()
    return cache.get(key)


def cache_set(key: str, value: str) -> None:
    cache = load_encrypted_cache()
    cache[key] = value
    save_encrypted_cache(cache)


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


def build_bw_command(args: Sequence[str], session: Optional[str] = None) -> list[str]:
    """Build a bw command, placing the session option in the global option position."""
    return ["bw"] + (["--session", session] if session else []) + list(args)


def run_command(args: Sequence[str], *, env: Optional[dict[str, str]] = None, check: bool = False) -> subprocess.CompletedProcess[str]:
    """Run a subprocess command and optionally raise a vault command error."""
    try:
        return subprocess.run(list(args), capture_output=True, text=True, env=env, check=check)
    except FileNotFoundError:
        err_console.print(f"[bold red]Command not found:[/bold red] {' '.join(args)}")
        raise VaultExit(code=1)
    except subprocess.CalledProcessError as exc:
        err_console.print(f"[bold red]Command failed:[/bold red] {' '.join(args)}")
        if exc.stderr:
            err_console.print("[red]stderr:[/red]", exc.stderr.strip())
        if exc.stdout:
            err_console.print("[red]stdout:[/red]", exc.stdout.strip())
        raise VaultExit(code=1)


def get_vault_status_field(status_payload: dict[str, Any], key: str) -> str | None:
    value = status_payload.get(key)
    if isinstance(value, str) and value:
        return value
    return None


def get_vault_status(session: Optional[str] = None) -> VaultStatus:
    """Return the bw vault status and authenticated account metadata when available."""
    cmd = build_bw_command(["status"], session)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
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


def parse_items(raw: str) -> List[VaultItem]:
    """Parse the JSON returned by `bw list items` into VaultItem objects."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        err_console.print("[bold red]Failed to parse JSON from bw output.[/bold red]")
        err_console.print(exc)
        raise VaultExit(code=1)

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


def choose_entry_interactive(items: List[VaultItem]) -> VaultItem:
    """Choose a vault item interactively using the tv fuzzy-finder with a preview panel."""
    if not items:
        raise ValueError("no items to choose from")

    from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview

    def _preview(e: VaultItem) -> str:
        login = e.raw.get("login", {}) or {}
        uris = ", ".join(u.get("uri", "") for u in (login.get("uris") or []))
        lines = [
            f"Name:     {e.name}",
            f"ID:       {e.id}",
            f"Username: {e.username or '-'}",
            f"Password: {'(set)' if e.password else '-'}",
            f"TOTP:     {'(set)' if login.get('totp') else '-'}",
            f"URLs:     {uris or '-'}",
            f"Notes:    {(get_item_notes(e.raw) or '-')[:200]}",
        ]
        return "\n".join(lines)

    mapping: dict[str, VaultItem] = {f"{e.name} | {e.username or ''}": e for e in items}
    preview_mapping: dict[str, str] = {k: _preview(e) for k, e in mapping.items()}

    choice = choose_from_dict_with_preview(preview_mapping, extension="txt", multi=False, preview_size_percent=50.0)
    if choice is None:
        raise VaultExit(code=2)
    return mapping[choice]


def copy_to_clipboard(value: str, slot: int = 1) -> bool:
    """Copy value to clipboard using `cb` CLI tool. Return True on success."""
    try:
        subprocess.run(["cb", f"cp{slot}", value], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


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
        err_console.print(f"[bold red]Multiple Bitwarden secret bundles matched.[/bold red] {selection}")
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


def print_process_output(result: subprocess.CompletedProcess[str], *, stderr: bool = False) -> None:
    """Print captured command output if present."""
    printer = err_console.print if stderr else console.print
    for stream in (result.stdout, result.stderr):
        text = stream.strip()
        if text:
            printer(text)


def search(
    name: str,
    copy: str = "password",
    sync: bool = False,
    show: bool = False,
    use_totp: bool = True,
    username_slot: int = 0,
    password_slot: int = 1,
    totp_slot: int = 2,
    json_slot: int = 3,
    silent: bool = False,
    json_output: bool = False,
    raw_output: bool = False,
    fresh: bool = False,
) -> None:
    """Retrieve credentials from Bitwarden (`bw`) and optionally copy them to the clipboard."""

    # install_if_missing(which="tv")

    info = (lambda *a, **kw: None) if silent or json_output or raw_output else console.print

    copy = copy.lower()
    if copy not in {"password", "username", "totp", "none"}:
        err_console.print("[red]Invalid --copy value. Use 'password', 'username', 'totp', or 'none'.[/red]")
        raise VaultExit(code=2)

    # Try to load session from cache
    session = load_session_token_from_cache()

    if sync:
        info("[blue]🔄 Syncing vault...[/blue]")
        sync_cmd = build_bw_command(["sync"], session)
        try:
            sync_result = subprocess.run(sync_cmd, capture_output=True, text=True)
            if sync_result.returncode == 0:
                info("[green]✅ Vault synced.[/green]")
            else:
                info(f"[yellow]⚠️  Sync failed (continuing anyway):[/yellow] {sync_result.stderr.strip() or sync_result.stdout.strip()}")
        except FileNotFoundError:
            info("[yellow]⚠️  bw not found — skipping sync.[/yellow]")

    cache_key = f"search::{name}"
    raw = None
    use_cached_search = not (fresh or sync)
    if use_cached_search:
        raw = cache_get(cache_key)
        if raw:
            info("[green]Loaded from cache.[/green]")

    if not raw:
        vault_status = get_vault_status(session)
        status = vault_status.status
        login_command = DEFAULT_LOGIN_COMMAND
        if status == "locked":
            message_lines = ["[bold red]🔒 Vault is locked.[/bold red]"]
            for label, value in get_vault_account_details(vault_status):
                message_lines.append(f"[dim]{label}:[/dim] [bold]{escape(value)}[/bold]")
            message_lines.append(f"[dim]Next:[/dim] Run [bold]{login_command}[/bold] or save a valid session token using the CLI.")
            err_console.print("\n".join(message_lines))
            raise VaultExit(code=1)
        if status == "unauthenticated":
            err_console.print(f"[bold red]🔒 Not logged in to Bitwarden.[/bold red] Run [bold]{login_command}[/bold] first.")
            raise VaultExit(code=1)
        if status == "unknown":
            info("[yellow]⚠️  Could not determine vault status — proceeding anyway.[/yellow]")

        info(f"🔍 Searching for credentials matching: [bold]{name}[/bold] ...")
        cmd_args = build_bw_command(["list", "items", "--search", name], session)
        masked_args = cmd_args.copy()
        if session:
            masked_args[2] = "***"
        info(f"[dim]$ {' '.join(masked_args)}[/dim]")
        raw = run_bw_command(cmd_args)
        cache_set(cache_key, raw)

    items = parse_items(raw)

    if raw_output:
        copy_to_clipboard(raw, slot=json_slot)
        print(raw)
        return

    if not items:
        err_console.print(f"[red]No entries found for:[/red] {name}")
        raise VaultExit(code=1)

    if len(items) == 1:
        entry = items[0]
        info(f"[green]Found:[/green] {entry.name}")
    else:
        entry = choose_entry_interactive(items)
        info(f"[green]Selected:[/green] {entry.name}")

    notes_value = get_item_notes(entry.raw)
    json_str = json.dumps(entry.raw)
    copy_to_clipboard(json_str, slot=json_slot)

    if not silent and not json_output:
        tbl = Table(box=None, show_header=False)
        tbl.add_column(justify="right", style="bold")
        tbl.add_column()
        tbl.add_row("Name:", entry.name)
        tbl.add_row("ID:", entry.id)
        tbl.add_row("Username:", entry.username or "-")
        tbl.add_row("Password:", "********" if entry.password else "-")
        tbl.add_row("Notes:", notes_value or "-")
        console.print(Panel(tbl, title="Credential summary"))

    totp_value: Optional[str] = None
    if use_totp:
        login = entry.raw.get("login", {}) or {}
        if login.get("totp"):
            info("[blue]Fetching TOTP...[/blue]")
            totp_cmd = build_bw_command(["get", "totp", entry.id], session)
            try:
                totp_value = run_bw_command(totp_cmd).strip()
            except VaultExit:
                raw_totp_seed = login.get("totp")
                if raw_totp_seed:
                    info(f"[red]Failed to fetch TOTP via bw — raw TOTP seed:[/red] [bold]{raw_totp_seed}[/bold]")
                    totp_value = raw_totp_seed
                else:
                    info("[red]Failed to fetch TOTP.[/red]")

    copied = False
    copy_target_value: Optional[str] = None
    copy_slot: int = password_slot
    if copy != "none":
        if copy == "password":
            copy_target_value = entry.password
            copy_slot = password_slot
        elif copy == "username":
            copy_target_value = entry.username
            copy_slot = username_slot
        elif copy == "totp":
            copy_target_value = totp_value
            copy_slot = totp_slot

        if copy_target_value:
            if copy_to_clipboard(copy_target_value, slot=copy_slot):
                info(f"✅ [bold]{copy}[/bold] copied to clipboard (slot {copy_slot}).")
                copied = True
            elif not json_output:
                console.print(f"[yellow]Clipboard tool not available — cannot copy {copy}. Showing credentials instead:[/yellow]")
                fallback_tbl = Table(show_header=False, box=None)
                fallback_tbl.add_column(style="bold", width=12)
                fallback_tbl.add_column()
                if entry.username:
                    fallback_tbl.add_row("Username:", entry.username)
                if entry.password:
                    fallback_tbl.add_row("Password:", entry.password)
                if totp_value:
                    fallback_tbl.add_row("TOTP:", totp_value)
                console.print(Panel(fallback_tbl, title="Credentials (cleartext fallback)"))
                copied = True

    if json_output:
        print(
            json.dumps(
                {"name": entry.name, "id": entry.id, "username": entry.username, "password": entry.password, "totp": totp_value, "notes": notes_value}
            )
        )
    elif not silent and (show or not copied):
        panel_rows = []
        if entry.username:
            panel_rows.append(("Username", entry.username))
        if entry.password:
            panel_rows.append(("Password", entry.password))
        if totp_value:
            panel_rows.append(("TOTP", totp_value))
        if notes_value:
            panel_rows.append(("Notes", notes_value))

        if panel_rows:
            out_tbl = Table(show_header=False, box=None)
            out_tbl.add_column(style="bold", width=12)
            out_tbl.add_column()
            for left, right in panel_rows:
                out_tbl.add_row(f"{left}:", right)
            console.print(Panel(out_tbl, title="Credential (cleartext)"))
        else:
            console.print("[yellow]No credential fields available to display.[/yellow]")

    time.sleep(0.05)


def login_and_unlock(account_name: str | None = None, *, login_name: str = DEFAULT_BITWARDEN_LOGIN_NAME) -> None:
    """Authenticate with Bitwarden and persist a local BW_SESSION token."""
    credentials = load_bitwarden_credentials(login_name=login_name, account_name=account_name)

    env = os.environ.copy()
    existing_session = load_session_token_from_cache()
    if existing_session:
        env["BW_SESSION"] = existing_session
        os.environ["BW_SESSION"] = existing_session

    env["BW_CLIENTID"] = credentials.client_id
    env["BW_CLIENTSECRET"] = credentials.client_secret
    env["BW_PASSWORD"] = credentials.password
    os.environ["BW_CLIENTID"] = credentials.client_id
    os.environ["BW_CLIENTSECRET"] = credentials.client_secret
    os.environ["BW_PASSWORD"] = credentials.password

    login_check = run_command(["bw", "login", "--check"], env=env)
    if login_check.returncode == 0:
        selection = _format_bitwarden_secret_selection(login_name=credentials.login_name, account_name=credentials.account_name)
        console.print(f"[green]Already logged in.[/green] {selection}")
    else:
        console.print("Logging in")
        login_result = run_command(["bw", "login", "--apikey"], env=env, check=True)
        print_process_output(login_result)

        login_verify = run_command(["bw", "login", "--check"], env=env)
        if login_verify.returncode != 0:
            print_process_output(login_verify, stderr=True)
            err_console.print("[bold red]Bitwarden login check failed after bw login --apikey.[/bold red]")
            raise VaultExit(code=1)

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
    os.environ["BW_SESSION"] = session
    persist_session_token_to_cache(session)

    unlock_verify = run_command(["bw", "unlock", "--check"], env=env)
    if unlock_verify.returncode != 0:
        print_process_output(unlock_verify, stderr=True)
        err_console.print("[bold red]Bitwarden unlock check failed after bw unlock.[/bold red]")
        raise VaultExit(code=1)

    console.print("[green]Vault unlocked.[/green] Session saved to encrypted cache.")


def clean_cache() -> None:
    """Remove cached vault data under ~/tmp_results."""
    if CACHE_PATH.exists():
        CACHE_PATH.unlink()
        prune_empty_directories(CACHE_PATH.parent, stop=TMP_RESULTS_ROOT)
        console.print("[green]Removed cached vault data.[/green] This clears cached search results and any saved BW_SESSION.")
        return

    console.print(f"[yellow]No vault cache file found.[/yellow] [dim]{CACHE_PATH}[/dim]")
