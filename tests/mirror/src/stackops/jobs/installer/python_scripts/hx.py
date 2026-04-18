from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, cast

import pytest

import stackops.jobs.installer.python_scripts.hx as hx_script
from stackops.utils.schemas.installer.installer_types import InstallerData


DUMMY_INSTALLER_DATA = cast(InstallerData, {})


@dataclass
class DownloadedArchive:
    root: Path
    deleted: bool = False

    @property
    def name(self) -> str:
        return self.root.name

    def rglob(self, pattern: str) -> list[Path]:
        return list(self.root.rglob(pattern))

    def delete(self, sure: bool) -> None:
        _ = sure
        self.deleted = True


class InstallerSpy:
    archive: ClassVar[DownloadedArchive]
    versions: ClassVar[list[str | None]] = []

    def __init__(self, installer_data: InstallerData) -> None:
        self.installer_data = installer_data

    def binary_download(self, version: str | None) -> tuple[DownloadedArchive, str]:
        type(self).versions.append(version)
        return (type(self).archive, "24.03.0")


def test_main_raises_when_download_missing_hx_executable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    download_root = tmp_path / "helix-download"
    download_root.mkdir()
    (download_root / "README.txt").write_text("missing executable", encoding="utf-8")

    InstallerSpy.archive = DownloadedArchive(root=download_root)
    InstallerSpy.versions.clear()

    monkeypatch.setattr(hx_script, "Installer", InstallerSpy)
    monkeypatch.setattr(hx_script.platform, "system", lambda: "Linux")

    with pytest.raises(FileNotFoundError, match="Could not find 'hx' executable"):
        hx_script.main(installer_data=DUMMY_INSTALLER_DATA, version=None, update=False)

    assert InstallerSpy.versions == [None]
