import json
import re
from dataclasses import dataclass
from typing import Literal, TypedDict, cast

from stackops.scripts.python.helpers.helpers_devops import vault as bitwarden
from stackops.scripts.python.helpers.helpers_webui.vault_bitwarden_state import BitwardenStatus, ask_bitwarden

# Where `devops vault bitwarden search --all-matches` saves the whole list in the cache; the page reads and fills the same entry.
ALL_ITEMS_KEY = f"""search::{json.dumps([None, None])}"""
ITEM_ID_PATTERN = re.compile(r"[0-9A-Fa-f][0-9A-Fa-f-]{7,63}")
ITEM_KINDS: dict[object, "BitwardenItemKind"] = {1: "login", 2: "note", 3: "card", 4: "identity"}

type BitwardenItemKind = Literal["login", "note", "card", "identity", "other"]
type BitwardenField = Literal["password", "username", "code", "notes"]


# `reason` says how Bitwarden stands when that is why nothing could be read, so the page can offer the way forward, and is empty otherwise.
@dataclass(frozen=True)
class BitwardenProblem:
    status: int
    message: str
    reason: BitwardenStatus | Literal[""]


# One item by its labels. Whether it has a password, a one-time code or a note is said, and none of them is sent.
class BitwardenItemView(TypedDict):
    id: str
    name: str
    username: str
    urls: list[str]
    kind: BitwardenItemKind
    has_password: bool
    has_code: bool
    has_notes: bool
    favorite: bool
    changed: str


# `saved` says the list is the copy kept on this machine, which can be older than what Bitwarden holds. `searches` is how many saved searches
# the cache holds once this list is in it.
class BitwardenItemsView(TypedDict):
    items: list[BitwardenItemView]
    saved: bool
    searches: int


class BitwardenValue(TypedDict):
    text: str


WAYS_FORWARD: dict[BitwardenStatus, str] = {
    "missing": "Bitwarden's command-line program is not installed on this machine.",
    "unauthenticated": "Bitwarden is signed out. Unlock it to see your logins.",
    "locked": "Bitwarden is locked. Unlock it to see your logins.",
    "unknown": "Bitwarden did not say how it stands. Check again.",
    "unlocked": "",
}


# The whole vault by label, from the saved copy when there is one and `fresh` is not asked for, as the command's search does it. A fresh list
# is kept in the cache for the next time, encrypted the way the command keeps it.
def read_bitwarden_items(fresh: bool) -> BitwardenItemsView | BitwardenProblem:
    cache = bitwarden.load_encrypted_cache()
    raw = None if fresh else cache.get(ALL_ITEMS_KEY)
    saved = bool(raw)
    if not raw:
        session = cache.get("BW_SESSION")
        standing = ask_bitwarden(session=session)["status"]
        if standing != "unlocked":
            return BitwardenProblem(status=409, message=WAYS_FORWARD[standing], reason=standing)
        try:
            listing = bitwarden.run_command(bitwarden.build_bw_command(["list", "items"], session))
        except bitwarden.VaultExit:
            return BitwardenProblem(status=409, message=WAYS_FORWARD["missing"], reason="missing")
        if listing.returncode != 0:
            said = (listing.stderr.strip() or listing.stdout.strip()).splitlines()
            return BitwardenProblem(status=502, message=f"""Bitwarden did not list its items. {said[-1] if said else ""}""".strip(), reason="")
        raw = listing.stdout
        try:
            bitwarden.cache_set(ALL_ITEMS_KEY, raw)
        except bitwarden.VaultExit:
            # The list is still shown; without a working GPG key it is only not kept for next time.
            pass
    try:
        items = bitwarden.parse_items(raw)
    except (bitwarden.VaultExit, TypeError, AttributeError):
        return BitwardenProblem(status=502, message="What Bitwarden listed could not be read. Sync and try again.", reason="")
    searches = {key for key in cache if key.startswith("search::")} | {ALL_ITEMS_KEY}
    return {"items": [_item_view(item) for item in items], "saved": saved, "searches": len(searches)}


def _item_view(item: bitwarden.VaultItem) -> BitwardenItemView:
    login_raw = item.raw.get("login")
    login = cast(dict[str, object], login_raw) if isinstance(login_raw, dict) else {}
    uris_raw = login.get("uris")
    uris = cast(list[object], uris_raw) if isinstance(uris_raw, list) else []
    changed = item.raw.get("revisionDate")
    return {
        "id": item.id,
        "name": item.name,
        "username": item.username or "",
        "urls": [str(cast(dict[str, object], uri)["uri"]) for uri in uris if isinstance(uri, dict) and cast(dict[str, object], uri).get("uri")],
        "kind": ITEM_KINDS.get(item.raw.get("type"), "other"),
        "has_password": bool(item.password),
        "has_code": bool(login.get("totp")),
        "has_notes": bitwarden.get_item_notes(item.raw) is not None,
        "favorite": item.raw.get("favorite") is True,
        "changed": changed if isinstance(changed, str) else "",
    }


# One value of one item, for the page to copy or show because the person asked. A password, user name or note comes from the saved list; a
# one-time code is asked of Bitwarden at that moment, since it changes every half minute.
def read_bitwarden_value(body: object) -> BitwardenValue | BitwardenProblem:
    payload = cast(dict[str, object], body) if isinstance(body, dict) else {}
    item_id, field = payload.get("id"), payload.get("field")
    if not isinstance(item_id, str) or ITEM_ID_PATTERN.fullmatch(item_id) is None:
        return BitwardenProblem(status=400, message="Name the item by its `id`.", reason="")
    cache = bitwarden.load_encrypted_cache()
    match field:
        case "code":
            try:
                answer = bitwarden.run_command(bitwarden.build_bw_command(["get", "totp", item_id], cache.get("BW_SESSION")))
            except bitwarden.VaultExit:
                return BitwardenProblem(status=409, message=WAYS_FORWARD["missing"], reason="missing")
            if answer.returncode != 0 or answer.stdout.strip() == "":
                return BitwardenProblem(status=409, message="Bitwarden did not give a code. It has to be unlocked for that.", reason="locked")
            return {"text": answer.stdout.strip()}
        case "password" | "username" | "notes":
            raw = cache.get(ALL_ITEMS_KEY)
            if not raw:
                return BitwardenProblem(status=409, message="The list is no longer saved on this machine. Refresh it and try again.", reason="")
            try:
                found = [item for item in bitwarden.parse_items(raw) if item.id == item_id]
            except (bitwarden.VaultExit, TypeError, AttributeError):
                found = []
            if len(found) == 0:
                return BitwardenProblem(status=404, message="That item is no longer in the list. Refresh it.", reason="")
            text = found[0].password if field == "password" else found[0].username if field == "username" else bitwarden.get_item_notes(found[0].raw)
            if not text:
                return BitwardenProblem(status=404, message=f"""This item has no {"user name" if field == "username" else "note" if field == "notes" else field}.""", reason="")
            return {"text": text}
        case _:
            return BitwardenProblem(status=400, message="`field` must be password, username, code or notes.", reason="")
