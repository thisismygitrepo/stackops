import click
import pytest
import typer

from stackops.scripts.python.helpers.helpers_sessions import sessions_cli_run


def test_run_cli_rejects_negative_sleep_inbetween(
    capsys: pytest.CaptureFixture[str],
) -> None:
    ctx = typer.Context(click.Command("test"))

    with pytest.raises(typer.Exit) as exc_info:
        sessions_cli_run.run_cli(
            ctx=ctx,
            layouts_file=None,
            test_layout=False,
            choose_layouts=None,
            choose_tabs=None,
            sleep_inbetween=-0.1,
            parallel_layouts=None,
            max_tabs=25,
            max_layouts=25,
            backend="tmux",
            on_conflict="error",
            exit_mode="backToShell",
            monitor=False,
            kill_upon_completion=False,
            subsitute_home=False,
        )

    captured = capsys.readouterr()

    assert exc_info.value.exit_code == 1
    assert captured.out == ""
    assert "--sleep-inbetween must be >= 0." in captured.err


def test_run_cli_allows_zero_sleep_inbetween(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    layout = {
        "layoutName": "demo",
        "layoutTabs": [
            {
                "tabName": "tab-1",
                "startDir": ".",
                "command": "echo hi",
            }
        ],
    }
    captured: dict[str, float | list[object] | str | bool | None] = {}
    ctx = typer.Context(click.Command("test"))
    layout_source = object()

    monkeypatch.setattr(
        sessions_cli_run,
        "resolve_layout_source",
        lambda ctx, layouts_file, test_layout: layout_source,
    )
    monkeypatch.setattr(
        sessions_cli_run,
        "load_selected_layouts_from_source",
        lambda layout_source, choose_layouts: [layout],
    )
    monkeypatch.setattr(
        sessions_cli_run,
        "choose_tabs_from_source",
        lambda layout_source, layouts_selected, choose_tabs: layouts_selected,
    )
    monkeypatch.setattr(
        sessions_cli_run,
        "resolve_standard_backend",
        lambda backend: "tmux",
    )

    def fake_run_layouts(
        *,
        sleep_inbetween: float,
        monitor: bool,
        parallel_layouts: int | None,
        kill_upon_completion: bool,
        layouts_selected: list[object],
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

    monkeypatch.setattr(sessions_cli_run, "run_layouts", fake_run_layouts)

    sessions_cli_run.run_cli(
        ctx=ctx,
        layouts_file=None,
        test_layout=False,
        choose_layouts=None,
        choose_tabs=None,
        sleep_inbetween=0.0,
        parallel_layouts=None,
        max_tabs=25,
        max_layouts=25,
        backend="tmux",
        on_conflict="error",
        exit_mode="backToShell",
        monitor=False,
        kill_upon_completion=False,
        subsitute_home=False,
    )

    assert captured == {
        "sleep_inbetween": 0.0,
        "monitor": False,
        "parallel_layouts": None,
        "kill_upon_completion": False,
        "layouts_selected": [layout],
        "backend": "tmux",
        "on_conflict": "error",
        "exit_mode": "backToShell",
    }
