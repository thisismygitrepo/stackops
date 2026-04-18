from __future__ import annotations

import subprocess

import pytest

from stackops.jobs.installer.python_scripts import alacritty as alacritty_module
from stackops.utils.schemas.installer.installer_types import InstallerData


class _FakeConsole:
    def print(self, *_args: object, **_kwargs: object) -> None:
        return None


def _build_installer_data() -> InstallerData:
    return {
        "appName": "Alacritty",
        "license": "MIT",
        "doc": "Terminal",
        "repoURL": "CMD",
        "fileNamePattern": {"amd64": {"windows": None, "linux": None, "darwin": None}, "arm64": {"windows": None, "linux": None, "darwin": None}},
    }


def test_main_runs_cargo_program_for_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, object] = {}

    def fake_run(program: str, shell: bool, text: bool, check: bool) -> subprocess.CompletedProcess[str]:
        called["program"] = program
        called["shell"] = shell
        called["text"] = text
        called["check"] = check
        return subprocess.CompletedProcess(args=program, returncode=0)

    monkeypatch.setattr(alacritty_module, "Console", _FakeConsole)
    monkeypatch.setattr(alacritty_module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(alacritty_module.subprocess, "run", fake_run)

    alacritty_module.main(_build_installer_data(), version=None, update=False)

    program = called["program"]
    assert isinstance(program, str)
    assert "cargo install alacritty" in program
    assert "alacritty-theme" in program
    assert called["shell"] is True
    assert called["text"] is True
    assert called["check"] is True


def test_main_rejects_unknown_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(alacritty_module, "Console", _FakeConsole)
    monkeypatch.setattr(alacritty_module.platform, "system", lambda: "Plan9")

    with pytest.raises(NotImplementedError, match="Unsupported platform: Plan9"):
        alacritty_module.main(_build_installer_data(), version="1.0.0", update=False)
