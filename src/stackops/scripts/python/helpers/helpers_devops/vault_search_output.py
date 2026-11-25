import json
from collections.abc import Sequence
from typing import TypedDict, cast
from urllib.parse import urlsplit

from rich import box
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_constants import CANDIDATE_DISPLAY_LIMIT
from stackops.scripts.python.helpers.helpers_devops.vault import VaultItem, get_item_notes, run_bw_command


class CredentialRecord(TypedDict):
    name: str
    id: str
    username: str | None
    password: str | None
    totp: str | None
    notes: str | None


def item_has_totp(item: VaultItem) -> bool:
    login = item.raw.get("login")
    return isinstance(login, dict) and bool(cast(dict[str, object], login).get("totp"))


def item_urls(item: VaultItem) -> tuple[str, ...]:
    login = item.raw.get("login")
    uris = cast(dict[str, object], login).get("uris") if isinstance(login, dict) else None
    return tuple(str(cast(dict[str, object], uri).get("uri", "")) for uri in cast(list[object], uris) if isinstance(uri, dict)) if isinstance(uris, list) else ()


def item_field_names(item: VaultItem) -> tuple[str, ...]:
    fields = item.raw.get("fields")
    if not isinstance(fields, list):
        return ()
    names = (cast(dict[str, object], field).get("name") for field in cast(list[object], fields) if isinstance(field, dict))
    return tuple(name for name in names if isinstance(name, str) and name)


def item_holdings(item: VaultItem) -> str:
    held = (("password", bool(item.password)), ("totp", item_has_totp(item)), ("notes", get_item_notes(item.raw) is not None))
    return ", ".join(label for label, present in held if present)


def print_items(items: Sequence[VaultItem], target: Console, limited: bool, plain: bool) -> None:
    shown = items[:CANDIDATE_DISPLAY_LIMIT] if limited else items
    hidden_count = len(items) - len(shown)
    if plain:
        for item in shown:
            target.print(f"{item.name} [{item.id}]", markup=False, highlight=False)
            details = (("Username", item.username or ""), ("URLs", ", ".join(item_urls(item))), ("Holds", item_holdings(item)), ("Environment keys", ", ".join(item_field_names(item))))
            for label, value in details:
                if value:
                    target.print(f"  {label}: {value}", markup=False, highlight=False)
        if hidden_count:
            target.print(f"... {hidden_count} more", markup=False, highlight=False)
        return
    show_environment_keys = any(item_field_names(item) for item in shown)
    table = Table(box=box.SIMPLE_HEAD, header_style="bold cyan", caption=f"{hidden_count} more not shown" if hidden_count else None, show_lines=len(shown) > 1)
    table.add_column("Name", style="bold", overflow="fold")
    table.add_column("Username", overflow="fold")
    table.add_column("Sites", style="blue", overflow="fold")
    table.add_column("Holds", style="green")
    if show_environment_keys:
        table.add_column("Env keys", style="magenta", overflow="fold")
    table.add_column("ID", style="dim", no_wrap=True)
    for item in shown:
        sites = "\n".join(dict.fromkeys(urlsplit(url).hostname or url for url in item_urls(item)))
        cells = (item.name, item.username or "-", sites or "-", item_holdings(item) or "-", *((", ".join(item_field_names(item)) or "-",) if show_environment_keys else ()), item.id)
        table.add_row(*(escape(cell) for cell in cells))
    target.print(table)


def item_preview(item: VaultItem) -> str:
    lines = [
        f"# {item.name}",
        "",
        f"- ID: `{item.id}`",
        f"- Username: `{item.username or '-'}`",
        f"- URLs: `{', '.join(item_urls(item)) or '-'}`",
        f"- Holds: `{item_holdings(item) or '-'}`",
        f"- Environment keys: `{', '.join(item_field_names(item)) or '-'}`",
    ]
    return "\n".join(lines) + "\n"


def print_cleartext_panel(item: VaultItem, totp: str | None, target: Console) -> None:
    rows = [("Username", item.username), ("Password", item.password), ("TOTP", totp), ("Notes", get_item_notes(item.raw))]
    table = Table(show_header=False, box=None)
    table.add_column(style="bold", width=12)
    table.add_column()
    for label, value in rows:
        if value:
            table.add_row(f"{label}:", escape(value))
    target.print(Panel(table, title=f"{escape(item.name)} (cleartext)"))


def print_credentials_json(items: Sequence[VaultItem], environment: dict[str, str], use_totp: bool) -> None:
    records: list[CredentialRecord] = []
    for item in items:
        totp = run_bw_command(["bw", "get", "totp", item.id], env=environment).strip() if use_totp and item_has_totp(item) else None
        records.append(
            {
                "name": item.name,
                "id": item.id,
                "username": item.username,
                "password": item.password,
                "totp": totp,
                "notes": get_item_notes(raw_item=item.raw),
            }
        )
    print(json.dumps(records, ensure_ascii=False))
