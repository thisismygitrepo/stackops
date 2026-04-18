from pathlib import Path
import subprocess

import pytest
import typer

import stackops.profile.create_shell_profile as create_shell_profile_module
import stackops.scripts.python.helpers.helpers_devops.cli_config_terminal as cli_config_terminal_module


def test_configure_shell_profile_dispatches_to_requested_builder(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_create_default_shell_profile() -> None:
        calls.append("default")

    def fake_create_nu_shell_profile() -> None:
        calls.append("nushell")

    monkeypatch.setattr(create_shell_profile_module, "create_default_shell_profile", fake_create_default_shell_profile)
    monkeypatch.setattr(create_shell_profile_module, "create_nu_shell_profile", fake_create_nu_shell_profile)

    cli_config_terminal_module.configure_shell_profile(which="n")
    cli_config_terminal_module.configure_shell_profile(which="default")

    assert calls == ["nushell", "default"]


def test_starship_theme_on_windows_falls_back_to_powershell(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    script_path = tmp_path / "theme.ps1"
    script_path.write_text("Write-Host test", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run(args: list[str], check: bool) -> subprocess.CompletedProcess[str]:
        _ = check
        calls.append(args)
        if args[0] == "pwsh":
            raise FileNotFoundError("pwsh not found")
        return subprocess.CompletedProcess(args=args, returncode=0)

    monkeypatch.setattr(cli_config_terminal_module.platform, "system", lambda: "Windows")
    monkeypatch.setattr(cli_config_terminal_module, "get_path_reference_path", lambda module, path_reference: script_path)
    monkeypatch.setattr(cli_config_terminal_module.subprocess, "run", fake_run)

    cli_config_terminal_module.starship_theme()

    assert calls == [["pwsh", "-File", str(script_path)], ["powershell", "-File", str(script_path)]]


def test_configure_ghostty_theme_adds_include_once_and_opens_preview(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_home = tmp_path / "config-home"
    config_path = config_home / "ghostty" / "config"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("font-size = 12\n", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run(args: list[str], check: bool) -> subprocess.CompletedProcess[str]:
        _ = check
        calls.append(args)
        return subprocess.CompletedProcess(args=args, returncode=0)

    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.setattr(cli_config_terminal_module.subprocess, "run", fake_run)

    cli_config_terminal_module.configure_ghostty_theme()
    cli_config_terminal_module.configure_ghostty_theme()

    content = config_path.read_text(encoding="utf-8")
    assert content.count("config-file = ?auto/theme.ghostty") == 1
    assert calls == [["ghostty", "+list-themes"], ["ghostty", "+list-themes"]]


def test_configure_windows_terminal_theme_rejects_non_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_config_terminal_module.platform, "system", lambda: "Linux")

    with pytest.raises(typer.Exit) as exit_info:
        cli_config_terminal_module.configure_windows_terminal_theme()

    assert exit_info.value.exit_code == 1
