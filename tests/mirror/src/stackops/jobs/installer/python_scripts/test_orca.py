from pathlib import Path

import pytest

from stackops.jobs.installer.python_scripts.orca import _find_bundled_windows_orca_cli, _write_windows_orca_wrapper


def test_windows_wrapper_runs_the_bundled_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    gui_executable = tmp_path.joinpath("Orca", "Orca.exe")
    cli_executable = gui_executable.parent.joinpath("resources", "bin", "orca.exe")
    cli_executable.parent.mkdir(parents=True)
    gui_executable.touch()
    cli_executable.touch()

    resolved_cli = _find_bundled_windows_orca_cli(gui_executable=gui_executable)
    monkeypatch.setattr("stackops.jobs.installer.python_scripts.orca.WINDOWS_INSTALL_PATH", str(tmp_path.joinpath("WindowsApps")))
    wrapper_path = _write_windows_orca_wrapper(target_executable=resolved_cli)

    assert resolved_cli == cli_executable
    assert (
        wrapper_path.read_text(encoding="utf-8")
        == f"""@echo off
"{cli_executable}" %*
"""
    )
