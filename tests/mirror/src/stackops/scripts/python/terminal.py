from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import cast

import pytest
import typer
from typer.testing import CliRunner

from stackops.scripts.python import terminal as module


def _install_module(monkeypatch: pytest.MonkeyPatch, module_name: str, attrs: dict[str, object]) -> None:
    fake_module = ModuleType(module_name)
    for attr_name, attr_value in attrs.items():
        setattr(fake_module, attr_name, attr_value)
    monkeypatch.setitem(sys.modules, module_name, fake_module)


def test_resolve_session_backend_enforces_platform_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    resolve_session_backend = cast(Callable[[str], str], getattr(module, "_resolve_session_backend"))

    monkeypatch.setattr("platform.system", lambda: "Linux")
    assert resolve_session_backend("z") == "zellij"
    assert resolve_session_backend("t") == "tmux"
    assert resolve_session_backend("auto") == "zellij"

    monkeypatch.setattr("platform.system", lambda: "Windows")
    with pytest.raises(typer.Exit):
        resolve_session_backend("z")


@pytest.mark.parametrize(
    ("name", "kill_all", "window", "message"),
    [("demo", True, False, "--all cannot be used together with NAME"), (None, True, True, "--all cannot be used together with --window")],
)
def test_kill_session_target_rejects_invalid_flag_pairs(
    name: str | None, kill_all: bool, window: bool, message: str, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(typer.Exit):
        module.kill_session_target(name=name, kill_all=kill_all, window=window, backend="tmux")

    captured = capsys.readouterr()
    assert message in captured.err


def test_attach_to_session_runs_requested_script(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, bool]] = []

    monkeypatch.setattr("platform.system", lambda: "Linux")
    _install_module(
        monkeypatch,
        "stackops.scripts.python.helpers.helpers_sessions.attach_impl",
        {"choose_session": lambda **kwargs: ("run_script", "echo launch")},
    )
    _install_module(monkeypatch, "stackops.utils.code", {"exit_then_run_shell_script": lambda *, script, strict: calls.append((script, strict))})

    module.attach_to_session(name="demo", new_session=False, kill_all=False, window=False, backend="tmux")

    assert calls == [("echo launch", True)]


def test_summarize_parses_comment_json_and_reports_counts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    layout_path = tmp_path.joinpath("layout.json")
    layout_path.write_text(
        "/* test */\n"
        "{\n"
        '  "version": 2,\n'
        '  "layouts": [\n'
        '    {"layoutName": "alpha", "layoutTabs": ["a", "b"]},\n'
        '    {"layoutName": "beta", "layoutTabs": ["c"]}\n'
        "  ]\n"
        "}\n",
        encoding="utf-8",
    )
    printed: list[object] = []

    class FakeConsole:
        def print(self, obj: object) -> None:
            printed.append(obj)

    class FakePanel:
        def __init__(self, renderable: object, title: str, border_style: str) -> None:
            self.renderable = renderable
            self.title = title
            self.border_style = border_style

    class FakeTable:
        def __init__(self, title: str) -> None:
            self.title = title
            self.columns: list[tuple[str, str | None, str | None]] = []
            self.rows: list[tuple[str, str, str]] = []

        def add_column(self, header: str, justify: str | None = None, style: str | None = None) -> None:
            self.columns.append((header, justify, style))

        def add_row(self, index: str, layout_name: str, tab_count: str) -> None:
            self.rows.append((index, layout_name, tab_count))

    _install_module(monkeypatch, "rich.console", {"Console": FakeConsole})
    _install_module(monkeypatch, "rich.panel", {"Panel": FakePanel})
    _install_module(monkeypatch, "rich.table", {"Table": FakeTable})
    _install_module(monkeypatch, "stackops.utils.io", {"remove_c_style_comments": lambda text: text.replace("/* test */", "")})

    module.summarize(layout_path=str(layout_path))

    summary_panel = cast(FakePanel, printed[0])
    layouts_table = cast(FakeTable, printed[1])
    assert "Layouts:[/bold] 2" in cast(str, summary_panel.renderable)
    assert "Tabs:[/bold] 3" in cast(str, summary_panel.renderable)
    assert layouts_table.rows == [("1", "alpha", "2"), ("2", "beta", "1")]


def test_run_aoe_normalizes_optional_lists(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_run_aoe_cli(**kwargs: object) -> None:
        calls.append(kwargs)

    _install_module(monkeypatch, "stackops.scripts.python.helpers.helpers_sessions.sessions_cli_run_aoe", {"run_aoe_cli": fake_run_aoe_cli})
    ctx = cast(typer.Context, SimpleNamespace(args=[]))

    module.run_aoe(ctx=ctx, args=None, env=None, yolo=True, sandbox="workspace-write", launch=False)

    assert len(calls) == 1
    call = calls[0]
    assert call["ctx"] is ctx
    assert call["args"] == []
    assert call["env"] == []
    assert call["sandbox"] == "workspace-write"
    assert call["launch"] is False


def test_get_app_help_lists_core_terminal_commands() -> None:
    runner = CliRunner()

    result = runner.invoke(module.get_app(), ["--help"])

    assert result.exit_code == 0
    assert "run" in result.stdout
    assert "run-all" in result.stdout
    assert "run-aoe" in result.stdout
    assert "attach" in result.stdout
    assert "kill" in result.stdout
    assert "summarize" in result.stdout
