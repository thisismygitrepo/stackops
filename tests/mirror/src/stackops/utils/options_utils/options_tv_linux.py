from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest

import stackops.utils.options_utils.options_tv_linux as options_tv_linux


def test_toml_inline_table_sorts_keys_and_escapes_values() -> None:
    result = options_tv_linux._toml_inline_table({"b": '"quoted"', "a": r"c:\tmp"})

    assert result == 'env = { a = "c:\\\\tmp", b = "\\"quoted\\"" }\n'


def test_select_from_options_builds_temp_channel_and_returns_selected_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_home = tmp_path.joinpath("home")
    fake_home.mkdir()
    fake_xdg = tmp_path.joinpath("xdg")
    fake_xdg.mkdir()

    def fake_home_method(_cls: type[Path]) -> Path:
        return fake_home

    def fake_terminal_size(*_args: object, **_kwargs: object) -> os.terminal_size:
        return os.terminal_size((120, 40))

    captured: dict[str, str] = {}

    def fake_run(
        args: list[str],
        *,
        check: bool,
        stdout: int,
        text: bool,
        env: dict[str, str],
    ) -> subprocess.CompletedProcess[list[str]]:
        assert args == ["tv", "temp_options"]
        assert check is False
        assert stdout == subprocess.PIPE
        assert text is True
        cable_link = fake_xdg.joinpath("television", "cable", "temp_options.toml")
        assert cable_link.is_symlink()
        channel_path = cable_link.resolve()
        captured["channel"] = channel_path.read_text(encoding="utf-8")
        captured["previews"] = channel_path.parent.joinpath("previews.tsv").read_text(encoding="utf-8")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="1\n")

    monkeypatch.setattr(options_tv_linux.pathlib.Path, "home", classmethod(fake_home_method))
    monkeypatch.setenv("XDG_CONFIG_HOME", fake_xdg.as_posix())
    monkeypatch.setattr(options_tv_linux.shutil, "get_terminal_size", fake_terminal_size)
    monkeypatch.setattr(options_tv_linux.subprocess, "run", fake_run)

    result = options_tv_linux.select_from_options(
        {"doc.md": "# Title", "script.py": "print('x')"},
        extension=None,
        multi=False,
        preview_size_percent=95,
    )

    assert result == "script.py"
    assert "size = 90" in captured["channel"]
    assert 'BAT_THEME = "ansi"' in captured["channel"]
    assert 'STACKOPS_PREVIEW_WIDTH = "104"' in captured["channel"]
    assert captured["previews"].splitlines()[0].endswith("\tmd")
    assert captured["previews"].splitlines()[1].endswith("\tpy")
    assert fake_xdg.joinpath("television", "cable", "temp_options.toml").exists() is False


def test_select_from_options_returns_empty_list_on_cancel(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_home = tmp_path.joinpath("home")
    fake_home.mkdir()
    fake_xdg = tmp_path.joinpath("xdg")
    fake_xdg.mkdir()

    def fake_home_method(_cls: type[Path]) -> Path:
        return fake_home

    def fake_run(
        args: list[str],
        *,
        check: bool,
        stdout: int,
        text: bool,
        env: dict[str, str],
    ) -> subprocess.CompletedProcess[list[str]]:
        _ = check, stdout, text, env
        return subprocess.CompletedProcess(args=args, returncode=130, stdout="")

    monkeypatch.setattr(options_tv_linux.pathlib.Path, "home", classmethod(fake_home_method))
    monkeypatch.setenv("XDG_CONFIG_HOME", fake_xdg.as_posix())
    monkeypatch.setattr(options_tv_linux.subprocess, "run", fake_run)

    result = options_tv_linux.select_from_options(
        {"one": "value"},
        extension="txt",
        multi=True,
        preview_size_percent=40,
    )

    assert result == []
