from pathlib import Path
from typing import cast

import pytest

import machineconfig.jobs.installer.python_scripts.poppler as poppler
from machineconfig.utils.path_extended import PathExtended
from machineconfig.utils.schemas.installer.installer_types import InstallerData


def _installer_data() -> InstallerData:
    return cast(InstallerData, {})


def test_select_extracted_root_prefers_single_child_directory(tmp_path: Path) -> None:
    extracted_path = PathExtended(str(tmp_path / "poppler"))
    extracted_path.mkdir()
    nested_dir = PathExtended(str(extracted_path / "release"))
    nested_dir.mkdir()

    selected_path = poppler._select_extracted_root(extracted_path=extracted_path)

    assert selected_path == nested_dir


def test_main_copies_download_into_user_poppler_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home_dir = PathExtended(str(tmp_path / "home"))
    home_dir.mkdir()
    extracted_path = PathExtended(str(tmp_path / "downloaded"))
    extracted_path.mkdir()
    nested_dir = PathExtended(str(extracted_path / "Release-24.08.0"))
    nested_dir.mkdir()
    bin_dir = PathExtended(str(nested_dir / "bin"))
    bin_dir.mkdir()
    (bin_dir / "pdftotext.exe").write_text("payload", encoding="utf-8")

    target_root = PathExtended(str(home_dir / ".local" / "share" / "poppler"))
    target_root.mkdir(parents=True, exist_ok=True)
    (target_root / "old.txt").write_text("stale", encoding="utf-8")

    class FakeInstaller:
        def __init__(self, installer_data: InstallerData) -> None:
            _ = installer_data

        def binary_download(self, version: str | None) -> tuple[PathExtended, str]:
            assert version == "24.08.0"
            return extracted_path, "24.08.0"

    def fake_home(cls: type[PathExtended]) -> PathExtended:
        _ = cls
        return home_dir

    monkeypatch.setattr(poppler.platform, "system", lambda: "Windows")
    monkeypatch.setattr(poppler, "Installer", FakeInstaller)
    monkeypatch.setattr(poppler.PathExtended, "home", classmethod(fake_home))

    poppler.main(installer_data=_installer_data(), version="24.08.0", update=False)

    assert (target_root / "bin" / "pdftotext.exe").read_text(encoding="utf-8") == "payload"
    assert not (target_root / "old.txt").exists()
    assert not extracted_path.exists()


def test_main_rejects_file_download_on_windows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home_dir = PathExtended(str(tmp_path / "home"))
    home_dir.mkdir()
    extracted_file = PathExtended(str(tmp_path / "poppler.zip"))
    extracted_file.write_text("not extracted", encoding="utf-8")

    class FakeInstaller:
        def __init__(self, installer_data: InstallerData) -> None:
            _ = installer_data

        def binary_download(self, version: str | None) -> tuple[PathExtended, str]:
            _ = version
            return extracted_file, "24.08.0"

    def fake_home(cls: type[PathExtended]) -> PathExtended:
        _ = cls
        return home_dir

    monkeypatch.setattr(poppler.platform, "system", lambda: "Windows")
    monkeypatch.setattr(poppler, "Installer", FakeInstaller)
    monkeypatch.setattr(poppler.PathExtended, "home", classmethod(fake_home))

    with pytest.raises(FileNotFoundError, match="Expected extracted directory, got file"):
        poppler.main(installer_data=_installer_data(), version=None, update=False)
