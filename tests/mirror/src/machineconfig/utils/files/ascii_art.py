from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType

import pytest

from machineconfig.utils.files import ascii_art


@dataclass(slots=True)
class FakeCompletedProcess:
    stdout: str


@dataclass(slots=True)
class FakeNamedTemporaryFile:
    path: Path

    @property
    def name(self) -> str:
        return str(self.path)

    def __enter__(self) -> FakeNamedTemporaryFile:
        self.path.write_text("", encoding="utf-8")
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: TracebackType | None) -> None:
        _ = exc_type, exc, traceback


def test_get_art_falls_back_to_machineconfig_when_fortune_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_choice(options: Sequence[str]) -> str:
        return options[0]

    def fake_run(command: str, shell: bool, capture_output: bool = False, text: bool = False, check: bool = False) -> FakeCompletedProcess:
        _ = shell, capture_output, text, check
        calls.append(command)
        if command == "fortune":
            raise RuntimeError("fortune unavailable")
        return FakeCompletedProcess(stdout="croco\n")

    monkeypatch.setattr(ascii_art.random, "choice", fake_choice)
    monkeypatch.setattr(ascii_art.subprocess, "run", fake_run)

    result = ascii_art.get_art(comment=None, artlib="boxes", style="shell", prefix="> ", verbose=False)

    assert calls[0] == "fortune"
    assert calls[1].startswith('figlet -f Banner "machineconfig" | boxes -d shell')
    assert result == "> croco\n"


def test_character_or_box_color_prefers_bat_on_macos_when_available(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    generated_files: list[str] = []
    commands: list[str] = []
    tmp_file = tmp_path.joinpath("art.txt")
    bin_dir = tmp_path.joinpath("bin")
    bin_dir.mkdir()
    bin_dir.joinpath("bat").write_text("", encoding="utf-8")

    def fake_named_temporary_file(mode: str, suffix: str, delete: bool) -> FakeNamedTemporaryFile:
        _ = mode, suffix, delete
        return FakeNamedTemporaryFile(tmp_file)

    def fake_get_art(
        comment: str | None = None,
        artlib: ascii_art.BOX_OR_CHAR | None = None,
        style: str | None = None,
        super_style: str = "scene",
        prefix: str = " ",
        file: str | None = None,
        verbose: bool = True,
    ) -> str:
        _ = comment, artlib, style, super_style, prefix, verbose
        assert file is not None
        generated_files.append(file)
        return ""

    def fake_run(command: str, shell: bool, check: bool) -> None:
        assert shell
        assert not check
        commands.append(command)

    monkeypatch.setenv("PATH", str(bin_dir))
    monkeypatch.setattr(ascii_art.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(ascii_art.tempfile, "NamedTemporaryFile", fake_named_temporary_file)
    monkeypatch.setattr(ascii_art, "get_art", fake_get_art)
    monkeypatch.setattr(ascii_art.subprocess, "run", fake_run)

    ascii_art.character_or_box_color("MC")

    assert generated_files == [str(tmp_file)]
    assert commands == [f"bat {tmp_file} | lolcatjs"]
