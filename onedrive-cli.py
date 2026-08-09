#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "requests>=2.32,<3",
#     "typer>=0.16,<1",
# ]
# ///

"""A small Microsoft OneDrive CLI backed by Microsoft Graph."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

import requests
import typer


SCOPES = "User.Read Files.ReadWrite offline_access"
DEVICE_ENDPOINT = (
    "https://login.microsoftonline.com/consumers/oauth2/v2.0/devicecode"
)
TOKEN_ENDPOINT = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
GRAPH_BASE = "https://graph.microsoft.com/v1.0"
REQUEST_TIMEOUT = 30


def _config_dir() -> Path:
    override = os.environ.get("ONEDRIVE_CLI_CONFIG_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / "dotfiles" / "creds" / "onedrive-cli"


def _token_file() -> Path:
    return _config_dir() / "token.json"


class CliError(Exception):
    """An expected error that is safe to show to the user."""


app = typer.Typer(
    add_completion=False,
    help="Access OneDrive through Microsoft Graph.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)


def _request(method: str, url: str, **kwargs: Any) -> requests.Response:
    kwargs.setdefault("timeout", REQUEST_TIMEOUT)
    try:
        return requests.request(method, url, **kwargs)
    except requests.RequestException as exc:
        raise CliError(f"Network request failed: {exc}") from exc


def _response_json(response: requests.Response, operation: str) -> dict[str, Any]:
    try:
        payload = response.json()
    except requests.exceptions.JSONDecodeError as exc:
        if response.ok:
            raise CliError(f"{operation} returned invalid JSON.") from exc
        raise CliError(f"{operation} failed with HTTP {response.status_code}.") from exc

    if not isinstance(payload, dict):
        raise CliError(f"{operation} returned an unexpected response.")
    return payload


def _error_description(payload: dict[str, Any], fallback: str) -> str:
    description = payload.get("error_description")
    if isinstance(description, str) and description:
        return description

    error = payload.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str) and message:
            return message
    return fallback


def _require_success(response: requests.Response, operation: str) -> dict[str, Any]:
    payload = _response_json(response, operation)
    if not response.ok:
        raise CliError(
            _error_description(
                payload, f"{operation} failed with HTTP {response.status_code}."
            )
        )
    return payload


def _prepare_config_directory() -> Path:
    config_dir = _config_dir()
    try:
        config_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        config_dir.chmod(0o700)
    except OSError as exc:
        raise CliError(f"Unable to prepare config directory: {exc}") from exc
    return config_dir


def _load_token_data() -> dict[str, Any]:
    token_file = _token_file()
    if not token_file.is_file():
        raise CliError(
            "token.json is missing. Add a client_id before authenticating."
        )

    try:
        stored = json.loads(token_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CliError("Unable to read token.json.") from exc

    if not isinstance(stored, dict):
        raise CliError("token.json must contain a JSON object.")
    return stored


def _client_id(token_data: dict[str, Any] | None = None) -> str:
    if token_data is None:
        token_data = _load_token_data()

    client_id = token_data.get("client_id")
    if not isinstance(client_id, str) or not client_id:
        raise CliError("token.json does not contain a valid client_id.")
    return client_id


def _save_refresh_token(
    token_response: dict[str, Any],
    client_id: str,
    previous_refresh_token: str = "",
) -> None:
    refresh_token = token_response.get("refresh_token") or previous_refresh_token
    if not isinstance(refresh_token, str) or not refresh_token:
        raise CliError("Microsoft did not return a refresh token.")

    config_dir = _prepare_config_directory()
    token_data = {
        "client_id": client_id,
        "authority": "consumers",
        "scopes": SCOPES,
        "refresh_token": refresh_token,
    }
    temporary_path: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix="token.", dir=config_dir
        )
        temporary_path = Path(temporary_name)
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(token_data, stream)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, _token_file())
        temporary_path = None
    except OSError as exc:
        raise CliError(f"Unable to save authentication: {exc}") from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _authorization_pending(
    device_code: str, poll_interval: int, client_id: str
) -> None:
    while True:
        response = _request(
            "POST",
            TOKEN_ENDPOINT,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "client_id": client_id,
                "device_code": device_code,
            },
        )
        payload = _response_json(response, "Authentication")
        if response.ok and payload.get("access_token") and payload.get("refresh_token"):
            _save_refresh_token(payload, client_id)
            typer.echo(f"Authentication saved to {_token_file()}")
            return

        oauth_error = payload.get("error")
        if oauth_error == "authorization_pending":
            time.sleep(poll_interval)
        elif oauth_error == "slow_down":
            poll_interval += 5
            time.sleep(poll_interval)
        else:
            raise CliError(_error_description(payload, "Authentication failed."))


def _refresh_access_token() -> str:
    stored = _load_token_data()
    client_id = _client_id(stored)
    refresh_token = stored.get("refresh_token") if isinstance(stored, dict) else None
    if not isinstance(refresh_token, str) or not refresh_token:
        raise CliError("The saved authentication is invalid. Run: onedrive-cli auth")

    response = _request(
        "POST",
        TOKEN_ENDPOINT,
        data={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "refresh_token": refresh_token,
            "scope": SCOPES,
        },
    )
    payload = _response_json(response, "Token refresh")
    access_token = payload.get("access_token")
    if not response.ok or not isinstance(access_token, str) or not access_token:
        raise CliError(_error_description(payload, "Token refresh failed."))

    _save_refresh_token(payload, client_id, refresh_token)
    return access_token


def _encoded_remote_path(remote_path: str) -> str:
    return quote(remote_path.lstrip("/"), safe="/")


def _graph_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _graph_json(
    method: str,
    url: str,
    access_token: str,
    operation: str,
    **kwargs: Any,
) -> dict[str, Any]:
    headers = dict(kwargs.pop("headers", {}))
    headers.update(_graph_headers(access_token))
    response = _request(method, url, headers=headers, **kwargs)
    return _require_success(response, operation)


def _json_output(payload: Any) -> None:
    json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
    typer.echo()


def _display_cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\t", " ").replace("\r", " ").replace("\n", " ")


def _print_table(headers: Sequence[str], rows: Iterable[Sequence[Any]]) -> None:
    rendered = [[_display_cell(value) for value in row] for row in rows]
    widths = [len(header) for header in headers]
    for row in rendered:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))

    typer.echo("  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    for row in rendered:
        typer.echo("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)))


@app.command("auth", short_help="<a> Authenticate with Microsoft")
def authenticate() -> None:
    """Authenticate using Microsoft's device-code flow."""
    client_id = _client_id()
    response = _request(
        "POST",
        DEVICE_ENDPOINT,
        data={"client_id": client_id, "scope": SCOPES},
    )
    payload = _require_success(response, "Authentication")

    try:
        device_code = str(payload["device_code"])
        user_code = str(payload["user_code"])
        verification_uri = str(payload["verification_uri"])
        poll_interval = int(payload["interval"])
    except (KeyError, TypeError, ValueError) as exc:
        raise CliError("Authentication returned an unexpected response.") from exc

    typer.echo(f"Open {verification_uri} and enter code {user_code}")
    _authorization_pending(device_code, poll_interval, client_id)


@app.command("status", short_help="<t> Show account and storage status")
def show_status() -> None:
    """Show account and storage quota information."""
    access_token = _refresh_access_token()
    payload = _graph_json(
        "GET",
        f"{GRAPH_BASE}/me/drive",
        access_token,
        "Reading drive status",
        params={"$select": "driveType,owner,quota,webUrl"},
    )
    owner = payload.get("owner") or {}
    user = owner.get("user") or {} if isinstance(owner, dict) else {}
    quota = payload.get("quota") or {}
    if not isinstance(quota, dict):
        quota = {}
    _json_output(
        {
            "account": user.get("displayName") if isinstance(user, dict) else None,
            "drive_type": payload.get("driveType"),
            "used_bytes": quota.get("used"),
            "total_bytes": quota.get("total"),
            "web_url": payload.get("webUrl"),
        }
    )


@app.command("ls", short_help="<l> List a remote folder")
def list_items(
    remote_path: str = typer.Argument("/", help="Remote folder path."),
) -> None:
    """List the contents of a remote folder."""
    encoded_path = _encoded_remote_path(remote_path)
    if encoded_path:
        endpoint = f"{GRAPH_BASE}/me/drive/root:/{encoded_path}:/children"
    else:
        endpoint = f"{GRAPH_BASE}/me/drive/root/children"

    access_token = _refresh_access_token()
    payload = _graph_json(
        "GET",
        endpoint,
        access_token,
        "Listing remote items",
        params={
            "$select": "name,size,lastModifiedDateTime,folder,file",
            "$orderby": "name",
            "$top": 200,
        },
    )
    items = payload.get("value")
    if not isinstance(items, list):
        raise CliError("Listing remote items returned an unexpected response.")
    _print_table(
        ("NAME", "TYPE", "SIZE (BYTES)", "LAST MODIFIED"),
        (
            (
                item.get("name"),
                "folder" if item.get("folder") is not None else "file",
                item.get("size"),
                item.get("lastModifiedDateTime"),
            )
            for item in items
            if isinstance(item, dict)
        ),
    )


def _validated_next_link(next_link: Any) -> str | None:
    if next_link is None:
        return None
    if not isinstance(next_link, str):
        raise CliError("Search returned an invalid pagination link.")
    graph_host = urlsplit(GRAPH_BASE).netloc
    parts = urlsplit(next_link)
    if parts.scheme != "https" or parts.netloc != graph_host:
        raise CliError("Search returned an untrusted pagination link.")
    return next_link


@app.command("search", short_help="<s> Search the drive")
def search_items(
    query: str = typer.Argument(..., help="Text to search for."),
    output_json: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Search the entire drive."""
    odata_query = quote(query.replace("'", "''"), safe="")
    next_url: str | None = f"{GRAPH_BASE}/me/drive/root/search(q='{odata_query}')"
    access_token = _refresh_access_token()
    items_by_id: dict[str, dict[str, Any]] = {}
    params: dict[str, Any] | None = {
        "$select": (
            "id,name,size,lastModifiedDateTime,folder,file,parentReference,webUrl"
        ),
        "$top": 200,
    }

    while next_url:
        payload = _graph_json(
            "GET",
            next_url,
            access_token,
            "Searching remote items",
            params=params,
        )
        page = payload.get("value")
        if not isinstance(page, list):
            raise CliError("Search returned an unexpected response.")
        for item in page:
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                items_by_id[item["id"]] = item
        next_url = _validated_next_link(payload.get("@odata.nextLink"))
        params = None

    items = [items_by_id[item_id] for item_id in sorted(items_by_id)]
    if output_json:
        _json_output(
            [
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "type": "folder" if item.get("folder") is not None else "file",
                    "size": item.get("size"),
                    "last_modified": item.get("lastModifiedDateTime"),
                    "parent_path": (item.get("parentReference") or {}).get("path"),
                    "web_url": item.get("webUrl"),
                }
                for item in items
            ]
        )
        return

    _print_table(
        ("NAME", "TYPE", "SIZE (BYTES)", "PARENT", "LAST MODIFIED"),
        (
            (
                item.get("name"),
                "folder" if item.get("folder") is not None else "file",
                item.get("size"),
                (item.get("parentReference") or {}).get("path"),
                item.get("lastModifiedDateTime"),
            )
            for item in items
        ),
    )


@app.command("download", short_help="<w> Download a remote file")
def download_file(
    remote_path: str = typer.Argument(..., help="Remote file path."),
    local_path: Path = typer.Argument(..., help="New local file path."),
) -> None:
    """Download a remote file without overwriting local files."""
    if local_path.exists():
        raise CliError(f"Local target already exists: {local_path}")
    encoded_path = _encoded_remote_path(remote_path)
    if not encoded_path:
        raise CliError("Remote file path cannot be root.")

    try:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".onedrive-download.", dir=local_path.parent
        )
        os.close(descriptor)
    except OSError as exc:
        raise CliError(f"Unable to prepare the local target: {exc}") from exc

    temporary_path = Path(temporary_name)
    access_token = _refresh_access_token()
    try:
        response = _request(
            "GET",
            f"{GRAPH_BASE}/me/drive/root:/{encoded_path}:/content",
            headers=_graph_headers(access_token),
            allow_redirects=True,
            stream=True,
        )
        if not response.ok:
            payload = _response_json(response, "Downloading remote file")
            raise CliError(
                _error_description(
                    payload,
                    f"Download failed with HTTP {response.status_code}.",
                )
            )
        with response, temporary_path.open("wb") as stream:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    stream.write(chunk)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, local_path)
    except (OSError, requests.RequestException) as exc:
        raise CliError(f"Unable to download the file: {exc}") from exc
    finally:
        temporary_path.unlink(missing_ok=True)

    typer.echo(f"Downloaded {remote_path} to {local_path}")


@app.command("upload", short_help="<u> Upload a local file")
def upload_file(
    local_path: Path = typer.Argument(..., help="Existing local file path."),
    remote_path: str = typer.Argument(..., help="Remote target path."),
    overwrite: bool = typer.Option(
        False, "--overwrite", help="Replace an existing remote item."
    ),
) -> None:
    """Upload a local file, optionally replacing the remote target."""
    if not local_path.is_file():
        raise CliError(f"Local source is not a file: {local_path}")
    encoded_path = _encoded_remote_path(remote_path)
    if not encoded_path:
        raise CliError("Remote file path cannot be root.")

    access_token = _refresh_access_token()
    target_url = f"{GRAPH_BASE}/me/drive/root:/{encoded_path}"
    metadata = _request("GET", target_url, headers=_graph_headers(access_token))
    if metadata.status_code == 200:
        if not overwrite:
            raise CliError("Remote target exists. Pass --overwrite to replace it.")
    elif metadata.status_code != 404:
        raise CliError(
            "Unable to inspect remote target; Microsoft Graph returned "
            f"HTTP {metadata.status_code}."
        )

    try:
        with local_path.open("rb") as stream:
            response = _request(
                "PUT",
                f"{target_url}:/content",
                headers={
                    **_graph_headers(access_token),
                    "Content-Type": "application/octet-stream",
                },
                data=stream,
            )
    except OSError as exc:
        raise CliError(f"Unable to read local source: {exc}") from exc
    payload = _require_success(response, "Uploading local file")
    _json_output(
        {
            "name": payload.get("name"),
            "size": payload.get("size"),
            "webUrl": payload.get("webUrl"),
        }
    )


@app.command("delete", short_help="<d> Move an item to the recycle bin")
def delete_item(
    remote_path: str = typer.Argument(..., help="Remote item path."),
    yes: bool = typer.Option(False, "--yes", help="Skip the confirmation prompt."),
) -> None:
    """Move a remote item to the OneDrive recycle bin."""
    encoded_path = _encoded_remote_path(remote_path)
    if not encoded_path:
        raise CliError("Refusing to delete the OneDrive root.")

    access_token = _refresh_access_token()
    item = _graph_json(
        "GET",
        f"{GRAPH_BASE}/me/drive/root:/{encoded_path}",
        access_token,
        "Reading remote item",
    )
    item_id = item.get("id")
    if not isinstance(item_id, str) or not item_id:
        raise CliError("Reading remote item returned an unexpected response.")

    if not yes:
        answer = typer.prompt(
            f"Move {remote_path} to the OneDrive recycle bin? Type DELETE"
        )
        if answer != "DELETE":
            raise CliError("Deletion cancelled.")

    response = _request(
        "DELETE",
        f"{GRAPH_BASE}/me/drive/items/{quote(item_id, safe='')}",
        headers=_graph_headers(access_token),
    )
    if response.status_code != 204:
        raise CliError(f"Delete failed with HTTP {response.status_code}.")
    typer.echo(f"Moved {remote_path} to the OneDrive recycle bin.")


@app.command("config-path", short_help="<c> Print the authentication file path")
def config_path() -> None:
    """Print the path to the private authentication file."""
    typer.echo(_token_file())


def register_aliases() -> None:
    app.command("a", hidden=True, help="Alias for auth.")(authenticate)
    app.command("t", hidden=True, help="Alias for status.")(show_status)
    app.command("l", hidden=True, help="Alias for ls.")(list_items)
    app.command("s", hidden=True, help="Alias for search.")(search_items)
    app.command("w", hidden=True, help="Alias for download.")(download_file)
    app.command("u", hidden=True, help="Alias for upload.")(upload_file)
    app.command("d", hidden=True, help="Alias for delete.")(delete_item)
    app.command("c", hidden=True, help="Alias for config-path.")(config_path)


register_aliases()


def main() -> None:
    try:
        app()
    except CliError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
