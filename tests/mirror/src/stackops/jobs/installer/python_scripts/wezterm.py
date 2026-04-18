from pathlib import Path
import subprocess
from typing import cast

import pytest

import stackops.jobs.installer.linux_scripts as linux_scripts
import stackops.jobs.installer.python_scripts.wezterm as wezterm
from stackops.utils.path_reference import get_path_reference_path
from stackops.utils.schemas.installer.installer_types import InstallerData


def _installer_data() -> InstallerData:
    return cast(InstallerData, {})


def test_linux_script_reference_exists() -> None:
    script_path = get_path_reference_path(module=linux_scripts, path_reference=linux_scripts.WEZTERM_PATH_REFERENCE)

    assert script_path.is_file()
    assert script_path.suffix == ".sh"


@pytest.mark.parametrize(
    ("platform_name", "expected_program"),
    [
        (
            "Windows",
            'winget install --no-upgrade --name "WezTerm" --Id "wez.wezterm" --source winget --accept-package-agreements --accept-source-agreements',
        ),
        ("Darwin", "brew install --cask wezterm"),
    ],
)
def test_non_linux_branches_use_expected_command(monkeypatch: pytest.MonkeyPatch, platform_name: str, expected_program: str) -> None:
    recorded_calls: list[tuple[str, bool, bool, bool]] = []

    def fake_run(program: str, shell: bool, text: bool, check: bool) -> subprocess.CompletedProcess[str]:
        recorded_calls.append((program, shell, text, check))
        return subprocess.CompletedProcess(args=[program], returncode=0, stdout="")

    monkeypatch.setattr(wezterm.platform, "system", lambda: platform_name)
    monkeypatch.setattr(wezterm.subprocess, "run", fake_run)

    wezterm.main(installer_data=_installer_data(), version="latest", update=False)

    assert len(recorded_calls) == 1
    assert recorded_calls[0][0].strip() == expected_program
    assert recorded_calls[0][1:] == (True, True, True)


def test_linux_branch_executes_repo_script(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    script_path = tmp_path / "wezterm.sh"
    script_path.write_text("echo install wezterm", encoding="utf-8")
    recorded_calls: list[tuple[str, bool, bool, bool]] = []

    def fake_get_path_reference_path(*, module: object, path_reference: str) -> Path:
        _ = module, path_reference
        return script_path

    def fake_run(program: str, shell: bool, text: bool, check: bool) -> subprocess.CompletedProcess[str]:
        recorded_calls.append((program, shell, text, check))
        return subprocess.CompletedProcess(args=[program], returncode=0, stdout="")

    monkeypatch.setattr(wezterm.platform, "system", lambda: "Linux")
    monkeypatch.setattr(wezterm, "get_path_reference_path", fake_get_path_reference_path)
    monkeypatch.setattr(wezterm.subprocess, "run", fake_run)

    wezterm.main(installer_data=_installer_data(), version=None, update=False)

    assert recorded_calls == [("echo install wezterm", True, True, True)]


def test_unsupported_platform_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wezterm.platform, "system", lambda: "Plan9")

    with pytest.raises(NotImplementedError, match="Unsupported platform: Plan9"):
        wezterm.main(installer_data=_installer_data(), version=None, update=False)
