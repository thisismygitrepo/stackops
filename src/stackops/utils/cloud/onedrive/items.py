from collections.abc import Mapping
from typing import cast
from urllib.parse import quote, urlsplit

from stackops.utils.cloud.onedrive.auth import graph_json, refresh_access_token
from stackops.utils.cloud.onedrive.constants import GRAPH_BASE
from stackops.utils.cloud.onedrive.errors import OneDriveError
from stackops.utils.cloud.onedrive.output import json_output, print_table


type GraphItem = Mapping[str, object]


def show_status(account_name: str) -> None:
    access_token = refresh_access_token(account_name)
    payload = graph_json("GET", f"{GRAPH_BASE}/me/drive", access_token, "Reading drive status", params={"$select": "driveType,owner,quota,webUrl"})

    owner_value = payload.get("owner")
    owner: GraphItem = cast(GraphItem, owner_value) if isinstance(owner_value, Mapping) else {}
    user_value = owner.get("user")
    user: GraphItem = cast(GraphItem, user_value) if isinstance(user_value, Mapping) else {}
    quota_value = payload.get("quota")
    quota: GraphItem = cast(GraphItem, quota_value) if isinstance(quota_value, Mapping) else {}
    json_output(
        {
            "account": user.get("displayName"),
            "drive_type": payload.get("driveType"),
            "used_bytes": quota.get("used"),
            "total_bytes": quota.get("total"),
            "web_url": payload.get("webUrl"),
        }
    )


def list_items(account_name: str, remote_path: str) -> None:
    encoded_path = quote(remote_path.lstrip("/"), safe="/")
    if encoded_path:
        endpoint = f"{GRAPH_BASE}/me/drive/root:/{encoded_path}:/children"
    else:
        endpoint = f"{GRAPH_BASE}/me/drive/root/children"

    access_token = refresh_access_token(account_name)
    payload = graph_json(
        "GET",
        endpoint,
        access_token,
        "Listing remote items",
        params={"$select": "name,size,lastModifiedDateTime,folder,file", "$orderby": "name", "$top": 200},
    )
    items_value = payload.get("value")
    if not isinstance(items_value, list):
        raise OneDriveError("Listing remote items returned an unexpected response.")

    rows: list[tuple[object, object, object, object]] = []
    for item_value in items_value:
        if not isinstance(item_value, Mapping):
            continue
        item = cast(GraphItem, item_value)
        rows.append((item.get("name"), "folder" if item.get("folder") is not None else "file", item.get("size"), item.get("lastModifiedDateTime")))
    print_table(("NAME", "TYPE", "SIZE (BYTES)", "LAST MODIFIED"), rows)


def search_items(account_name: str, query: str, output_json: bool) -> None:
    odata_query = quote(query.replace("'", "''"), safe="")
    next_url: str | None = f"{GRAPH_BASE}/me/drive/root/search(q='{odata_query}')"
    access_token = refresh_access_token(account_name)
    items_by_id: dict[str, GraphItem] = {}
    params: Mapping[str, str | int] | None = {"$select": "id,name,size,lastModifiedDateTime,folder,file,parentReference,webUrl", "$top": 200}

    while next_url is not None:
        payload = graph_json("GET", next_url, access_token, "Searching remote items", params=params)
        page_value = payload.get("value")
        if not isinstance(page_value, list):
            raise OneDriveError("Search returned an unexpected response.")
        for item_value in page_value:
            if not isinstance(item_value, Mapping):
                continue
            item = cast(GraphItem, item_value)
            item_id = item.get("id")
            if isinstance(item_id, str):
                items_by_id[item_id] = item
        next_url = _validated_next_link(payload.get("@odata.nextLink"))
        params = None

    items = [items_by_id[item_id] for item_id in sorted(items_by_id)]
    if output_json:
        rendered_items: list[dict[str, object]] = []
        for item in items:
            parent_value = item.get("parentReference")
            parent: GraphItem = cast(GraphItem, parent_value) if isinstance(parent_value, Mapping) else {}
            rendered_items.append(
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "type": "folder" if item.get("folder") is not None else "file",
                    "size": item.get("size"),
                    "last_modified": item.get("lastModifiedDateTime"),
                    "parent_path": parent.get("path"),
                    "web_url": item.get("webUrl"),
                }
            )
        json_output(rendered_items)
        return

    rows: list[tuple[object, object, object, object, object]] = []
    for item in items:
        parent_value = item.get("parentReference")
        parent: GraphItem = cast(GraphItem, parent_value) if isinstance(parent_value, Mapping) else {}
        rows.append(
            (
                item.get("name"),
                "folder" if item.get("folder") is not None else "file",
                item.get("size"),
                parent.get("path"),
                item.get("lastModifiedDateTime"),
            )
        )
    print_table(("NAME", "TYPE", "SIZE (BYTES)", "PARENT", "LAST MODIFIED"), rows)


def _validated_next_link(next_link: object) -> str | None:
    if next_link is None:
        return None
    if not isinstance(next_link, str):
        raise OneDriveError("Search returned an invalid pagination link.")

    graph_host = urlsplit(GRAPH_BASE).netloc
    parts = urlsplit(next_link)
    if parts.scheme != "https" or parts.netloc != graph_host:
        raise OneDriveError("Search returned an untrusted pagination link.")
    return next_link
