from collections.abc import Mapping
from typing import TYPE_CHECKING, Annotated, BinaryIO, cast

import typer

if TYPE_CHECKING:
    import requests


REQUEST_TIMEOUT_SECONDS: int = 30
TEMP_BASE_URL: str = "https://temp.sh"
UPLOAD_ENDPOINT: str = f"{TEMP_BASE_URL}/upload"
STDIN_FILE_NAME: str = "stdin.bin"
TEXT_FILE_NAME: str = "text.txt"
TEXT_CONTENT_TYPE: str = "text/plain; charset=utf-8"
URL_RESPONSE_KEYS: tuple[str, str, str] = ("url", "link", "download")


class UploadResponseError(RuntimeError):
    pass


def _normalize_http_url(value: str) -> str | None:
    from urllib.parse import urlparse

    candidate = value.strip()
    parsed = urlparse(candidate)
    if parsed.scheme in {"http", "https"} and parsed.netloc != "":
        return candidate
    return None


def _extract_url(response: "requests.Response") -> str:
    content_type = response.headers.get("content-type", "").lower()
    text = response.text.strip()
    if "application/json" in content_type:
        try:
            data = cast(object, response.json())
        except ValueError:
            data = None
        if isinstance(data, Mapping):
            for key in URL_RESPONSE_KEYS:
                url_value = data.get(key)
                if isinstance(url_value, str):
                    url = _normalize_http_url(value=url_value)
                    if url is not None:
                        return url
    for token in text.split():
        url = _normalize_http_url(value=token)
        if url is not None:
            return url
    raise UploadResponseError("Upload succeeded but temp.sh did not return a URL.")


def _upload_file_handle(file_name: str, file_handle: BinaryIO | bytes, content_type: str | None) -> str:
    import requests

    files: dict[str, tuple[str, BinaryIO | bytes, str] | tuple[str, BinaryIO | bytes]]
    if content_type is None:
        files = {"file": (file_name, file_handle)}
    else:
        files = {"file": (file_name, file_handle, content_type)}
    response = requests.post(UPLOAD_ENDPOINT, files=files, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return _extract_url(response=response)


def upload_file(file_path: Annotated[str, typer.Argument(...)]) -> None:
    """Upload a file to temp.sh (unsecure) and print the resulting URL. Use '-' as the file path to read from stdin."""
    import sys
    from pathlib import Path

    import requests

    try:
        if file_path == "-":
            stdin_payload = sys.stdin.buffer.read()
            url = _upload_file_handle(file_name=STDIN_FILE_NAME, file_handle=stdin_payload, content_type=None)
        else:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {path}")
            if path.is_dir():
                raise IsADirectoryError(f"Expected a file path, got directory: {path}")
            with path.open("rb") as file_handle:
                url = _upload_file_handle(file_name=path.name, file_handle=file_handle, content_type=None)
    except (OSError, requests.RequestException, UploadResponseError) as exc:
        typer.echo(f"Upload failed: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(url)


def upload_text(text: Annotated[str, typer.Argument(...)]) -> None:
    import sys

    import requests

    text_value = text
    if text == "-":
        text_value = sys.stdin.read()
    try:
        payload = text_value.encode("utf-8")
        url = _upload_file_handle(file_name=TEXT_FILE_NAME, file_handle=payload, content_type=TEXT_CONTENT_TYPE)
    except (OSError, requests.RequestException, UploadResponseError) as exc:
        typer.echo(f"Upload failed: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(url)
