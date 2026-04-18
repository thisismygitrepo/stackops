from pathlib import Path
import subprocess
from typing import cast

import pytest

import stackops.jobs.installer.linux_scripts as linux_scripts
import stackops.jobs.installer.python_scripts.nerdfont as nerdfont
import stackops.jobs.installer.python_scripts.nerfont_windows_helper as windows_helper
from stackops.utils.path_reference import get_path_reference_path
from stackops.utils.schemas.installer.installer_types import InstallerData


def _installer_data() -> InstallerData:
    return cast(InstallerData, {})


def test_linux_script_reference_exists() -> None:
    script_path = get_path_reference_path(module=linux_scripts, path_reference=linux_scripts.NERDFONT_PATH_REFERENCE)

    assert script_path.is_file()
    assert script_path.suffix == ".sh"


def test_linux_main_executes_repo_script(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    script_path = tmp_path / "nerdfont.sh"
    script_path.write_text("echo install nerd fonts", encoding="utf-8")
    recorded_calls: list[tuple[str, bool, bool, bool]] = []

    def fake_run(program: str, shell: bool, text: bool, check: bool) -> subprocess.CompletedProcess[str]:
        recorded_calls.append((program, shell, text, check))
        return subprocess.CompletedProcess(args=[program], returncode=0, stdout="")

    def fake_get_path_reference_path(*, module: object, path_reference: str) -> Path:
        _ = module, path_reference
        return script_path

    monkeypatch.setattr(nerdfont.platform, "system", lambda: "Linux")
    monkeypatch.setattr(nerdfont, "get_path_reference_path", fake_get_path_reference_path)
    monkeypatch.setattr(nerdfont.subprocess, "run", fake_run)

    nerdfont.main(installer_data=_installer_data(), version="1.2.3", update=False)

    assert recorded_calls == [("echo install nerd fonts", True, True, True)]


def test_windows_main_wraps_helper_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_install_nerd_fonts() -> None:
        raise ValueError("boom")

    monkeypatch.setattr(nerdfont.platform, "system", lambda: "Windows")
    monkeypatch.setattr(windows_helper, "install_nerd_fonts", fake_install_nerd_fonts)

    with pytest.raises(RuntimeError, match="Windows Nerd Fonts installation failed: boom"):
        nerdfont.main(installer_data=_installer_data(), version=None, update=False)
