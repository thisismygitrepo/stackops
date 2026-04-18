from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

import stackops.utils.accessories as accessories
import stackops.utils.code as code
import stackops.utils.options_utils.options_tv_windows as options_tv_windows


@dataclass(frozen=True, slots=True)
class _RunResult:
    returncode: int


def test_normalize_extension_trims_whitespace_and_leading_dot() -> None:
    assert options_tv_windows._normalize_extension(" .md ") == "md"
    assert options_tv_windows._normalize_extension("   ") is None


def test_select_from_options_writes_preview_files_and_cleans_tempdir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_home = tmp_path.joinpath("home")
    fake_home.mkdir()

    def fake_home_method(_cls: type[Path]) -> Path:
        return fake_home

    def fake_randstr(*_args: object, **_kwargs: object) -> str:
        return "token01"

    captured: dict[str, str] = {}

    def fake_run_shell_script(
        script: str,
        *,
        display_script: bool,
        clean_env: bool,
    ) -> _RunResult:
        assert display_script is False
        assert clean_env is False
        assert "--preview-size 10" in script
        tempdir = fake_home.joinpath("tmp_results", "tmp_files", "tv_channel_token01")
        captured["entries"] = tempdir.joinpath("entries.txt").read_text(encoding="utf-8")
        captured["preview0"] = tempdir.joinpath("0.md").read_text(encoding="utf-8")
        tempdir.joinpath("selection.txt").write_text("1\n", encoding="utf-8")
        return _RunResult(returncode=0)

    monkeypatch.setattr(options_tv_windows.pathlib.Path, "home", classmethod(fake_home_method))
    monkeypatch.setattr(accessories, "randstr", fake_randstr)
    monkeypatch.setattr(code, "run_shell_script", fake_run_shell_script)

    result = options_tv_windows.select_from_options(
        {"one": "alpha", "two": "beta"},
        extension=".md",
        multi=False,
        preview_size_percent=5,
    )

    assert result == "two"
    assert captured["entries"].splitlines() == ["0|one", "1|two"]
    assert captured["preview0"] == "alpha"
    assert fake_home.joinpath("tmp_results", "tmp_files", "tv_channel_token01").exists() is False


def test_select_from_options_returns_empty_list_on_cancel(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_home = tmp_path.joinpath("home")
    fake_home.mkdir()

    def fake_home_method(_cls: type[Path]) -> Path:
        return fake_home

    def fake_randstr(*_args: object, **_kwargs: object) -> str:
        return "token02"

    def fake_run_shell_script(
        script: str,
        *,
        display_script: bool,
        clean_env: bool,
    ) -> _RunResult:
        _ = script, display_script, clean_env
        return _RunResult(returncode=130)

    monkeypatch.setattr(options_tv_windows.pathlib.Path, "home", classmethod(fake_home_method))
    monkeypatch.setattr(accessories, "randstr", fake_randstr)
    monkeypatch.setattr(code, "run_shell_script", fake_run_shell_script)

    result = options_tv_windows.select_from_options(
        {"one": "alpha"},
        extension="txt",
        multi=True,
        preview_size_percent=50,
    )

    assert result == []
