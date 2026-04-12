from __future__ import annotations

import sys
from types import ModuleType
from typing import cast

import pytest
import typer

import machineconfig.scripts.python.helpers.helpers_sessions.sessions_cli_run_all as subject
from machineconfig.utils.schemas.layouts.layout_types import LayoutConfig


class StubContext:
    def get_help(self) -> str:
        return "HELP"


def _make_context() -> typer.Context:
    return cast(typer.Context, StubContext())


def test_run_all_cli_merges_tabs_and_calls_dynamic_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = ModuleType(
        "machineconfig.scripts.python.helpers.helpers_sessions.sessions_dynamic"
    )
    layouts_selected: list[LayoutConfig] = [
        {
            "layoutName": "alpha",
            "layoutTabs": [{"tabName": "one", "startDir": "/a", "command": "echo a"}],
        },
        {
            "layoutName": "beta",
            "layoutTabs": [
                {"tabName": "two", "startDir": "/b", "command": "echo b"},
                {"tabName": "three", "startDir": "/c", "command": "echo c"},
            ],
        },
    ]
    substituted_layouts: list[LayoutConfig] = [
        {
            "layoutName": "alpha",
            "layoutTabs": [{"tabName": "one", "startDir": "/resolved/a", "command": "echo a"}],
        },
        {
            "layoutName": "beta",
            "layoutTabs": [
                {"tabName": "two", "startDir": "/resolved/b", "command": "echo b"},
                {"tabName": "three", "startDir": "/resolved/c", "command": "echo c"},
            ],
        },
    ]
    captured: dict[str, object] = {}

    def fake_run_dynamic(
        *,
        layout: LayoutConfig,
        max_parallel_tabs: int,
        kill_finished_tabs: bool,
        backend: str,
        on_conflict: str,
        poll_seconds: float,
    ) -> None:
        captured["layout"] = layout
        captured["max_parallel_tabs"] = max_parallel_tabs
        captured["kill_finished_tabs"] = kill_finished_tabs
        captured["backend"] = backend
        captured["on_conflict"] = on_conflict
        captured["poll_seconds"] = poll_seconds

    setattr(module, "run_dynamic", fake_run_dynamic)
    monkeypatch.setitem(sys.modules, module.__name__, module)
    monkeypatch.setattr(subject, "resolve_layout_source", lambda **kwargs: object())
    monkeypatch.setattr(subject, "load_all_layouts_from_source", lambda **kwargs: layouts_selected)
    monkeypatch.setattr(subject, "substitute_home_in_layouts", lambda layouts_selected: substituted_layouts)

    subject.run_all_cli(
        ctx=_make_context(),
        layouts_file="layouts.json",
        test_layout=False,
        max_parallel_tabs=2,
        poll_seconds=0.5,
        kill_finished_tabs=True,
        backend="tmux",
        on_conflict="rename",
        subsitute_home=True,
    )

    assert captured == {
        "layout": {
            "layoutName": "all-layouts-dynamic",
            "layoutTabs": [
                {"tabName": "one", "startDir": "/resolved/a", "command": "echo a"},
                {"tabName": "two", "startDir": "/resolved/b", "command": "echo b"},
                {"tabName": "three", "startDir": "/resolved/c", "command": "echo c"},
            ],
        },
        "max_parallel_tabs": 2,
        "kill_finished_tabs": True,
        "backend": "tmux",
        "on_conflict": "rename",
        "poll_seconds": 0.5,
    }


def test_run_all_cli_rejects_empty_layouts(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    empty_layouts: list[LayoutConfig] = [{"layoutName": "alpha", "layoutTabs": []}]

    monkeypatch.setattr(subject, "resolve_layout_source", lambda **kwargs: object())
    monkeypatch.setattr(subject, "load_all_layouts_from_source", lambda **kwargs: empty_layouts)

    with pytest.raises(typer.Exit) as exc_info:
        subject.run_all_cli(
            ctx=_make_context(),
            layouts_file="layouts.json",
            test_layout=False,
            max_parallel_tabs=2,
            poll_seconds=0.5,
            kill_finished_tabs=False,
            backend="auto",
            on_conflict="rename",
            subsitute_home=False,
        )

    captured = capsys.readouterr()
    assert exc_info.value.exit_code == 1
    assert "No tabs found across all layouts" in captured.out


def test_run_all_cli_converts_dynamic_errors_to_typer_exit(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = ModuleType(
        "machineconfig.scripts.python.helpers.helpers_sessions.sessions_dynamic"
    )
    layouts_selected: list[LayoutConfig] = [
        {
            "layoutName": "alpha",
            "layoutTabs": [{"tabName": "one", "startDir": "/a", "command": "echo a"}],
        }
    ]

    def fail_run_dynamic(**kwargs: object) -> None:
        _ = kwargs
        raise ValueError("boom")

    setattr(module, "run_dynamic", fail_run_dynamic)
    monkeypatch.setitem(sys.modules, module.__name__, module)
    monkeypatch.setattr(subject, "resolve_layout_source", lambda **kwargs: object())
    monkeypatch.setattr(subject, "load_all_layouts_from_source", lambda **kwargs: layouts_selected)

    with pytest.raises(typer.Exit) as exc_info:
        subject.run_all_cli(
            ctx=_make_context(),
            layouts_file="layouts.json",
            test_layout=False,
            max_parallel_tabs=2,
            poll_seconds=0.5,
            kill_finished_tabs=False,
            backend="auto",
            on_conflict="rename",
            subsitute_home=False,
        )

    captured = capsys.readouterr()
    assert exc_info.value.exit_code == 1
    assert "boom" in captured.out
