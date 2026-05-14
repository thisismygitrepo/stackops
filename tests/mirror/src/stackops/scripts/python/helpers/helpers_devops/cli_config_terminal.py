from pathlib import Path
import subprocess

import pytest
from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_devops import cli_config_terminal


def test_starship_theme_uses_bash_outside_windows(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    script_path = tmp_path / "choose-starship-theme.sh"
    recorded_commands: list[list[str]] = []

    def fake_get_path_reference_path(*, module: object, path_reference: object) -> Path:
        del module, path_reference
        return script_path

    def fake_run(command: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        assert check is True
        recorded_commands.append(command)
        return subprocess.CompletedProcess(args=command, returncode=0)

    monkeypatch.setattr(cli_config_terminal.platform, "system", lambda: "Linux")
    monkeypatch.setattr(cli_config_terminal, "get_path_reference_path", fake_get_path_reference_path)
    monkeypatch.setattr(cli_config_terminal.subprocess, "run", fake_run)

    result = CliRunner().invoke(cli_config_terminal.get_app(), ["starship-theme"])

    assert result.exit_code == 0
    assert recorded_commands == [["bash", str(script_path)]]


def test_starship_theme_uses_pwsh_on_windows(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    script_path = tmp_path / "choose-starship-theme.ps1"
    recorded_commands: list[list[str]] = []

    def fake_get_path_reference_path(*, module: object, path_reference: object) -> Path:
        del module, path_reference
        return script_path

    def fake_run(command: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        assert check is True
        recorded_commands.append(command)
        return subprocess.CompletedProcess(args=command, returncode=0)

    monkeypatch.setattr(cli_config_terminal.platform, "system", lambda: "Windows")
    monkeypatch.setattr(cli_config_terminal, "get_path_reference_path", fake_get_path_reference_path)
    monkeypatch.setattr(cli_config_terminal.subprocess, "run", fake_run)

    result = CliRunner().invoke(cli_config_terminal.get_app(), ["starship-theme"])

    assert result.exit_code == 0
    assert recorded_commands == [["pwsh", "-File", str(script_path)]]


def test_starship_theme_requires_pwsh_on_windows(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    script_path = tmp_path / "choose-starship-theme.ps1"
    recorded_commands: list[list[str]] = []

    def fake_get_path_reference_path(*, module: object, path_reference: object) -> Path:
        del module, path_reference
        return script_path

    def fake_run(command: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        del check
        recorded_commands.append(command)
        raise FileNotFoundError(command[0])

    monkeypatch.setattr(cli_config_terminal.platform, "system", lambda: "Windows")
    monkeypatch.setattr(cli_config_terminal, "get_path_reference_path", fake_get_path_reference_path)
    monkeypatch.setattr(cli_config_terminal.subprocess, "run", fake_run)

    result = CliRunner().invoke(cli_config_terminal.get_app(), ["starship-theme"])

    assert result.exit_code == 1
    assert result.stderr == "Error: pwsh is required to select a starship prompt theme.\n"
    assert recorded_commands == [["pwsh", "-File", str(script_path)]]
