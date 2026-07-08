from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console

from stackops.utils.installer_utils import install_from_url


@pytest.mark.parametrize("package_name", ["tool-1.0.0-r0.apk", "tool-1.0.0-1-x86_64.pkg.tar.zst"])
def test_finalize_install_dispatches_linux_package(package_name: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    package_path = tmp_path.joinpath(package_name)
    package_path.touch()
    version_root = tmp_path.joinpath("versions")
    installed_packages: list[Path] = []
    monkeypatch.setattr(install_from_url, "install_linux_package_file", installed_packages.append)
    monkeypatch.setattr(install_from_url, "INSTALL_VERSION_ROOT", version_root)

    install_from_url._finalize_install(
        repo_name="owner/tool", asset_name=package_path.name, version="1.0.0", extracted_path=package_path, console=Console(file=StringIO())
    )

    assert installed_packages == [package_path]
    assert version_root.joinpath("tool").read_text(encoding="utf-8") == "1.0.0"
