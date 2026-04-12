from __future__ import annotations

from pathlib import Path

import pytest

from machineconfig.utils.files import ascii_art, headers
from machineconfig.utils.installer_utils import installer_locator_utils, installer_runner


class CaptureConsole:
    def __init__(self, sink: list[object]) -> None:
        self._sink = sink

    def print(self, value: object) -> None:
        self._sink.append(value)


def test_print_header_renders_shell_panel(monkeypatch: pytest.MonkeyPatch) -> None:
    printed: list[object] = []

    monkeypatch.setattr(headers.pretty, "install", lambda: None)
    monkeypatch.setattr(headers, "Console", lambda: CaptureConsole(printed))
    monkeypatch.setattr(installer_runner, "get_machineconfig_version", lambda: "9.9.9")

    headers.print_header()

    assert len(printed) == 1
    panel = printed[0]
    assert getattr(panel, "title", None) == "[bold blue]✨ 🐊 Machineconfig Shell 9.9.9 ✨ Made with 🐍 | Built with ❤️[/bold blue]"


def test_print_logo_linux_falls_back_to_repo_art(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    art_file = tmp_path.joinpath("fallback.txt")
    art_file.write_text("CROCO", encoding="utf-8")

    monkeypatch.setattr(headers.platform, "system", lambda: "Linux")
    monkeypatch.setattr(installer_locator_utils, "is_executable_in_path", lambda name: False)
    monkeypatch.setattr(headers.glob, "glob", lambda pattern: [str(art_file)])

    headers.print_logo("MC")

    captured = capsys.readouterr()
    assert "Missing ASCII art dependencies" in captured.out
    assert "CROCO" in captured.out


def test_print_logo_windows_uses_dynamic_renderer_when_dependencies_exist(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    home_dir = tmp_path.joinpath("home")
    install_dir = tmp_path.joinpath("install")
    npm_dir = home_dir.joinpath("AppData", "Roaming", "npm")
    npm_dir.mkdir(parents=True)
    install_dir.mkdir()
    npm_dir.joinpath("figlet").write_text("", encoding="utf-8")
    npm_dir.joinpath("lolcatjs").write_text("", encoding="utf-8")
    install_dir.joinpath("boxes.exe").write_text("", encoding="utf-8")

    monkeypatch.setattr(headers.platform, "system", lambda: "Windows")
    monkeypatch.setattr(headers.Path, "home", staticmethod(lambda: home_dir))
    monkeypatch.setattr(headers, "WINDOWS_INSTALL_PATH", str(install_dir))
    monkeypatch.setattr(headers.random, "choice", lambda options: options[0])
    monkeypatch.setattr(ascii_art, "font_box_color", lambda logo: calls.append(f"font:{logo}"))
    monkeypatch.setattr(ascii_art, "character_color", lambda logo: calls.append(f"char:{logo}"))

    headers.print_logo("MC")

    assert calls == ["font:MC"]
