from __future__ import annotations

from pathlib import Path
import platform
import sys
from types import ModuleType
from typing import TypedDict

import pytest

import machineconfig.scripts.python.helpers.helpers_seek.seek_impl as seek_impl


class SymbolInfo(TypedDict):
    type: str
    name: str
    path: str
    file_path: str
    line: int
    end_line: int
    docstring: str
    body: str


class TtyStdin:
    encoding: str

    def __init__(self, encoding: str) -> None:
        self.encoding = encoding

    def isatty(self) -> bool:
        return True


def test_ast_option_helpers_build_lookup_and_payload() -> None:
    symbol: SymbolInfo = {
        "type": "function",
        "name": "demo",
        "path": "pkg.demo",
        "file_path": "pkg/demo.py",
        "line": 12,
        "end_line": 18,
        "docstring": "demo doc",
        "body": "def demo() -> None:\n    pass",
    }

    options_to_preview_mapping, symbol_lookup = seek_impl._build_ast_option_lookup(symbols=[symbol])
    option_key = "pkg.demo    [pkg/demo.py:12]"

    assert option_key in options_to_preview_mapping
    assert "def demo() -> None:" in options_to_preview_mapping[option_key]
    assert symbol_lookup[option_key] == symbol
    assert seek_impl._build_ast_output_payload(symbol=symbol) == {
        "type": "function",
        "name": "demo",
        "path": "pkg.demo",
        "file_path": "pkg/demo.py",
        "line": 12,
        "end_line": 18,
        "docstring": "demo doc",
    }


def test_shell_helpers_quote_for_linux_and_windows() -> None:
    linux_script = seek_impl._prepend_directory_change(script="echo hi", directory="/tmp/alpha beta", platform_name="Linux")
    windows_script = seek_impl._prepend_directory_change(
        script="Write-Output hi", directory="C:/Users/alex/rock'n", platform_name="Windows"
    )
    linux_query_script = seek_impl._set_initial_query(
        script='INITIAL_QUERY=""\necho hi', search_term="alpha beta", platform_name="Linux"
    )
    windows_query_script = seek_impl._set_initial_query(
        script="$initialQuery = ''\nWrite-Output hi", search_term="rock'n", platform_name="Windows"
    )

    assert linux_script.startswith("cd '/tmp/alpha beta'\n")
    assert windows_script.startswith("Set-Location -LiteralPath 'C:/Users/alex/rock''n'\n")
    assert "INITIAL_QUERY='alpha beta'" in linux_query_script
    assert "$initialQuery = 'rock''n'" in windows_query_script
    assert seek_impl._get_fzf_query_argument(search_term="alpha beta", platform_name="Linux") == "--query 'alpha beta'"
    assert seek_impl._get_fzf_query_argument(search_term="rock'n", platform_name="Windows") == "--query 'rock''n'"


def test_search_file_with_context_builds_linux_script_with_cleanup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target_file = tmp_path / "notes.txt"
    target_file.write_text("line\n", encoding="utf-8")

    monkeypatch.setattr(platform, "system", lambda: "Linux")

    script = seek_impl.search_file_with_context(path=str(target_file), is_temp_file=True, edit=False)

    assert "$TEMP_FILE" not in script
    assert "nl -ba -w1 -s' '" in script
    assert "| cut -d' ' -f2-" in script
    assert f"\nrm {target_file}" in script


def test_search_file_with_context_builds_windows_editor_script(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target_file = tmp_path / "rock'n.txt"
    target_file.write_text("line\n", encoding="utf-8")

    monkeypatch.setattr(platform, "system", lambda: "Windows")

    script = seek_impl.search_file_with_context(path=str(target_file), is_temp_file=True, edit=True)

    assert "powershell -NoProfile -ExecutionPolicy Bypass -EncodedCommand" in script
    assert "hx " in script
    assert "Remove-Item" in script
    assert "rock''n.txt" in script


def test_search_file_with_context_rejects_unsupported_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Plan9")

    with pytest.raises(RuntimeError, match="Unsupported platform"):
        seek_impl.search_file_with_context(path="/tmp/notes.txt", is_temp_file=False, edit=False)


def test_seek_dispatches_to_symantic_search(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str | None] = {}

    def fake_run_symantic_search(path: str, query: str, extension: str | None) -> None:
        captured["path"] = path
        captured["query"] = query
        captured["extension"] = extension

    monkeypatch.setattr(seek_impl, "_run_symantic_search", fake_run_symantic_search)

    seek_impl.seek(
        path="repo",
        search_term="needle",
        ast=False,
        symantic=True,
        extension=".py",
        file=False,
        dotfiles=False,
        rga=False,
        edit=False,
        install_dependencies=False,
    )

    assert captured == {"path": "repo", "query": "needle", "extension": ".py"}


def test_seek_dispatches_to_file_search(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str | bool | None] = {}

    def fake_run_file_search(directory: str | None, dotfiles: bool, edit: bool, search_term: str) -> None:
        captured["directory"] = directory
        captured["dotfiles"] = dotfiles
        captured["edit"] = edit
        captured["search_term"] = search_term

    monkeypatch.setattr(seek_impl, "_run_file_search", fake_run_file_search)

    seek_impl.seek(
        path="repo",
        search_term="needle",
        ast=False,
        symantic=False,
        extension=None,
        file=True,
        dotfiles=True,
        rga=False,
        edit=True,
        install_dependencies=False,
    )

    assert captured == {"directory": "repo", "dotfiles": True, "edit": True, "search_term": "needle"}


def test_seek_runs_context_search_for_file_input(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target_file = tmp_path / "notes.txt"
    target_file.write_text("line\n", encoding="utf-8")
    captured: dict[str, str | bool] = {}

    def fake_search_file_with_context(path: str, is_temp_file: bool, edit: bool) -> str:
        captured["path"] = path
        captured["is_temp_file"] = is_temp_file
        captured["edit"] = edit
        return "echo scripted"

    fake_code_module = ModuleType("machineconfig.utils.code")

    def fake_exit_then_run_shell_script(*, script: str, strict: bool) -> None:
        captured["script"] = script
        captured["strict"] = strict

    setattr(fake_code_module, "exit_then_run_shell_script", fake_exit_then_run_shell_script)
    monkeypatch.setattr(seek_impl, "search_file_with_context", fake_search_file_with_context)
    monkeypatch.setitem(sys.modules, "machineconfig.utils.code", fake_code_module)

    seek_impl.seek(
        path=str(target_file),
        search_term="needle",
        ast=False,
        symantic=False,
        extension=None,
        file=False,
        dotfiles=False,
        rga=False,
        edit=True,
        install_dependencies=False,
    )

    assert captured == {
        "path": str(target_file),
        "is_temp_file": False,
        "edit": True,
        "script": "echo scripted",
        "strict": False,
    }


def test_seek_dispatches_to_text_search_for_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str | bool | None] = {}

    def fake_run_text_search(rga: bool, directory: str | None, search_term: str) -> None:
        captured["rga"] = rga
        captured["directory"] = directory
        captured["search_term"] = search_term

    monkeypatch.setattr(seek_impl, "_run_text_search", fake_run_text_search)
    monkeypatch.setattr(sys, "stdin", TtyStdin(encoding="utf-8"))

    seek_impl.seek(
        path=str(tmp_path),
        search_term="needle",
        ast=False,
        symantic=False,
        extension=None,
        file=False,
        dotfiles=False,
        rga=True,
        edit=False,
        install_dependencies=False,
    )

    assert captured == {"rga": True, "directory": str(tmp_path), "search_term": "needle"}
