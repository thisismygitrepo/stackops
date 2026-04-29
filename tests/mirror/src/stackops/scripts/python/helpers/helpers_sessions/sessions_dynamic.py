import pytest

from stackops.scripts.python.helpers.helpers_sessions import sessions_dynamic


class _DummyLive:
    def __init__(self, *args: object, **kwargs: object) -> None:
        return None

    def __enter__(self) -> "_DummyLive":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def update(self, _renderable: object) -> None:
        return None


class _DummyConsole:
    def print(self, _renderable: object) -> None:
        return None


def test_run_dynamic_waits_two_seconds_before_first_completion_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current_time = 100.0
    observed_check_times: list[float] = []

    def fake_monotonic() -> float:
        return current_time

    def fake_sleep(seconds: float) -> None:
        nonlocal current_time
        current_time += seconds

    monkeypatch.setattr(sessions_dynamic, "monotonic", fake_monotonic)
    monkeypatch.setattr(sessions_dynamic.time, "sleep", fake_sleep)
    monkeypatch.setattr(sessions_dynamic, "Live", _DummyLive)
    monkeypatch.setattr(sessions_dynamic, "Console", _DummyConsole)
    monkeypatch.setattr(sessions_dynamic, "Panel", lambda *args, **kwargs: {"args": args, "kwargs": kwargs})
    monkeypatch.setattr(sessions_dynamic, "build_dashboard", lambda display: display)
    monkeypatch.setattr(sessions_dynamic, "create_display", lambda **kwargs: kwargs)
    monkeypatch.setattr(sessions_dynamic, "update_dashboard", lambda live, display: None)
    monkeypatch.setattr(sessions_dynamic, "format_duration", lambda seconds: f"{seconds:.0f}s")
    monkeypatch.setattr(sessions_dynamic, "_validate_backend", lambda backend: "tmux")
    monkeypatch.setattr(
        sessions_dynamic,
        "_start_backend_session",
        lambda backend, layout_name, initial_layout, initial_tasks, on_conflict: (
            ["dynamic-session"],
            {"dynamic-session": {"success": True}},
        ),
    )
    monkeypatch.setattr(
        sessions_dynamic,
        "_spawn_backend_tab",
        lambda backend, session_name, task: None,
    )
    monkeypatch.setattr(
        sessions_dynamic,
        "_close_backend_tab",
        lambda backend, session_name, runtime_tab_name: None,
    )

    def fake_is_dynamic_task_running(
        backend: str,
        session_name: str,
        task: sessions_dynamic.DynamicTabTask,
    ) -> bool:
        observed_check_times.append(current_time)
        return False

    monkeypatch.setattr(sessions_dynamic, "_is_dynamic_task_running", fake_is_dynamic_task_running)

    layout = {
        "layoutName": "demo-layout",
        "layoutTabs": [
            {"tabName": "first-tab", "startDir": "/workspace", "command": "uv run first.py"},
            {"tabName": "second-tab", "startDir": "/workspace", "command": "uv run second.py"},
        ],
    }

    sessions_dynamic.run_dynamic(
        layout=layout,
        max_parallel_tabs=1,
        kill_finished_tabs=False,
        backend="tmux",
        on_conflict="error",
        poll_seconds=5.0,
    )

    assert observed_check_times == [102.0, 107.0]
