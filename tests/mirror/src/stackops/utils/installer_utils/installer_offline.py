import io
import platform
from pathlib import Path

import pytest
from rich.console import Console

from stackops.utils.installer_utils import installer_offline
from stackops.utils.installer_utils import installer_offline_constants


def test_export_builds_archive_and_summary(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    install_path = tmp_path.joinpath("bin")
    install_path.mkdir()
    install_path.joinpath("bat").write_text("bat-binary", encoding="utf-8")

    config_root = tmp_path.joinpath("config-root")
    config_root.mkdir()
    config_root.joinpath("settings.toml").write_text("theme=dark", encoding="utf-8")

    monkeypatch.setattr(installer_offline_constants, "BINARY_NAMES", ["bat", "yq"])
    monkeypatch.setattr(installer_offline_constants, "CONFIG_ROOT", config_root)
    monkeypatch.setattr(installer_offline_constants, "LINUX_INSTALL_PATH", str(install_path))
    monkeypatch.setattr(installer_offline_constants, "UV_TOOLS_ROOT", tmp_path.joinpath("uv"))
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(platform, "machine", lambda: "x86_64")

    console_output = io.StringIO()
    report = installer_offline.export(
        options=installer_offline.OfflineInstallerOptions(
            output_root=tmp_path.joinpath("out"),
            include_configs=True,
            include_uv_bundle=False,
            keep_unpacked=True,
        ),
        console=Console(file=console_output, force_terminal=False, color_system=None),
    )

    binary_statuses = {result.binary_name: result.status for result in report.binary_results}
    step_statuses = {result.label: result.status for result in report.step_results}

    assert report.archive_path.is_file()
    assert report.output_dir.is_dir()
    assert report.output_dir.joinpath("binaries", "bat").read_text(encoding="utf-8") == "bat-binary"
    assert report.output_dir.joinpath("configs", "settings.toml").read_text(encoding="utf-8") == "theme=dark"
    assert report.output_dir.joinpath("install.sh").is_file()
    assert binary_statuses == {"bat": "included", "yq": "missing"}
    assert step_statuses["configs"] == "included"
    assert step_statuses["uv bundle"] == "skipped"
    assert step_statuses["install script"] == "included"
    assert step_statuses["archive"] == "included"
    assert "Installer binaries" in console_output.getvalue()
    assert "Build steps" in console_output.getvalue()
