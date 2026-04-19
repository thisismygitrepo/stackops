

from pathlib import Path
import platform
import zipfile

import pytest

from stackops.utils.installer_utils import installer_offline as offline
import stackops.utils.source_of_truth as source_of_truth


def test_uv_helper_functions_parse_python_and_filter_links(tmp_path: Path) -> None:
    tool_root = tmp_path / "tools" / offline.UV_TOOL_NAME
    install_path = tmp_path / "install"
    python_root = tmp_path / "python" / "cpython-3.14"

    (tool_root / "bin").mkdir(parents=True)
    install_path.mkdir()
    (python_root / "bin").mkdir(parents=True)
    (tool_root / "pyvenv.cfg").write_text(
        f"home = {python_root / 'bin'}\n",
        encoding="utf-8",
    )
    (tool_root / "bin" / "stackops").write_text(
        "#!/usr/bin/env sh\n",
        encoding="utf-8",
    )
    (tool_root / "bin" / "python").symlink_to(python_root / "bin" / "python3.14")
    (install_path / "stackops").symlink_to(tool_root / "bin" / "stackops")
    outside = tmp_path / "outside"
    outside.write_text("x", encoding="utf-8")
    (install_path / "outside").symlink_to(outside)

    assert offline._read_uv_python_home(tool_root) == python_root / "bin"
    assert offline._read_uv_python_bin_name(tool_root) == "python3.14"
    assert offline._collect_uv_tool_links(
        install_path=install_path,
        tool_root=tool_root,
    ) == ["stackops"]


def test_export_creates_linux_archive_with_uv_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_home = tmp_path / "home"
    install_path = tmp_home / ".local" / "bin"
    config_root = tmp_home / "config-root"
    uv_root = tmp_home / ".local" / "share" / "uv"
    tool_root = uv_root / "tools" / offline.UV_TOOL_NAME
    python_root = uv_root / "python" / "cpython-3.14"

    install_path.mkdir(parents=True)
    config_root.mkdir(parents=True)
    (tool_root / "bin").mkdir(parents=True)
    (python_root / "bin").mkdir(parents=True)

    (install_path / "bat").write_text("binary", encoding="utf-8")
    (config_root / "settings.toml").write_text("enabled = true\n", encoding="utf-8")
    (tool_root / "bin" / "stackops").write_text(
        "#!/usr/bin/env python3\n",
        encoding="utf-8",
    )
    (python_root / "bin" / "python3.14").write_text("python", encoding="utf-8")
    (tool_root / "pyvenv.cfg").write_text(
        f"home = {python_root / 'bin'}\n",
        encoding="utf-8",
    )
    (tool_root / "bin" / "python").symlink_to(python_root / "bin" / "python3.14")
    (install_path / "stackops").symlink_to(tool_root / "bin" / "stackops")

    monkeypatch.setattr(Path, "home", lambda: tmp_home)
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(offline, "BINARIES", ["bat"])
    monkeypatch.setattr(offline, "UV_TOOL_BINARIES", ["stackops"])
    monkeypatch.setattr(offline, "UV_TOOLS_ROOT", uv_root / "tools")
    monkeypatch.setattr(source_of_truth, "CONFIG_ROOT", config_root)
    monkeypatch.setattr(source_of_truth, "LINUX_INSTALL_PATH", str(install_path))
    monkeypatch.setattr(source_of_truth, "WINDOWS_INSTALL_PATH", str(tmp_home / "win"))

    offline.export()

    archive_path = tmp_home / "tmp_results" / "installer_offline-linux-x86_64.zip"
    build_root = tmp_home / "tmp_results" / "installer_offline-linux-x86_64"

    assert archive_path.is_file()
    assert not build_root.exists()

    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())

    assert "install.sh" in names
    assert "binaries/bat" in names
    assert "configs/settings.toml" in names
    assert "uv_bundle/uv_manifest.env" in names
    assert "uv_bundle/uv_links.txt" in names
    assert "uv_bundle/tools/stackops/pyvenv.cfg" in names
    assert "uv_bundle/python/cpython-3.14/bin/python3.14" in names
