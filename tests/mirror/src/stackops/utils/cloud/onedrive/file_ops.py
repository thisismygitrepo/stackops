from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest

from stackops.utils.cloud.onedrive import file_ops


@dataclass(slots=True)
class FakeGraphResponse:
    status_code: int
    payload: dict[str, object]
    text: str = ""

    def json(self) -> dict[str, object]:
        return self.payload


@dataclass(slots=True)
class FakeDownloadResponse:
    chunks: tuple[bytes, ...]
    status_code: int = 200
    text: str = ""

    def iter_content(self, chunk_size: int) -> Iterator[bytes]:
        _ = chunk_size
        yield from self.chunks

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(self.text or "download failed")


def test_push_to_onedrive_normalizes_path_and_uses_simple_upload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    local_file = tmp_path.joinpath("report.txt")
    local_file.write_text("payload", encoding="utf-8")
    created_dirs: list[str] = []
    upload_calls: list[tuple[Path, str, str]] = []

    def fake_create_remote_directory(remote_path: str, section: str) -> bool:
        created_dirs.append(remote_path)
        assert section == "work"
        return True

    def fake_simple_upload(local_path: Path, remote_path: str, section: str) -> bool:
        upload_calls.append((local_path, remote_path, section))
        return True

    def fake_resumable_upload(local_path: Path, remote_path: str, section: str) -> bool:
        raise AssertionError(f"unexpected resumable upload for {local_path} -> {remote_path} ({section})")

    monkeypatch.setattr(file_ops, "create_remote_directory", fake_create_remote_directory)
    monkeypatch.setattr(file_ops, "simple_upload", fake_simple_upload)
    monkeypatch.setattr(file_ops, "resumable_upload", fake_resumable_upload)

    success = file_ops.push_to_onedrive(str(local_file), "nested/report.txt", section="work")

    assert success
    assert created_dirs == ["/nested"]
    assert upload_calls == [(local_file, "/nested/report.txt", "work")]


def test_simple_upload_quotes_remote_path_and_sends_file_bytes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    local_file = tmp_path.joinpath("name with spaces.txt")
    local_file.write_bytes(b"abc")
    request_calls: list[tuple[str, str, bytes]] = []

    def fake_get_drive_id(section: str) -> str | None:
        assert section == "work"
        return "drive-123"

    def fake_make_graph_request(method: str, endpoint: str, section: str, data: bytes) -> FakeGraphResponse:
        request_calls.append((method, endpoint, data))
        assert section == "work"
        return FakeGraphResponse(status_code=201, payload={})

    monkeypatch.setattr(file_ops, "get_drive_id", fake_get_drive_id)
    monkeypatch.setattr(file_ops, "make_graph_request", fake_make_graph_request)

    success = file_ops.simple_upload(local_file, "/folder/name with spaces.txt", section="work")

    assert success
    assert request_calls == [("PUT", "drives/drive-123/root:/folder/name%20with%20spaces.txt:/content", b"abc")]


def test_pull_from_onedrive_downloads_file_contents(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    local_file = tmp_path.joinpath("downloads", "report.txt")

    def fake_get_drive_id(section: str) -> str | None:
        assert section == "work"
        return "drive-123"

    def fake_make_graph_request(method: str, endpoint: str, section: str) -> FakeGraphResponse:
        assert method == "GET"
        assert section == "work"
        assert endpoint == "drives/drive-123/root:/docs/report.txt"
        return FakeGraphResponse(status_code=200, payload={"@microsoft.graph.downloadUrl": "https://download.example/report", "size": 4})

    def fake_get(url: str, stream: bool) -> FakeDownloadResponse:
        assert url == "https://download.example/report"
        assert stream
        return FakeDownloadResponse(chunks=(b"ab", b"cd"))

    monkeypatch.setattr(file_ops, "get_drive_id", fake_get_drive_id)
    monkeypatch.setattr(file_ops, "make_graph_request", fake_make_graph_request)
    monkeypatch.setattr(file_ops.requests, "get", fake_get)

    success = file_ops.pull_from_onedrive("/docs/report.txt", str(local_file), section="work")

    assert success
    assert local_file.read_bytes() == b"abcd"


def test_create_remote_directory_creates_missing_parent_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def fake_get_drive_id(section: str) -> str | None:
        assert section == "work"
        return "drive-123"

    def fake_make_graph_request(method: str, endpoint: str, section: str, json: dict[str, object] | None = None) -> FakeGraphResponse:
        calls.append((method, endpoint, json))
        assert section == "work"
        if method == "GET" and endpoint in {"drives/drive-123/root:/parent/child", "drives/drive-123/root:/parent"}:
            return FakeGraphResponse(status_code=404, payload={})
        if method == "POST" and endpoint in {"drives/drive-123/root/children", "drives/drive-123/root:/parent:/children"}:
            return FakeGraphResponse(status_code=201, payload={})
        raise AssertionError(f"unexpected request: {method} {endpoint}")

    monkeypatch.setattr(file_ops, "get_drive_id", fake_get_drive_id)
    monkeypatch.setattr(file_ops, "make_graph_request", fake_make_graph_request)

    success = file_ops.create_remote_directory("/parent/child", section="work")

    assert success
    assert calls == [
        ("GET", "drives/drive-123/root:/parent/child", None),
        ("GET", "drives/drive-123/root:/parent", None),
        ("POST", "drives/drive-123/root/children", {"name": "parent", "folder": {}, "@microsoft.graph.conflictBehavior": "replace"}),
        ("POST", "drives/drive-123/root:/parent:/children", {"name": "child", "folder": {}, "@microsoft.graph.conflictBehavior": "replace"}),
    ]
