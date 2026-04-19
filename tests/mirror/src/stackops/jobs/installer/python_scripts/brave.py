

from pathlib import Path

import pytest

import stackops.utils.code as code_module
from stackops.jobs.installer.python_scripts import brave as brave_module
from stackops.utils.schemas.installer.installer_types import InstallerData


class _FakeConsole:
    def print(self, *_args: object, **_kwargs: object) -> None:
        return None


def _build_installer_data() -> InstallerData:
    return {
        "appName": "Brave",
        "license": "MPL",
        "doc": "Browser",
        "repoURL": "CMD",
        "fileNamePattern": {"amd64": {"windows": None, "linux": None, "darwin": None}, "arm64": {"windows": None, "linux": None, "darwin": None}},
    }


def test_main_reads_linux_script_and_runs_shell_helper(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    script_path = tmp_path / "brave.sh"
    script_path.write_text("echo brave-linux\n", encoding="utf-8")
    printed_scripts: list[tuple[str, str, str]] = []
    executed_scripts: list[tuple[str, bool, bool]] = []

    def fake_print_code(code: str, lexer: str, desc: str) -> None:
        printed_scripts.append((code, lexer, desc))

    def fake_run_shell_script(script: str, display_script: bool, clean_env: bool) -> None:
        executed_scripts.append((script, display_script, clean_env))

    monkeypatch.setattr(brave_module, "Console", _FakeConsole)
    monkeypatch.setattr(brave_module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(brave_module, "get_path_reference_path", lambda module, path_reference: script_path)
    monkeypatch.setattr(code_module, "print_code", fake_print_code)
    monkeypatch.setattr(code_module, "run_shell_script", fake_run_shell_script)

    brave_module.main(_build_installer_data(), version="1.2.3", update=False)

    assert printed_scripts == [("echo brave-linux\n", "shell", "Installation Script Preview")]
    assert executed_scripts == [("echo brave-linux\n", True, False)]


def test_main_uses_brew_command_for_darwin(monkeypatch: pytest.MonkeyPatch) -> None:
    printed_scripts: list[tuple[str, str, str]] = []
    executed_scripts: list[tuple[str, bool, bool]] = []

    def fake_print_code(code: str, lexer: str, desc: str) -> None:
        printed_scripts.append((code, lexer, desc))

    def fake_run_shell_script(script: str, display_script: bool, clean_env: bool) -> None:
        executed_scripts.append((script, display_script, clean_env))

    monkeypatch.setattr(brave_module, "Console", _FakeConsole)
    monkeypatch.setattr(brave_module.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(code_module, "print_code", fake_print_code)
    monkeypatch.setattr(code_module, "run_shell_script", fake_run_shell_script)

    brave_module.main(_build_installer_data(), version=None, update=False)

    assert printed_scripts == [("brew install --cask brave-browser", "shell", "Installation Script Preview")]
    assert executed_scripts == [("brew install --cask brave-browser", True, False)]


def test_main_rejects_unknown_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(brave_module, "Console", _FakeConsole)
    monkeypatch.setattr(brave_module.platform, "system", lambda: "Plan9")

    with pytest.raises(NotImplementedError, match="Unsupported platform: Plan9"):
        brave_module.main(_build_installer_data(), version=None, update=False)
