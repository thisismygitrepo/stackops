from __future__ import annotations

import platform
from pathlib import Path

import pytest

from stackops.utils import code as code_utils


def test_get_uv_command_maps_supported_platforms() -> None:
    assert code_utils.get_uv_command("Windows") == '& "$HOME\\.local\\bin\\uv.exe" '
    assert code_utils.get_uv_command("linux") == '"$HOME/.local/bin/uv" '
    assert code_utils.get_uv_command("Darwin") == '"$HOME/.local/bin/uv" '


def test_get_uv_command_executing_python_file_builds_expected_command(monkeypatch: pytest.MonkeyPatch) -> None:
    deps = ["polars"]

    def fake_get_uv_command(platform: str) -> str:
        assert platform == "Linux"
        return "uv "

    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(code_utils, "get_uv_command", fake_get_uv_command)

    command = code_utils.get_uv_command_executing_python_file(python_file="script.py", uv_with=deps, uv_project_dir="/repo", uv_run_flags="--quiet")

    assert '--with "polars,rich"' in command
    assert '--project "/repo"' in command
    assert "run" in command
    assert command.strip().endswith("script.py")


def test_get_uv_command_executing_python_script_writes_script_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    call_args: list[tuple[str, list[str] | None, str | None, str, bool]] = []

    def fake_get_uv_command_executing_python_file(
        python_file: str, uv_with: list[str] | None, uv_project_dir: str | None, uv_run_flags: str = "", prepend_print: bool = True
    ) -> str:
        call_args.append((python_file, uv_with, uv_project_dir, uv_run_flags, prepend_print))
        return "uv run generated"

    monkeypatch.setattr(code_utils, "randstr", lambda: "fixed-name")
    monkeypatch.setattr(code_utils.Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.setattr(code_utils, "get_uv_command_executing_python_file", fake_get_uv_command_executing_python_file)

    command, script_path = code_utils.get_uv_command_executing_python_script(
        python_script='print("hello")', uv_with=["pytest"], uv_project_dir="/repo", prepend_print=False
    )

    assert command == "uv run generated"
    assert script_path == tmp_path.joinpath("tmp_results", "tmp_scripts", "python", "fixed-name.py")
    assert script_path.read_text(encoding="utf-8") == 'print("hello")'
    assert call_args == [(str(script_path), ["pytest"], "/repo", "", False)]
