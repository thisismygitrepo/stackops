

from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
from types import ModuleType, SimpleNamespace

import pytest

from stackops.scripts.python.helpers.helpers_utils import download as subject


class FakeRequestException(Exception):
    pass


@dataclass(slots=True)
class FakeResponse:
    headers: dict[str, str]
    url: str
    body_chunks: list[bytes]

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object,
    ) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    @property
    def content(self) -> bytes:
        return b"".join(self.body_chunks)

    def iter_content(self, chunk_size: int) -> list[bytes]:
        assert chunk_size == 8192 * 40
        return self.body_chunks


def install_requests_module(
    monkeypatch: pytest.MonkeyPatch,
    response: FakeResponse,
    request_exception: FakeRequestException | None = None,
) -> None:
    requests_module = ModuleType("requests")

    class Response:
        pass

    def get(
        url: str,
        allow_redirects: bool,
        stream: bool,
        timeout: int,
    ) -> FakeResponse:
        _ = url
        assert allow_redirects is True
        assert stream is True
        assert timeout == 60
        if request_exception is not None:
            raise request_exception
        return response

    setattr(requests_module, "Response", Response)
    setattr(requests_module, "get", get)
    setattr(
        requests_module,
        "exceptions",
        SimpleNamespace(RequestException=FakeRequestException),
    )
    monkeypatch.setitem(sys.modules, "requests", requests_module)


def test_download_uses_content_disposition_filename_and_streams_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = FakeResponse(
        headers={
            "content-disposition": "attachment; filename*=UTF-8''report%20name.bin",
            "content-length": "6",
        },
        url="https://example.com/final",
        body_chunks=[b"abc", b"def"],
    )
    install_requests_module(monkeypatch, response=response)

    result = subject.download(
        url="https://example.com/download?id=1",
        decompress=False,
        output=None,
        output_dir=str(tmp_path / "out"),
    )

    expected_path = (tmp_path / "out" / "report name.bin").resolve()
    assert result == expected_path
    assert expected_path.read_bytes() == b"abcdef"


def test_download_decompresses_archive_and_removes_original(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = FakeResponse(
        headers={"content-length": "3"},
        url="https://example.com/files/archive.tar.gz",
        body_chunks=[b"tar"],
    )
    install_requests_module(monkeypatch, response=response)
    commands: list[list[str]] = []

    def fake_run(
        command: list[str],
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        assert check is True
        assert capture_output is True
        assert text is True
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    archive_path = tmp_path / "downloads" / "bundle.tar.gz"

    result = subject.download(
        url="https://example.com/archive",
        decompress=True,
        output=str(archive_path),
        output_dir=None,
    )

    extract_dir = archive_path.parent / "bundle"
    assert commands == [["ouch", "decompress", str(archive_path), "--dir", str(extract_dir)]]
    assert not archive_path.exists()
    assert result == extract_dir.resolve()


def test_download_rejects_conflicting_output_arguments(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_requests_module(
        monkeypatch,
        response=FakeResponse(headers={}, url="https://example.com", body_chunks=[]),
    )

    result = subject.download(
        url="https://example.com/file.txt",
        decompress=False,
        output=str(tmp_path / "file.txt"),
        output_dir=str(tmp_path / "out"),
    )

    assert result is None
