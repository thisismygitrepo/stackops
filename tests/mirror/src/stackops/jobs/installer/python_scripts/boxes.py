

from pathlib import Path

import pytest

from stackops.jobs.installer.python_scripts import boxes as boxes_module
from stackops.utils.schemas.installer.installer_types import InstallerData


class _FakeConsole:
    def print(self, *_args: object, **_kwargs: object) -> None:
        return None


def _build_installer_data() -> InstallerData:
    return {
        "appName": "ignored",
        "license": "MIT",
        "doc": "ignored",
        "repoURL": "https://example.invalid",
        "fileNamePattern": {"amd64": {"windows": None, "linux": None, "darwin": None}, "arm64": {"windows": None, "linux": None, "darwin": None}},
    }


def test_main_moves_boxes_files_into_windows_install_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    download_dir = tmp_path / "download"
    nested_dir = download_dir / "nested"
    nested_dir.mkdir(parents=True)
    nested_dir.joinpath("boxes.exe").write_text("exe", encoding="utf-8")
    nested_dir.joinpath("boxes.cfg").write_text("cfg", encoding="utf-8")
    nested_dir.joinpath("ignore.txt").write_text("ignore", encoding="utf-8")
    install_dir = tmp_path / "install"
    install_dir.mkdir()
    captured_versions: list[str | None] = []
    captured_installer_data: list[InstallerData] = []

    class _FakeInstaller:
        def __init__(self, installer_data: InstallerData) -> None:
            captured_installer_data.append(installer_data)

        def binary_download(self, version: str | None) -> tuple[Path, str]:
            captured_versions.append(version)
            return download_dir, "2.0.0"

    monkeypatch.setattr(boxes_module, "Console", _FakeConsole)
    monkeypatch.setattr(boxes_module, "Installer", _FakeInstaller)
    monkeypatch.setattr(boxes_module, "WINDOWS_INSTALL_PATH", str(install_dir))

    boxes_module.main(_build_installer_data(), version="2.0.0", update=False)

    assert captured_installer_data == [boxes_module.installer_data_modified]
    assert captured_versions == ["2.0.0"]
    assert install_dir.joinpath("boxes.exe").read_text(encoding="utf-8") == "exe"
    assert install_dir.joinpath("boxes.cfg").read_text(encoding="utf-8") == "cfg"
    assert not nested_dir.joinpath("boxes.exe").exists()
    assert not nested_dir.joinpath("boxes.cfg").exists()
    assert nested_dir.joinpath("ignore.txt").read_text(encoding="utf-8") == "ignore"
