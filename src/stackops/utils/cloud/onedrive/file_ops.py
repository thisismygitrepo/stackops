import os
import tempfile
from pathlib import Path
from urllib.parse import quote

import requests
import typer

from stackops.utils.cloud.onedrive.auth import encoded_remote_path, graph_headers, graph_json, refresh_access_token, require_success, send_request
from stackops.utils.cloud.onedrive.constants import GRAPH_BASE
from stackops.utils.cloud.onedrive.errors import OneDriveError
from stackops.utils.cloud.onedrive.output import json_output


def download_file(account_name: str, remote_path: str, local_path: Path) -> None:
    if local_path.exists():
        raise OneDriveError(f"Local target already exists: {local_path}")
    encoded_path = encoded_remote_path(remote_path)
    if encoded_path == "":
        raise OneDriveError("Remote file path cannot be root.")

    try:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix=".onedrive-download.", dir=local_path.parent)
        os.close(descriptor)
    except OSError as exc:
        raise OneDriveError(f"Unable to prepare the local target: {exc}") from exc

    temporary_path = Path(temporary_name)
    try:
        access_token = refresh_access_token(account_name)
        response = send_request(
            "GET", f"{GRAPH_BASE}/me/drive/root:/{encoded_path}:/content", headers=graph_headers(access_token), allow_redirects=True, stream=True
        )
        if not response.ok:
            require_success(response, "Downloading remote file")
        with response, temporary_path.open("wb") as stream:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    stream.write(chunk)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, local_path)
    except (OSError, requests.RequestException) as exc:
        raise OneDriveError(f"Unable to download the file: {exc}") from exc
    finally:
        temporary_path.unlink(missing_ok=True)

    typer.echo(f"Downloaded {remote_path} to {local_path}")


def upload_file(account_name: str, local_path: Path, remote_path: str, overwrite: bool) -> None:
    if not local_path.is_file():
        raise OneDriveError(f"Local source is not a file: {local_path}")
    encoded_path = encoded_remote_path(remote_path)
    if encoded_path == "":
        raise OneDriveError("Remote file path cannot be root.")

    access_token = refresh_access_token(account_name)
    target_url = f"{GRAPH_BASE}/me/drive/root:/{encoded_path}"
    metadata = send_request("GET", target_url, headers=graph_headers(access_token))
    if metadata.status_code == 200 and not overwrite:
        raise OneDriveError("Remote target exists. Pass --overwrite to replace it.")
    if metadata.status_code not in (200, 404):
        require_success(metadata, "Inspecting remote target")

    try:
        with local_path.open("rb") as stream:
            response = send_request(
                "PUT", f"{target_url}:/content", headers={**graph_headers(access_token), "Content-Type": "application/octet-stream"}, data=stream
            )
    except OSError as exc:
        raise OneDriveError(f"Unable to read local source: {exc}") from exc

    payload = require_success(response, "Uploading local file")
    json_output({"name": payload.get("name"), "size": payload.get("size"), "webUrl": payload.get("webUrl")})


def delete_item(account_name: str, remote_path: str, yes: bool) -> None:
    encoded_path = encoded_remote_path(remote_path)
    if encoded_path == "":
        raise OneDriveError("Refusing to delete the OneDrive root.")

    access_token = refresh_access_token(account_name)
    item = graph_json("GET", f"{GRAPH_BASE}/me/drive/root:/{encoded_path}", access_token, "Reading remote item", params={})
    item_id = item.get("id")
    if not isinstance(item_id, str) or item_id == "":
        raise OneDriveError("Reading remote item returned an unexpected response.")

    if not yes:
        answer = typer.prompt(f"Move {remote_path} to the OneDrive recycle bin? Type DELETE")
        if answer != "DELETE":
            raise OneDriveError("Deletion cancelled.")

    response = send_request("DELETE", f"{GRAPH_BASE}/me/drive/items/{quote(item_id, safe='')}", headers=graph_headers(access_token))
    if response.status_code != 204:
        raise OneDriveError(f"Delete failed with HTTP {response.status_code}.")
    typer.echo(f"Moved {remote_path} to the OneDrive recycle bin.")
