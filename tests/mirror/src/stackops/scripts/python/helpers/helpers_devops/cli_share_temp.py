from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest
import requests
import typer

from stackops.scripts.python.helpers.helpers_devops import cli_share_temp as module


@dataclass
class FakeResponse:
    headers: dict[str, str]
    text: str
    json_payload: object | None

    def json(self) -> object:
        if isinstance(self.json_payload, Exception):
            raise self.json_payload
        return self.json_payload

    def raise_for_status(self) -> None:
        return None


def test_extract_url_prefers_json_fields() -> None:
    response = cast(
        requests.Response,
        FakeResponse(
            headers={"content-type": "application/json; charset=utf-8"},
            text='{"url": "https://temp.sh/file.txt"}',
            json_payload={"url": "https://temp.sh/file.txt"},
        ),
    )

    assert module._extract_url(response) == "https://temp.sh/file.txt"


def test_extract_url_falls_back_to_plain_text_tokens() -> None:
    response = cast(
        requests.Response,
        FakeResponse(
            headers={"content-type": "text/plain"},
            text="done https://temp.sh/file.txt now",
            json_payload=None,
        ),
    )

    assert module._extract_url(response) == "https://temp.sh/file.txt"


def test_upload_file_handle_posts_expected_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded_files: list[dict[str, tuple[str, object, str] | tuple[str, object]]] = []

    def fake_post(
        url: str,
        *,
        files: dict[str, tuple[str, object, str] | tuple[str, object]],
        timeout: int,
    ) -> requests.Response:
        assert url == module.UPLOAD_ENDPOINT
        assert timeout == module.REQUEST_TIMEOUT_SECONDS
        recorded_files.append(files)
        return cast(
            requests.Response,
            FakeResponse(
                headers={"content-type": "application/json"},
                text='{"link": "https://temp.sh/uploaded.txt"}',
                json_payload={"link": "https://temp.sh/uploaded.txt"},
            ),
        )

    monkeypatch.setattr(requests, "post", fake_post)

    result = module._upload_file_handle(file_name="note.txt", file_handle=b"hello", content_type="text/plain")

    assert result == "https://temp.sh/uploaded.txt"
    assert recorded_files == [{"file": ("note.txt", b"hello", "text/plain")}]


def test_upload_file_converts_request_errors_to_typer_exit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    file_path = tmp_path.joinpath("note.txt")
    file_path.write_text("hello", encoding="utf-8")

    def fake_upload_file_handle(*, file_name: str, file_handle: object, content_type: str | None) -> str:
        assert file_name == "note.txt"
        assert content_type is None
        raise requests.RequestException("boom")

    monkeypatch.setattr(module, "_upload_file_handle", fake_upload_file_handle)

    with pytest.raises(typer.Exit) as exc_info:
        module.upload_file(file_path=file_path)

    assert exc_info.value.exit_code == 1
    assert "Upload failed: boom" in capsys.readouterr().out


def test_upload_text_reads_stdin(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    recorded_payloads: list[tuple[str, bytes, str | None]] = []

    def fake_upload_file_handle(*, file_name: str, file_handle: object, content_type: str | None) -> str:
        assert isinstance(file_handle, bytes)
        recorded_payloads.append((file_name, file_handle, content_type))
        return "https://temp.sh/text.txt"

    monkeypatch.setattr(module, "_upload_file_handle", fake_upload_file_handle)
    monkeypatch.setattr(module.sys, "stdin", io.StringIO("hello from stdin"))

    module.upload_text(text="-")

    assert recorded_payloads == [("text.txt", b"hello from stdin", "text/plain; charset=utf-8")]
    assert capsys.readouterr().out.strip() == "https://temp.sh/text.txt"
