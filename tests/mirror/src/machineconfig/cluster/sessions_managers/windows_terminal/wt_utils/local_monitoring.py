from __future__ import annotations

from io import StringIO

import pytest
from rich.console import Console

from machineconfig.cluster.sessions_managers.windows_terminal.wt_utils import local_monitoring as monitoring_module


def test_update_runtime_tracker_and_build_rows_truncate_commands() -> None:
    all_status: dict[str, dict[str, object]] = {
        "session-a": {
            "commands_status": {
                "tab-a": {
                    "running": True,
                    "command": "python very_long_command_name.py --with-flags",
                    "processes": [1, 2],
                },
                "tab-b": {
                    "running": False,
                    "command": "sleep 1",
                    "processes": [],
                },
            }
        }
    }
    runtime_seconds_by_key: dict[tuple[str, str], float] = {}

    monitoring_module.update_runtime_tracker(all_status, runtime_seconds_by_key, elapsed_seconds=12.9)
    rows = monitoring_module.build_monitoring_rows(
        all_status,
        runtime_seconds_by_key,
        max_command_length=12,
    )

    assert runtime_seconds_by_key == {("session-a", "tab-a"): 12.9, ("session-a", "tab-b"): 0.0}
    assert rows == [
        {
            "session": "session-a",
            "tab": "tab-a",
            "running": True,
            "runTime": "00:00:12",
            "command": "python ve...",
            "processes": 2,
        },
        {
            "session": "session-a",
            "tab": "tab-b",
            "running": False,
            "runTime": "00:00:00",
            "command": "sleep 1",
            "processes": 0,
        },
    ]


def test_print_helpers_render_table_and_summary(
    capsys: pytest.CaptureFixture[str],
) -> None:
    buffer = StringIO()
    console = Console(file=buffer, force_terminal=False, color_system=None, record=True)
    rows = [
        {
            "session": "session-a",
            "tab": "tab-a",
            "running": True,
            "runTime": "00:00:10",
            "command": "python app.py",
            "processes": 1,
        },
        {
            "session": "session-b",
            "tab": "tab-b",
            "running": False,
            "runTime": "00:00:00",
            "command": "sleep 1",
            "processes": 0,
        },
    ]

    running_count = monitoring_module.print_monitoring_table(rows, console)
    monitoring_module.print_quick_summary(
        {
            "running_commands": 1,
            "total_commands": 2,
            "healthy_sessions": 1,
            "total_sessions": 2,
        }
    )

    rendered = buffer.getvalue()
    assert running_count == 1
    assert "session-a" in rendered
    assert "tab-a" in rendered
    assert "1/2 commands running across 1/2 sessions" in capsys.readouterr().out
