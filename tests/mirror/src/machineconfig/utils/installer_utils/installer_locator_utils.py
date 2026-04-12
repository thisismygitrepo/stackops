from __future__ import annotations

from pathlib import Path
import stat

import pytest

from machineconfig.utils.installer_utils import installer_locator_utils as locator
from machineconfig.utils.path_extended import PathExtended


def test_find_move_delete_linux_moves_largest_file_and_cleans_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    download_root = PathExtended(tmp_path / "download")
    install_root = tmp_path / "install-bin"
    download_root.mkdir()
    (download_root / "small-tool").write_text("small", encoding="utf-8")
    (download_root / "large-tool").write_text("large" * 20, encoding="utf-8")

    monkeypatch.setattr(locator, "LINUX_INSTALL_PATH", str(install_root))

    installed_path = locator.find_move_delete_linux(
        downloaded=download_root,
        tool_name=None,
        delete=True,
        rename_to="tool",
    )

    installed = Path(installed_path)
    assert installed == install_root / "tool"
    assert installed.read_text(encoding="utf-8") == "large" * 20
    assert stat.S_IMODE(installed.stat().st_mode) & 0o111 != 0
    assert not download_root.exists()


def test_check_if_installed_already_updates_outdated_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    version_root = PathExtended(tmp_path / "versions")
    cache_path = version_root / "demo-tool"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text("1.0.0\n", encoding="utf-8")

    monkeypatch.setattr(locator, "INSTALL_VERSION_ROOT", version_root)

    verdict, current_version, requested_version = locator.check_if_installed_already(
        exe_name="demo-tool",
        version="2.0.0",
        use_cache=True,
    )

    assert verdict == "❌ Outdated"
    assert current_version == "1.0.0"
    assert requested_version == "2.0.0"
    assert cache_path.read_text(encoding="utf-8") == "2.0.0"
