import json
import os
from dataclasses import dataclass
from typing import NoReturn, cast

from rich.markup import escape

from stackops.scripts.python.helpers.helpers_devops import vault
from stackops.scripts.python.helpers.helpers_devops import vault_search_output as output
from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_validation import is_valid_env_name
from stackops.scripts.python.helpers.helpers_devops.vault import VaultExit, VaultItem, console, err_console
from stackops.scripts.python.helpers.helpers_devops.vault_constants import (
    BITWARDEN_LINKED_FIELD_TYPE,
    BITWARDEN_LINKED_LOGIN_FIELDS,
    BITWARDEN_VALUE_FIELD_TYPES,
    BitwardenCopyField,
)


@dataclass(frozen=True)
class ItemQuery:
    name: str | None
    item_id: str | None
    interactive: bool
    all_matches: bool
    fresh: bool
    sync: bool
    silent: bool
    plain: bool


@dataclass(frozen=True)
class ItemSelection:
    items: tuple[VaultItem, ...]
    raw: str
    environment: dict[str, str]
    origin: str | None


def _fail(message: str, code: int) -> NoReturn:
    err_console.print(f"[bold red]Error:[/bold red] {escape(message)}", highlight=False)
    raise VaultExit(code=code)


def _validate_query(query: ItemQuery) -> None:
    if query.name is not None and not query.name.strip() or query.item_id is not None and not query.item_id.strip():
        _fail("The search name and --id/-I must not be blank.", code=2)
    if query.item_id is not None and (query.name is not None or query.all_matches or query.interactive):
        _fail("--id/-I cannot be combined with a search name, --all-matches/-a, or --interactive/-i.", code=2)
    if query.all_matches and query.interactive:
        _fail("--all-matches/-a cannot be combined with --interactive/-i.", code=2)
    if query.name is None and query.item_id is None and not query.all_matches and not query.interactive:
        _fail("Provide a search name, --id/-I, --interactive/-i, or --all-matches/-a.", code=2)


def _select_items(query: ItemQuery) -> ItemSelection:
    cache = vault.load_encrypted_cache()
    environment = vault.bw_environment(cache.get("BW_SESSION"))
    if query.sync:
        if not query.silent:
            err_console.print("[blue]🔄 Syncing vault...[/blue]")
        vault.run_bw_command(["bw", "sync"], env=environment)
        vault.purge_cached_searches()

    cache_key = f"""search::{json.dumps([query.name, query.item_id])}"""
    raw = None if query.fresh or query.sync else cache.get(cache_key)
    if not raw:
        vault.ensure_vault_accessible(vault.get_vault_status(environment.get("BW_SESSION")))
        arguments = ["bw", "get", "item", query.item_id] if query.item_id is not None else ["bw", "list", "items", *(["--search", query.name] if query.name is not None else [])]
        if not query.silent:
            err_console.print(f"[dim]$ {escape(' '.join(arguments))}[/dim]", highlight=False)
        raw = vault.run_bw_command(arguments, env=environment)
        vault.cache_set(cache_key, raw)
    elif not query.silent:
        err_console.print("[green]Loaded from cache.[/green]")

    items = vault.parse_items(f"""[{raw}]""" if query.item_id is not None else raw)
    sought = query.name or query.item_id or "the whole vault"
    if not items:
        _fail(f"No Bitwarden item matched: {sought}", code=1)
    if query.interactive:
        from stackops.scripts.python.helpers.helpers_devops.cli_interactive_picker import InteractivePickerOption, choose_interactive_option

        chosen = choose_interactive_option(
            [InteractivePickerOption(value=item, label=f"{item.name} | {item.username or ''}", preview=output.item_preview(item), disambiguator=item.id) for item in items],
            missing_tool_message="Interactive selection requires `tv` on PATH.",
            cancelled_message="Interactive selection cancelled.",
            missing_selection_message="Interactive selection did not map to a Bitwarden item",
        )
        return ItemSelection(items=(chosen,), raw=raw, environment=environment, origin=None)
    if len(items) > 1 and not query.all_matches:
        err_console.print(f"[bold red]Error:[/bold red] Selection did not identify a unique Bitwarden item: {escape(sought)} matched {len(items)} items.", highlight=False)
        output.print_items(items, target=err_console, limited=True, plain=query.plain)
        err_console.print("Narrow the name, or use --id/-I, --interactive/-i, or --all-matches/-a.", highlight=False)
        raise VaultExit(code=1)
    origin = f"""{len(items)} matching Bitwarden {"item" if len(items) == 1 else "items"}""" if query.all_matches else None
    return ItemSelection(items=tuple(items), raw=raw, environment=environment, origin=origin)


def _item_environment(item: VaultItem) -> dict[str, str]:
    fields_raw = item.raw.get("fields")
    fields = [cast(dict[str, object], field) for field in cast(list[object], fields_raw) if isinstance(field, dict)] if isinstance(fields_raw, list) else []
    if not fields:
        _fail(
            f"""Bitwarden item "{item.name}" has no custom fields to load. Add one custom field per environment variable, named after the variable. """
            + "A linked custom field can point at the login's username or password.",
            code=1,
        )
    environment: dict[str, str] = {}
    problems: list[str] = []
    for field in fields:
        name, value, field_type, linked_id = field.get("name"), field.get("value"), field.get("type"), field.get("linkedId")
        if not isinstance(name, str) or not is_valid_env_name(name):
            problems.append(f"""{name or "<unnamed>"}: not a valid environment variable name""")
        elif name in environment:
            problems.append(f"{name}: declared more than once")
        elif field_type in BITWARDEN_VALUE_FIELD_TYPES:
            environment[name] = value if isinstance(value, str) else ""
        elif field_type == BITWARDEN_LINKED_FIELD_TYPE and isinstance(linked_id, int) and linked_id in BITWARDEN_LINKED_LOGIN_FIELDS:
            linked_to = BITWARDEN_LINKED_LOGIN_FIELDS[linked_id]
            linked_value = item.username if linked_to == "username" else item.password
            if linked_value:
                environment[name] = linked_value
            else:
                problems.append(f"{name}: linked to the login's {linked_to}, which is empty")
        else:
            problems.append(f"{name}: linked to something other than the login's username or password")
    if problems:
        _fail(f"""Bitwarden item "{item.name}" has custom fields that cannot become environment variables:\n  """ + "\n  ".join(problems), code=1)
    return environment


def _merged_environment(items: tuple[VaultItem, ...]) -> dict[str, str]:
    merged: dict[str, str] = {}
    conflicting_names: set[str] = set()
    for item in items:
        for name, value in _item_environment(item).items():
            if merged.setdefault(name, value) != value:
                conflicting_names.add(name)
    if conflicting_names:
        _fail(
            f"Cannot merge {len(items)} Bitwarden items: {', '.join(sorted(conflicting_names))} would receive different values. "
            + "Select one item with --id/-I or --interactive/-i, or narrow the name.",
            code=1,
        )
    return merged


def search(
    query: ItemQuery, *, json_output: bool, raw_output: bool, copy_field: BitwardenCopyField | None, load_environment: bool, show: bool, use_totp: bool
) -> None:
    from stackops.scripts.python.helpers.helpers_devops.vault_clipboard import copy_secret, require_clipboard
    from stackops.scripts.python.helpers.helpers_devops.vault_environment import prepare_shell_environment

    _validate_query(query)
    if json_output and raw_output:
        _fail("Choose either --json/-j or --raw/-r.", code=2)
    if (json_output or raw_output) and (copy_field is not None or load_environment or show or query.interactive):
        _fail("--json/-j and --raw/-r print only JSON, so they cannot be combined with --copy/-C, --load/-L, --show/-w, or --interactive/-i.", code=2)
    if (copy_field is not None or show) and query.all_matches:
        _fail("--copy/-C and --show/-w act on one item, so they cannot be combined with --all-matches/-a.", code=2)
    if load_environment and not os.environ.get("OP_PROGRAM_PATH"):
        _fail(
            "--load/-L defines variables in the calling shell, so invoke search through the StackOps shell wrapper. "
            + "To run one program with the item's variables, use devops vault bitwarden load --command 'PROGRAM ARGUMENTS'.",
            code=2,
        )
    clipboard = require_clipboard() if copy_field is not None else None

    selection = _select_items(query)
    if raw_output:
        print(selection.raw)
        return
    if json_output:
        output.print_credentials_json(items=selection.items, environment=selection.environment, use_totp=use_totp)
        return

    output.print_items(selection.items, target=console, limited=False, plain=query.plain)
    item = selection.items[0]
    wants_totp = copy_field == "totp" or show and use_totp
    totp = vault.run_bw_command(["bw", "get", "totp", item.id], env=selection.environment).strip() if wants_totp and output.item_has_totp(item) else None
    if show:
        output.print_cleartext_panel(item, totp=totp, target=console)
    if copy_field is not None and clipboard is not None:
        value = {"password": item.password, "username": item.username, "totp": totp}[copy_field]
        if not value:
            _fail(f"""Cannot copy {copy_field}: Bitwarden item "{item.name}" has none.""", code=1)
        copy_secret(clipboard, value, label=f"the {copy_field} of {item.name}")
    if load_environment:
        prepare_shell_environment(_merged_environment(selection.items), origin=selection.origin, verbose=False)
    if not (show or copy_field is not None or load_environment or query.silent):
        err_console.print("""Nothing was copied or loaded. Add --copy/-C FIELD or --load/-L, or use "devops vault bitwarden load" with the same arguments.""", highlight=False)


def load(query: ItemQuery, *, command: str | None) -> None:
    from stackops.scripts.python.helpers.helpers_devops.vault_environment import parse_load_command, prepare_shell_environment, run_command_with_environment

    _validate_query(query)
    command_args = parse_load_command(command)
    selection = _select_items(query)
    key_values = _merged_environment(selection.items)
    if not query.silent:
        output.print_items(selection.items, target=err_console, limited=False, plain=query.plain)
    if command_args is not None:
        run_command_with_environment(command_args, key_values)
    prepare_shell_environment(key_values, origin=selection.origin, verbose=not query.silent)
