

from typing import cast

import pytest
import typer

import stackops.scripts.python.helpers.helpers_sessions.sessions_cli_run as subject
from stackops.utils.schemas.layouts.layout_types import LayoutConfig


class StubContext:
    def get_help(self) -> str:
        return "HELP"


def _make_context() -> typer.Context:
    return cast(typer.Context, StubContext())


def test_run_cli_calls_run_layouts_with_resolved_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = object()
    chosen_layouts: list[LayoutConfig] = [
        {
            "layoutName": "alpha",
            "layoutTabs": [{"tabName": "one", "startDir": "/a", "command": "echo a"}],
        }
    ]
    substituted_layouts: list[LayoutConfig] = [
        {
            "layoutName": "alpha",
            "layoutTabs": [{"tabName": "one", "startDir": "/resolved", "command": "echo a"}],
        }
    ]
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        subject,
        "resolve_layout_source",
        lambda *, ctx, layouts_file, test_layout: source,
    )
    monkeypatch.setattr(
        subject,
        "load_selected_layouts_from_source",
        lambda *, layout_source, choose_layouts: chosen_layouts,
    )
    monkeypatch.setattr(
        subject,
        "choose_tabs_from_source",
        lambda *, layout_source, layouts_selected, choose_tabs: chosen_layouts,
    )
    monkeypatch.setattr(
        subject,
        "substitute_home_in_layouts",
        lambda layouts_selected: substituted_layouts,
    )
    monkeypatch.setattr(subject, "resolve_standard_backend", lambda backend: "tmux")

    def fake_run_layouts(
        *,
        sleep_inbetween: float,
        monitor: bool,
        parallel_layouts: int | None,
        kill_upon_completion: bool,
        layouts_selected: list[LayoutConfig],
        backend: str,
        on_conflict: str,
        exit_mode: str,
    ) -> None:
        captured["sleep_inbetween"] = sleep_inbetween
        captured["monitor"] = monitor
        captured["parallel_layouts"] = parallel_layouts
        captured["kill_upon_completion"] = kill_upon_completion
        captured["layouts_selected"] = layouts_selected
        captured["backend"] = backend
        captured["on_conflict"] = on_conflict
        captured["exit_mode"] = exit_mode

    monkeypatch.setattr(subject, "run_layouts", fake_run_layouts)

    subject.run_cli(
        ctx=_make_context(),
        layouts_file="layouts.json",
        test_layout=False,
        choose_layouts="alpha",
        choose_tabs="one",
        sleep_inbetween=0.25,
        parallel_layouts=None,
        max_tabs=2,
        max_layouts=4,
        backend="auto",
        on_conflict="rename",
        exit_mode="backToShell",
        monitor=True,
        kill_upon_completion=False,
        subsitute_home=True,
    )

    assert captured == {
        "sleep_inbetween": 0.25,
        "monitor": True,
        "parallel_layouts": None,
        "kill_upon_completion": False,
        "layouts_selected": substituted_layouts,
        "backend": "tmux",
        "on_conflict": "rename",
        "exit_mode": "backToShell",
    }


def test_run_cli_rejects_invalid_parallel_layouts(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    chosen_layouts: list[LayoutConfig] = [
        {
            "layoutName": "alpha",
            "layoutTabs": [{"tabName": "one", "startDir": "/a", "command": "echo a"}],
        }
    ]

    monkeypatch.setattr(subject, "resolve_layout_source", lambda **kwargs: object())
    monkeypatch.setattr(subject, "load_selected_layouts_from_source", lambda **kwargs: chosen_layouts)
    monkeypatch.setattr(subject, "choose_tabs_from_source", lambda **kwargs: chosen_layouts)
    monkeypatch.setattr(subject, "resolve_standard_backend", lambda backend: "zellij")
    monkeypatch.setattr(
        subject,
        "run_layouts",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("run_layouts should not run")),
    )

    with pytest.raises(typer.Exit) as exc_info:
        subject.run_cli(
            ctx=_make_context(),
            layouts_file="layouts.json",
            test_layout=False,
            choose_layouts=None,
            choose_tabs=None,
            sleep_inbetween=0.25,
            parallel_layouts=0,
            max_tabs=2,
            max_layouts=4,
            backend="auto",
            on_conflict="rename",
            exit_mode="backToShell",
            monitor=False,
            kill_upon_completion=False,
            subsitute_home=False,
        )

    captured = capsys.readouterr()
    assert exc_info.value.exit_code == 1
    assert "--parallel-layouts must be a positive integer." in captured.out


def test_run_cli_converts_run_layouts_value_error_to_typer_exit(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    chosen_layouts: list[LayoutConfig] = [
        {
            "layoutName": "alpha",
            "layoutTabs": [{"tabName": "one", "startDir": "/a", "command": "echo a"}],
        }
    ]

    monkeypatch.setattr(subject, "resolve_layout_source", lambda **kwargs: object())
    monkeypatch.setattr(subject, "load_selected_layouts_from_source", lambda **kwargs: chosen_layouts)
    monkeypatch.setattr(subject, "choose_tabs_from_source", lambda **kwargs: chosen_layouts)
    monkeypatch.setattr(subject, "resolve_standard_backend", lambda backend: "zellij")

    def fail_run_layouts(**kwargs: object) -> None:
        _ = kwargs
        raise ValueError("boom")

    monkeypatch.setattr(subject, "run_layouts", fail_run_layouts)

    with pytest.raises(typer.Exit) as exc_info:
        subject.run_cli(
            ctx=_make_context(),
            layouts_file="layouts.json",
            test_layout=False,
            choose_layouts=None,
            choose_tabs=None,
            sleep_inbetween=0.25,
            parallel_layouts=None,
            max_tabs=2,
            max_layouts=4,
            backend="auto",
            on_conflict="rename",
            exit_mode="backToShell",
            monitor=False,
            kill_upon_completion=False,
            subsitute_home=False,
        )

    captured = capsys.readouterr()
    assert exc_info.value.exit_code == 1
    assert "boom" in captured.out
