from pathlib import Path
import subprocess
from typing import cast

import pytest
import requests

import machineconfig.jobs.installer.python_scripts.winget as winget
from machineconfig.utils.schemas.installer.installer_types import InstallerData


def _installer_data() -> InstallerData:
    return cast(InstallerData, {})


class JsonResponse:
    def __init__(self, payload: dict[str, object], raise_error: bool) -> None:
        self._payload = payload
        self._raise_error = raise_error

    def raise_for_status(self) -> None:
        if self._raise_error:
            raise requests.HTTPError("boom")

    def json(self) -> dict[str, object]:
        return self._payload


class DownloadResponse:
    def __init__(self, chunks: list[bytes], raise_error: bool) -> None:
        self._chunks = chunks
        self._raise_error = raise_error

    def raise_for_status(self) -> None:
        if self._raise_error:
            raise requests.HTTPError("boom")

    def iter_content(self, chunk_size: int) -> list[bytes]:
        assert chunk_size == 8192
        return self._chunks


def test_is_winget_available_returns_true_on_zero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: list[str], capture_output: bool, text: bool, timeout: int) -> subprocess.CompletedProcess[str]:
        assert command == ["winget", "--version"]
        assert capture_output is True
        assert text is True
        assert timeout == 10
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="1.0.0")

    monkeypatch.setattr(winget.subprocess, "run", fake_run)

    assert winget.is_winget_available() is True


def test_is_winget_available_returns_false_when_command_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: list[str], capture_output: bool, text: bool, timeout: int) -> subprocess.CompletedProcess[str]:
        _ = command, capture_output, text, timeout
        raise FileNotFoundError("winget not found")

    monkeypatch.setattr(winget.subprocess, "run", fake_run)

    assert winget.is_winget_available() is False


def test_get_latest_winget_release_url_picks_msixbundle(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "assets": [
            {"name": "notes.txt", "browser_download_url": "https://example.com/notes.txt"},
            {"name": "Microsoft.DesktopAppInstaller.msixbundle", "browser_download_url": "https://example.com/winget.msixbundle"},
        ]
    }

    def fake_get(url: str, headers: dict[str, str], timeout: int) -> JsonResponse:
        assert url == "https://api.github.com/repos/microsoft/winget-cli/releases/latest"
        assert headers == {"Accept": "application/vnd.github.v3+json"}
        assert timeout == 30
        return JsonResponse(payload=payload, raise_error=False)

    monkeypatch.setattr(winget.requests, "get", fake_get)

    assert winget.get_latest_winget_release_url() == "https://example.com/winget.msixbundle"


def test_download_file_writes_streamed_bytes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    destination = tmp_path / "winget.msixbundle"

    def fake_get(url: str, stream: bool, timeout: int) -> DownloadResponse:
        assert url == "https://example.com/winget.msixbundle"
        assert stream is True
        assert timeout == 60
        return DownloadResponse(chunks=[b"abc", b"", b"def"], raise_error=False)

    monkeypatch.setattr(winget.requests, "get", fake_get)

    assert winget.download_file("https://example.com/winget.msixbundle", destination) is True
    assert destination.read_bytes() == b"abcdef"


def test_install_msix_package_returns_false_on_non_zero_exit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    package_path = tmp_path / "winget.msixbundle"
    package_path.write_text("package", encoding="utf-8")

    def fake_run(command: list[str], text: bool, timeout: int) -> subprocess.CompletedProcess[str]:
        assert command[0:4] == ["powershell.exe", "-ExecutionPolicy", "Bypass", "-Command"]
        assert text is True
        assert timeout == 300
        return subprocess.CompletedProcess(args=command, returncode=1, stderr="boom")

    monkeypatch.setattr(winget.subprocess, "run", fake_run)

    assert winget.install_msix_package(package_path=package_path) is False


def test_main_returns_early_when_winget_already_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(winget, "is_winget_available", lambda: True)
    monkeypatch.setattr(winget, "get_latest_winget_release_url", lambda: (_ for _ in ()).throw(AssertionError("should not fetch releases")))

    assert winget.main(installer_data=_installer_data(), version=None, update=False) is True


def test_main_downloads_installs_and_verifies_missing_winget(monkeypatch: pytest.MonkeyPatch) -> None:
    availability = iter([False, True])
    downloaded_paths: list[Path] = []
    installed_paths: list[Path] = []

    def fake_is_winget_available() -> bool:
        return next(availability)

    def fake_get_latest_release_url() -> str:
        return "https://example.com/latest"

    def fake_download_file(url: str, destination: Path) -> bool:
        assert url == "https://example.com/latest"
        downloaded_paths.append(destination)
        destination.write_bytes(b"package")
        return True

    def fake_install_msix_package(package_path: Path) -> bool:
        installed_paths.append(package_path)
        return True

    monkeypatch.setattr(winget, "is_winget_available", fake_is_winget_available)
    monkeypatch.setattr(winget, "get_latest_winget_release_url", fake_get_latest_release_url)
    monkeypatch.setattr(winget, "download_file", fake_download_file)
    monkeypatch.setattr(winget, "install_msix_package", fake_install_msix_package)

    assert winget.main(installer_data=_installer_data(), version=None, update=False) is True
    assert len(downloaded_paths) == 1
    assert downloaded_paths[0].name == "winget-latest.msixbundle"
    assert installed_paths == downloaded_paths
