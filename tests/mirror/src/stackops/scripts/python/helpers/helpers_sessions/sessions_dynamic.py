

import platform
import subprocess

import pytest

import stackops.scripts.python.helpers.helpers_sessions.sessions_dynamic as subject
from stackops.utils.schemas.layouts.layout_types import LayoutConfig


def test_run_zellij_action_raises_with_process_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subject.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args[0],
            returncode=1,
            stdout="",
            stderr="boom",
        ),
    )

    with pytest.raises(RuntimeError, match="zellij --session demo action list"):
        subject._run_zellij_action("demo", ["action", "list"])


def test_run_tmux_command_raises_with_process_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subject.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args[0],
            returncode=1,
            stdout="no server",
            stderr="",
        ),
    )

    with pytest.raises(RuntimeError, match="tmux list-sessions"):
        subject._run_tmux_command(["list-sessions"])


@pytest.mark.parametrize(
    ("backend", "system_name", "expected"),
    [
        ("zellij", "Linux", "zellij"),
        ("tmux", "Linux", "tmux"),
        ("auto", "Linux", "zellij"),
    ],
)
def test_validate_backend_returns_supported_choice(
    backend: str,
    system_name: str,
    expected: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(platform, "system", lambda: system_name)

    assert subject._validate_backend(backend) == expected


def test_validate_backend_rejects_windows_auto(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Windows")

    with pytest.raises(ValueError, match="not supported on Windows"):
        subject._validate_backend("auto")


@pytest.mark.parametrize(
    ("layout", "max_parallel_tabs", "poll_seconds", "expected_message"),
    [
        (
            {"layoutName": "alpha", "layoutTabs": [{"tabName": "one", "startDir": "/a", "command": "echo a"}]},
            0,
            0.5,
            "max_parallel_tabs must be a positive integer",
        ),
        (
            {"layoutName": "alpha", "layoutTabs": [{"tabName": "one", "startDir": "/a", "command": "echo a"}]},
            1,
            0.0,
            "poll_seconds must be a positive number",
        ),
        (
            {"layoutName": "alpha", "layoutTabs": []},
            1,
            0.5,
            "Selected layout has no tabs",
        ),
    ],
)
def test_run_dynamic_validates_inputs(
    layout: LayoutConfig,
    max_parallel_tabs: int,
    poll_seconds: float,
    expected_message: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(subject, "_validate_backend", lambda backend: "zellij")

    with pytest.raises(ValueError, match=expected_message):
        subject.run_dynamic(
            layout=layout,
            max_parallel_tabs=max_parallel_tabs,
            kill_finished_tabs=False,
            backend="auto",
            on_conflict="rename",
            poll_seconds=poll_seconds,
        )


def test_run_dynamic_schedules_pending_tabs_until_completion(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    layout: LayoutConfig = {
        "layoutName": "batch",
        "layoutTabs": [
            {"tabName": "one", "startDir": "/a", "command": "echo a"},
            {"tabName": "two", "startDir": "/b", "command": "echo b"},
            {"tabName": "three", "startDir": "/c", "command": "echo c"},
        ],
    }
    captured: dict[str, object] = {}
    spawned: list[tuple[str, str]] = []
    closed: list[tuple[str, str]] = []
    status_sequences: dict[str, list[bool]] = {
        "one__dynamic_1": [False],
        "two__dynamic_2": [True, False],
        "three__dynamic_3": [False],
    }
    status_indexes: dict[str, int] = {}

    class FakeManager:
        def __init__(self, *, session_layouts: list[LayoutConfig]) -> None:
            captured["session_layouts"] = session_layouts

        def start_all_sessions(
            self,
            *,
            on_conflict: str,
            poll_interval: float,
            poll_seconds: float,
        ) -> dict[str, dict[str, object]]:
            captured["on_conflict"] = on_conflict
            captured["poll_interval"] = poll_interval
            captured["start_poll_seconds"] = poll_seconds
            return {"demo": {"success": True, "message": "started"}}

        def get_all_session_names(self) -> list[str]:
            return ["demo"]

    def fake_is_task_running(*, task: subject.DynamicTabTask) -> bool:
        name = task["runtime_tab_name"]
        index = status_indexes.get(name, 0)
        status_indexes[name] = index + 1
        values = status_sequences[name]
        if index >= len(values):
            return values[-1]
        return values[index]

    def fake_spawn_tab(*, session_name: str, task: subject.DynamicTabTask) -> None:
        spawned.append((session_name, task["runtime_tab_name"]))

    def fake_close_tab(*, session_name: str, runtime_tab_name: str) -> None:
        closed.append((session_name, runtime_tab_name))

    monkeypatch.setattr(subject, "_validate_backend", lambda backend: "zellij")
    monkeypatch.setattr(subject, "ZellijLocalManager", FakeManager)
    monkeypatch.setattr(subject, "_is_task_running", fake_is_task_running)
    monkeypatch.setattr(subject, "_spawn_tab", fake_spawn_tab)
    monkeypatch.setattr(subject, "_close_tab", fake_close_tab)
    monkeypatch.setattr(subject.time, "sleep", lambda seconds: None)

    subject.run_dynamic(
        layout=layout,
        max_parallel_tabs=2,
        kill_finished_tabs=True,
        backend="zellij",
        on_conflict="rename",
        poll_seconds=0.1,
    )

    assert captured["session_layouts"] == [
        {
            "layoutName": "batch",
            "layoutTabs": [
                {"tabName": "one__dynamic_1", "startDir": "/a", "command": "echo a"},
                {"tabName": "two__dynamic_2", "startDir": "/b", "command": "echo b"},
            ],
        }
    ]
    assert spawned == [("demo", "three__dynamic_3")]
    assert closed == [
        ("demo", "one__dynamic_1"),
        ("demo", "two__dynamic_2"),
        ("demo", "three__dynamic_3"),
    ]
    output = capsys.readouterr().out
    assert "Dynamic tab runner started" in output
    assert "Started tab: three__dynamic_3" in output
    assert "completed all tabs" in output
