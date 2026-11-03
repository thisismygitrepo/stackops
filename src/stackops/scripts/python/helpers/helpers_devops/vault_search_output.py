import json
from collections.abc import Sequence
from typing import TypedDict

from stackops.scripts.python.helpers.helpers_devops.vault import VaultItem, build_bw_command, get_item_notes, run_bw_command


class CredentialRecord(TypedDict):
    name: str
    id: str
    username: str | None
    password: str | None
    totp: str | None
    notes: str | None


def print_credentials_json(items: Sequence[VaultItem], session: str | None, use_totp: bool) -> None:
    records: list[CredentialRecord] = []
    for item in items:
        totp: str | None = None
        login = item.raw.get("login")
        if use_totp and isinstance(login, dict) and login.get("totp"):
            command = build_bw_command(args=["get", "totp", item.id], session=session)
            totp = run_bw_command(command).strip()
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
