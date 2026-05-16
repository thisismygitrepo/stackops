import io
from pathlib import Path

import pytest
from rich.console import Console

from stackops.utils.installer_utils import install_from_url
from stackops.utils.installer_utils import installer_locator_utils


def test_derive_tool_name_prefers_asset_prefix_over_repo_slug() -> None:
    tool_name = install_from_url._derive_tool_name(
        repo_name="librespeed/speedtest-cli",
        asset_name="librespeed-cli_1.0.13_linux_amd64.tar.gz",
    )

    assert tool_name == "librespeed-cli"


def test_finalize_install_uses_asset_derived_name_for_linux_archive(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    extracted_path = tmp_path.joinpath("downloaded")
    extracted_path.mkdir()
    extracted_path.joinpath("LICENSE").write_text("license", encoding="utf-8")
    executable_path = extracted_path.joinpath("librespeed-cli")
    executable_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    executable_path.chmod(0o755)

    install_root = tmp_path.joinpath("bin")
    install_root.mkdir()
    version_root = tmp_path.joinpath("versions")
    version_root.mkdir()

    monkeypatch.setattr(install_from_url.platform, "system", lambda: "Linux")
    monkeypatch.setattr(installer_locator_utils, "LINUX_INSTALL_PATH", str(install_root))
    monkeypatch.setattr(install_from_url, "INSTALL_VERSION_ROOT", version_root)

    console_output = io.StringIO()
    install_from_url._finalize_install(
        repo_name="librespeed/speedtest-cli",
        asset_name="librespeed-cli_1.0.13_linux_amd64.tar.gz",
        version="v1.0.13",
        extracted_path=extracted_path,
        console=Console(file=console_output, force_terminal=False, color_system=None),
    )

    assert install_root.joinpath("librespeed-cli").is_file()
    assert not install_root.joinpath("speedtest-cli").exists()
    assert not install_root.joinpath("speedtestcli").exists()
    assert version_root.joinpath("librespeed-cli").read_text(encoding="utf-8") == "v1.0.13"


def test_find_move_delete_linux_error_lists_requested_and_available_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    extracted_path = tmp_path.joinpath("downloaded")
    extracted_path.mkdir()
    extracted_path.joinpath("LICENSE").write_text("license", encoding="utf-8")
    extracted_path.joinpath("README.md").write_text("readme", encoding="utf-8")

    install_root = tmp_path.joinpath("bin")
    install_root.mkdir()
    monkeypatch.setattr(installer_locator_utils, "LINUX_INSTALL_PATH", str(install_root))

    with pytest.raises(IndexError) as error_info:
        installer_locator_utils.find_move_delete_linux(
            downloaded=extracted_path,
            tool_name="missing-tool",
            delete=False,
            rename_to=None,
        )

    error_text = str(error_info.value)
    assert "Requested tool name: missing-tool" in error_text
    assert "Search terms tried:" in error_text
    assert "Executable files found:" in error_text
    assert "All files found:" in error_text
    assert "LICENSE" in error_text
    assert "README.md" in error_text


def test_find_move_delete_linux_rejects_source_tree_false_positive(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    extracted_path = tmp_path.joinpath("downloaded", "iperf-3.21", "src")
    extracted_path.mkdir(parents=True)
    extracted_path.joinpath("iperf.h").write_text("/* header */", encoding="utf-8")
    extracted_path.joinpath("main.c").write_text("int main(void) { return 0; }", encoding="utf-8")

    contrib_path = extracted_path.parent.joinpath("contrib")
    contrib_path.mkdir()
    contrib_script = contrib_path.joinpath("iperf3_to_gnuplot.py")
    contrib_script.write_text("#!/usr/bin/env python3\nprint('hi')\n", encoding="utf-8")
    contrib_script.chmod(0o755)

    configure_path = extracted_path.parent.joinpath("configure")
    configure_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    configure_path.chmod(0o755)

    install_root = tmp_path.joinpath("bin")
    install_root.mkdir()
    monkeypatch.setattr(installer_locator_utils, "LINUX_INSTALL_PATH", str(install_root))

    with pytest.raises(IndexError) as error_info:
        installer_locator_utils.find_move_delete_linux(
            downloaded=tmp_path.joinpath("downloaded"),
            tool_name="iperf",
            delete=False,
            rename_to=None,
        )

    error_text = str(error_info.value)
    assert "iperf.h" in error_text
    assert "configure" in error_text
    assert "iperf3_to_gnuplot.py" in error_text
    assert not install_root.joinpath("iperf").exists()
