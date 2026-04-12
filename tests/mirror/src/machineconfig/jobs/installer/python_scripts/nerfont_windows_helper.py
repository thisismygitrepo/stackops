from pathlib import Path
import subprocess
from typing import cast

import pytest

import machineconfig.jobs.installer.powershell_scripts as powershell_scripts
import machineconfig.jobs.installer.python_scripts.nerfont_windows_helper as helper
from machineconfig.utils.path_extended import PathExtended
from machineconfig.utils.path_reference import get_path_reference_path
from machineconfig.utils.schemas.installer.installer_types import InstallerData


def _installer_data() -> InstallerData:
    return cast(InstallerData, {})


def test_install_fonts_script_reference_exists() -> None:
    script_path = get_path_reference_path(module=powershell_scripts, path_reference=powershell_scripts.INSTALL_FONTS_PATH_REFERENCE)

    assert script_path.is_file()
    assert script_path.suffix == ".ps1"


def test_missing_required_fonts_normalizes_names() -> None:
    missing = helper._missing_required_fonts(["Cascadia_Code_NF", "Other Font"])

    assert missing == ["Caskaydia Cove Nerd Font family"]


def test_install_nerd_fonts_skips_download_when_required_fonts_exist(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingInstaller:
        def __init__(self, installer_data: InstallerData) -> None:
            _ = installer_data
            raise AssertionError("download should be skipped")

    monkeypatch.setattr(helper, "_list_installed_fonts", lambda: ["CascadiaCode", "CaskaydiaCove"])
    monkeypatch.setattr(helper, "Installer", FailingInstaller)

    helper.install_nerd_fonts()


def test_install_nerd_fonts_writes_ascii_script_and_cleans_up(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    downloaded_dir = PathExtended(str(tmp_path / "downloaded"))
    downloaded_dir.mkdir()
    (downloaded_dir / "CascadiaCode-Regular.ttf").write_text("font", encoding="utf-8")
    (downloaded_dir / "Symbols.otf").write_text("font", encoding="utf-8")
    (downloaded_dir / "SomeWindowsNote.txt").write_text("trash", encoding="utf-8")
    (downloaded_dir / "readme.md").write_text("trash", encoding="utf-8")
    (downloaded_dir / "LICENSE.txt").write_text("trash", encoding="utf-8")

    template_path = tmp_path / "install_fonts.ps1"
    template_path.write_text("Write-Host 'café'\nSet-Location .\\fonts-to-be-installed\n", encoding="utf-8")

    expected_script_path = tmp_path / "tmp_results" / "tmp_files" / "fixed-script.ps1"
    captured_commands: list[str] = []
    captured_script_contents: list[str] = []

    class FakeInstaller:
        def __init__(self, installer_data: InstallerData) -> None:
            _ = installer_data

        def binary_download(self, version: str | None) -> tuple[PathExtended, str]:
            assert version is None
            return downloaded_dir, "1.0.0"

    def fake_get_path_reference_path(*, module: object, path_reference: str) -> Path:
        _ = module, path_reference
        return template_path

    def fake_run(command: str, check: bool) -> subprocess.CompletedProcess[str]:
        assert check is True
        captured_commands.append(command)
        captured_script_contents.append(expected_script_path.read_text(encoding="utf-8"))
        return subprocess.CompletedProcess(args=[command], returncode=0, stdout="")

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(helper, "_list_installed_fonts", lambda: [])
    monkeypatch.setattr(helper, "Installer", FakeInstaller)
    monkeypatch.setattr(helper, "get_path_reference_path", fake_get_path_reference_path)
    monkeypatch.setattr(helper, "randstr", lambda: "fixed-script")
    monkeypatch.setattr(helper.subprocess, "run", fake_run)

    helper.install_nerd_fonts()

    assert captured_commands == [f"powershell.exe -executionpolicy Bypass -nologo -noninteractive -File {expected_script_path}"]
    assert len(captured_script_contents) == 1
    assert captured_script_contents[0].isascii()
    assert str(downloaded_dir) in captured_script_contents[0]
    assert "café" not in captured_script_contents[0]
    assert not downloaded_dir.exists()
    assert not expected_script_path.exists()
