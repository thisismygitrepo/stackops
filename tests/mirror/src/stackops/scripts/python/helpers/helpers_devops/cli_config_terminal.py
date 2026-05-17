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


def test_pwsh_theme_uses_pwsh_outside_windows(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    script_path = tmp_path / "choose-pwsh-theme.ps1"
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

    result = CliRunner().invoke(cli_config_terminal.get_app(), ["pwsh-theme"])

    assert result.exit_code == 0
    assert recorded_commands == [["pwsh", "-File", str(script_path)]]


def test_pwsh_theme_requires_pwsh_outside_windows(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    script_path = tmp_path / "choose-pwsh-theme.ps1"
    recorded_commands: list[list[str]] = []

    def fake_get_path_reference_path(*, module: object, path_reference: object) -> Path:
        del module, path_reference
        return script_path

    def fake_run(command: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        del check
        recorded_commands.append(command)
        raise FileNotFoundError(command[0])

    monkeypatch.setattr(cli_config_terminal.platform, "system", lambda: "Linux")
    monkeypatch.setattr(cli_config_terminal, "get_path_reference_path", fake_get_path_reference_path)
    monkeypatch.setattr(cli_config_terminal.subprocess, "run", fake_run)

    result = CliRunner().invoke(cli_config_terminal.get_app(), ["pwsh-theme"])

    assert result.exit_code == 1
    assert result.stderr == "Error: pwsh is required to select a powershell prompt theme.\n"
    assert recorded_commands == [["pwsh", "-File", str(script_path)]]


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


def test_starship_theme_falls_back_to_powershell_on_windows(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    script_path = tmp_path / "choose-starship-theme.ps1"
    recorded_commands: list[list[str]] = []

    def fake_get_path_reference_path(*, module: object, path_reference: object) -> Path:
        del module, path_reference
        return script_path

    def fake_run(command: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        assert check is True
        recorded_commands.append(command)
        if command[0] == "pwsh":
            raise FileNotFoundError(command[0])
        return subprocess.CompletedProcess(args=command, returncode=0)

    monkeypatch.setattr(cli_config_terminal.platform, "system", lambda: "Windows")
    monkeypatch.setattr(cli_config_terminal, "get_path_reference_path", fake_get_path_reference_path)
    monkeypatch.setattr(cli_config_terminal.subprocess, "run", fake_run)

    result = CliRunner().invoke(cli_config_terminal.get_app(), ["starship-theme"])

    assert result.exit_code == 0
    assert recorded_commands == [
        ["pwsh", "-File", str(script_path)],
        ["powershell", "-File", str(script_path)],
    ]


def test_starship_theme_requires_powershell_runtime_on_windows(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    script_path = tmp_path / "choose-starship-theme.ps1"
    recorded_commands: list[list[str]] = []

    def fake_get_path_reference_path(*, module: object, path_reference: object) -> Path:
        del module, path_reference
        return script_path

    def fake_run(command: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        assert check is True
        recorded_commands.append(command)
        raise FileNotFoundError(command[0])

    monkeypatch.setattr(cli_config_terminal.platform, "system", lambda: "Windows")
    monkeypatch.setattr(cli_config_terminal, "get_path_reference_path", fake_get_path_reference_path)
    monkeypatch.setattr(cli_config_terminal.subprocess, "run", fake_run)

    result = CliRunner().invoke(cli_config_terminal.get_app(), ["starship-theme"])

    assert result.exit_code == 1
    assert result.stderr == "Error: pwsh or powershell is required to select a starship prompt theme.\n"
    assert recorded_commands == [
        ["pwsh", "-File", str(script_path)],
        ["powershell", "-File", str(script_path)],
    ]


def test_starship_theme_returns_script_exit_code(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    script_path = tmp_path / "choose-starship-theme.sh"

    def fake_get_path_reference_path(*, module: object, path_reference: object) -> Path:
        del module, path_reference
        return script_path

    def fake_run(command: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        assert check is True
        raise subprocess.CalledProcessError(returncode=23, cmd=command)

    monkeypatch.setattr(cli_config_terminal.platform, "system", lambda: "Linux")
    monkeypatch.setattr(cli_config_terminal, "get_path_reference_path", fake_get_path_reference_path)
    monkeypatch.setattr(cli_config_terminal.subprocess, "run", fake_run)

    result = CliRunner().invoke(cli_config_terminal.get_app(), ["starship-theme"])

    assert result.exit_code == 23


def test_windows_terminal_theme_falls_back_to_powershell(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    script_path = tmp_path / "choose-windows-terminal-theme.ps1"
    recorded_commands: list[list[str]] = []

    def fake_get_path_reference_path(*, module: object, path_reference: object) -> Path:
        del module, path_reference
        return script_path

    def fake_run(command: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        assert check is True
        recorded_commands.append(command)
        if command[0] == "pwsh":
            raise FileNotFoundError(command[0])
        return subprocess.CompletedProcess(args=command, returncode=0)

    monkeypatch.setattr(cli_config_terminal.platform, "system", lambda: "Windows")
    monkeypatch.setattr(cli_config_terminal, "get_path_reference_path", fake_get_path_reference_path)
    monkeypatch.setattr(cli_config_terminal.subprocess, "run", fake_run)

    result = CliRunner().invoke(cli_config_terminal.get_app(), ["windows-terminal-theme"])

    assert result.exit_code == 0
    assert recorded_commands == [
        ["pwsh", "-File", str(script_path)],
        ["powershell", "-File", str(script_path)],
    ]


def test_windows_terminal_theme_requires_powershell_runtime(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    script_path = tmp_path / "choose-windows-terminal-theme.ps1"
    recorded_commands: list[list[str]] = []

    def fake_get_path_reference_path(*, module: object, path_reference: object) -> Path:
        del module, path_reference
        return script_path

    def fake_run(command: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        assert check is True
        recorded_commands.append(command)
        raise FileNotFoundError(command[0])

    monkeypatch.setattr(cli_config_terminal.platform, "system", lambda: "Windows")
    monkeypatch.setattr(cli_config_terminal, "get_path_reference_path", fake_get_path_reference_path)
    monkeypatch.setattr(cli_config_terminal.subprocess, "run", fake_run)

    result = CliRunner().invoke(cli_config_terminal.get_app(), ["windows-terminal-theme"])

    assert result.exit_code == 1
    assert result.stderr == "Error: pwsh or powershell is required to select a Windows Terminal color scheme.\n"
    assert recorded_commands == [
        ["pwsh", "-File", str(script_path)],
        ["powershell", "-File", str(script_path)],
    ]
