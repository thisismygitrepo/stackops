from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_devops import run_script


@pytest.mark.parametrize("platform_name", ["Darwin", "Linux"])
def test_shell_script_default_sources_in_caller(monkeypatch: pytest.MonkeyPatch, platform_name: str) -> None:
    monkeypatch.setattr("platform.system", lambda: platform_name)

    command = run_script._get_shell_script_invoking_file(
        script_path=Path("/tmp/example script.sh"),
        forwarded_args=["--help", "two words"],
        run_in_subprocess=False,
    )

    assert command == "source '/tmp/example script.sh' --help 'two words'"


@pytest.mark.parametrize("platform_name", ["Darwin", "Linux"])
def test_shell_script_subprocess_uses_bash(monkeypatch: pytest.MonkeyPatch, platform_name: str) -> None:
    monkeypatch.setattr("platform.system", lambda: platform_name)

    command = run_script._get_shell_script_invoking_file(
        script_path=Path("/tmp/example script.sh"),
        forwarded_args=["--help", "two words"],
        run_in_subprocess=True,
    )

    assert command == "bash -- '/tmp/example script.sh' --help 'two words'"


def test_powershell_script_subprocess_uses_child_powershell(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("platform.system", lambda: "Windows")

    command = run_script._get_shell_script_invoking_file(
        script_path=Path("C:\\Scripts\\example script.ps1"),
        forwarded_args=["--help", "O'Brien"],
        run_in_subprocess=True,
    )

    assert command == (
        "& ((Get-Process -Id $PID).Path) -NoLogo -NoProfile -ExecutionPolicy Bypass "
        "-File 'C:\\Scripts\\example script.ps1' '--help' 'O''Brien'"
    )
