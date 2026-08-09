import time
from collections.abc import Mapping
from typing import IO, Literal, TypedDict, Unpack, cast
from urllib.parse import quote

import requests
import typer

from stackops.utils.cloud.onedrive.constants import DEVICE_ENDPOINT, REQUEST_TIMEOUT, SCOPE_TEXT, TOKEN_ENDPOINT
from stackops.utils.cloud.onedrive.credentials import load_credentials, save_refresh_token
from stackops.utils.cloud.onedrive.errors import OneDriveError


type RequestMethod = Literal["GET", "POST", "PUT", "DELETE"]


class RequestOptions(TypedDict, total=False):
    headers: Mapping[str, str]
    data: Mapping[str, str] | IO[bytes]
    params: Mapping[str, str | int]
    allow_redirects: bool
    stream: bool


def send_request(method: RequestMethod, url: str, **options: Unpack[RequestOptions]) -> requests.Response:
    try:
        return requests.request(method, url, timeout=REQUEST_TIMEOUT, **options)
    except requests.RequestException as exc:
        raise OneDriveError(f"Network request failed: {exc}") from exc


def response_json(response: requests.Response, operation: str) -> dict[str, object]:
    try:
        payload: object = response.json()
    except requests.exceptions.JSONDecodeError as exc:
        if response.ok:
            raise OneDriveError(f"{operation} returned invalid JSON.") from exc
        raise OneDriveError(f"{operation} failed with HTTP {response.status_code}.") from exc

    if not isinstance(payload, dict) or not all(isinstance(key, str) for key in payload):
        raise OneDriveError(f"{operation} returned an unexpected response.")
    return cast(dict[str, object], payload)


def _error_description(payload: Mapping[str, object], fallback: str) -> str:
    description = payload.get("error_description")
    if isinstance(description, str) and description:
        return description

    error = payload.get("error")
    if isinstance(error, Mapping):
        message = error.get("message")
        if isinstance(message, str) and message:
            return message
    if isinstance(error, str) and error:
        return error
    return fallback


def require_success(response: requests.Response, operation: str) -> dict[str, object]:
    payload = response_json(response, operation)
    if not response.ok:
        fallback = f"{operation} failed with HTTP {response.status_code}."
        raise OneDriveError(_error_description(payload, fallback))
    return payload


def graph_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def graph_json(method: RequestMethod, url: str, access_token: str, operation: str, *, params: Mapping[str, str | int] | None) -> dict[str, object]:
    if params is None:
        response = send_request(method, url, headers=graph_headers(access_token))
    else:
        response = send_request(method, url, headers=graph_headers(access_token), params=params)
    return require_success(response, operation)


def encoded_remote_path(remote_path: str) -> str:
    return quote(remote_path.lstrip("/"), safe="/")


def _authorization_pending(device_code: str, poll_interval: int, account_name: str, client_id: str) -> None:
    while True:
        response = send_request(
            "POST",
            TOKEN_ENDPOINT,
            data={"grant_type": "urn:ietf:params:oauth:grant-type:device_code", "client_id": client_id, "device_code": device_code},
        )
        payload = response_json(response, "Authentication")
        access_token = payload.get("access_token")
        refresh_token = payload.get("refresh_token")
        if response.ok and isinstance(access_token, str) and access_token and isinstance(refresh_token, str) and refresh_token:
            save_refresh_token(account_name=account_name, client_id=client_id, refresh_token=refresh_token)
            typer.echo(f"Authentication saved for OneDrive account {account_name}.")
            return

        oauth_error = payload.get("error")
        match oauth_error:
            case "authorization_pending":
                time.sleep(poll_interval)
            case "slow_down":
                poll_interval += 5
                time.sleep(poll_interval)
            case _:
                raise OneDriveError(_error_description(payload, "Authentication failed."))


def authenticate(account_name: str) -> None:
    credentials = load_credentials(account_name=account_name, require_refresh_token=False)
    client_id = credentials["client_id"]
    response = send_request("POST", DEVICE_ENDPOINT, data={"client_id": client_id, "scope": SCOPE_TEXT})
    payload = require_success(response, "Authentication")

    device_code = payload.get("device_code")
    user_code = payload.get("user_code")
    verification_uri = payload.get("verification_uri")
    poll_interval = payload.get("interval")
    if (
        not isinstance(device_code, str)
        or not device_code
        or not isinstance(user_code, str)
        or not user_code
        or not isinstance(verification_uri, str)
        or not verification_uri
        or isinstance(poll_interval, bool)
        or not isinstance(poll_interval, int)
        or poll_interval < 1
    ):
        raise OneDriveError("Authentication returned an unexpected response.")

    typer.echo(f"Open {verification_uri} and enter code {user_code}")
    _authorization_pending(device_code=device_code, poll_interval=poll_interval, account_name=account_name, client_id=client_id)


def refresh_access_token(account_name: str) -> str:
    credentials = load_credentials(account_name=account_name, require_refresh_token=True)
    client_id = credentials["client_id"]
    refresh_token = credentials["refresh_token"]
    if refresh_token is None:
        raise OneDriveError(f"OneDrive account {account_name} is not authenticated. Run: cloud onedrive auth --account-name {account_name}")

    response = send_request(
        "POST", TOKEN_ENDPOINT, data={"grant_type": "refresh_token", "client_id": client_id, "refresh_token": refresh_token, "scope": SCOPE_TEXT}
    )
    payload = response_json(response, "Token refresh")
    access_token = payload.get("access_token")
    if not response.ok or not isinstance(access_token, str) or not access_token:
        raise OneDriveError(_error_description(payload, "Token refresh failed."))

    rotated_refresh_token = payload.get("refresh_token")
    if rotated_refresh_token is None or rotated_refresh_token == "":
        rotated_refresh_token = refresh_token
    if not isinstance(rotated_refresh_token, str):
        raise OneDriveError("Token refresh returned an invalid refresh token.")
    save_refresh_token(account_name=account_name, client_id=client_id, refresh_token=rotated_refresh_token)
    return access_token
