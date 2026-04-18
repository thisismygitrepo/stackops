from __future__ import annotations

from pathlib import PureWindowsPath

import pytest

from stackops.jobs.installer.python_scripts import bypass_paywall as bypass_paywall_module
from stackops.utils.schemas.installer.installer_types import InstallerData


class _FakeConsole:
    def print(self, *_args: object, **_kwargs: object) -> None:
        return None


class _FakePathExtended:
    downloaded_urls: list[str] = []
    unzip_calls: list[tuple[str, bool]] = []

    def __init__(self, raw_path: str) -> None:
        self.raw_path = raw_path

    def download(self) -> "_FakePathExtended":
        self.downloaded_urls.append(self.raw_path)
        return self

    def unzip(self, folder: str, content: bool) -> "_FakePathExtended":
        self.unzip_calls.append((folder, content))
        return self

    def joinpath(self, name: str) -> "_FakePathExtended":
        return _FakePathExtended(str(PureWindowsPath(self.raw_path).joinpath(name)))

    def __str__(self) -> str:
        return self.raw_path



def _build_installer_data() -> InstallerData:
    return {
        "appName": "bypass-paywalls-chrome",
        "license": "MIT",
        "doc": "Extension",
        "repoURL": "https://github.com/iamadamdev/bypass-paywalls-chrome",
        "fileNamePattern": {
            "amd64": {"windows": None, "linux": None, "darwin": None},
            "arm64": {"windows": None, "linux": None, "darwin": None},
        },
    }



def test_main_downloads_archive_and_unzips_into_c_drive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bypass_paywall_module, "PathExtended", _FakePathExtended)
    monkeypatch.setattr(bypass_paywall_module, "Console", _FakeConsole)
    _FakePathExtended.downloaded_urls.clear()
    _FakePathExtended.unzip_calls.clear()

    result = bypass_paywall_module.main(
        _build_installer_data(),
        version=None,
        update=False,
    )

    assert _FakePathExtended.downloaded_urls == [
        "https://github.com/iamadamdev/bypass-paywalls-chrome/archive/master.zip"
    ]
    assert _FakePathExtended.unzip_calls == [("C:\\\\", True)]
    assert result == ""
