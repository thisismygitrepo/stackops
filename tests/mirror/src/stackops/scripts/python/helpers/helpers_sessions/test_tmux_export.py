import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from stackops.scripts.python import terminal
from stackops.scripts.python.helpers.helpers_sessions import _tmux_backend, tmux_export
from stackops.utils.schemas.layouts.layout_types import LayoutConfig


def _fake_tmux_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    if command == ["tmux", "list-sessions", "-F", "#S"]:
        return subprocess.CompletedProcess(command, 0, "alpha\nbeta\n", "")
    if command[:3] == ["tmux", "list-windows", "-t"]:
        return subprocess.CompletedProcess(
            command,
            0,
            "0\tmain\t1\tactive\t@10\n1\tworker\t2\t\t@11\n",
            "",
        )
    if command[:3] == ["tmux", "list-panes", "-s"]:
        return subprocess.CompletedProcess(
            command,
            0,
            "\n".join(
                [
                    "0\t0\t/tmp/alpha\tzsh\tactive\t\t\t100\t@10\t%10\tzsh",
                    "1\t0\t/tmp/worker\tpython\tactive\t\t\t101\t@11\t%11\tpython -m http.server",
                    "1\t1\t/tmp/worker\tbash\t\t\t\t102\t@11\t%12\tbash",
                ]
            ),
            "",
        )
    return subprocess.CompletedProcess(command, 1, "", "unexpected tmux command")


def test_build_layouts_from_tmux_sessions_exports_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tmux_export, "run_command", _fake_tmux_command)

    layouts = tmux_export.build_layouts_from_tmux_sessions(
        session_names=["alpha"],
        command_source="shell",
    )

    assert layouts == [
        {
            "layoutName": "alpha",
            "layoutTabs": [
                {
                    "tabName": "main",
                    "startDir": "/tmp/alpha",
                    "command": """sh -lc 'exec "${SHELL:-/bin/sh}"'""",
                },
                {
                    "tabName": "worker",
                    "startDir": "/tmp/worker",
                    "command": """sh -lc 'exec "${SHELL:-/bin/sh}"'""",
                },
            ],
        }
    ]


def test_build_layouts_from_tmux_sessions_can_export_start_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tmux_export, "run_command", _fake_tmux_command)

    layouts = tmux_export.build_layouts_from_tmux_sessions(
        session_names=["alpha"],
        command_source="start-command",
    )

    assert layouts[0]["layoutTabs"][1]["command"] == "python -m http.server"


def test_terminal_export_writes_layout_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    output_path = tmp_path / "tmux_layout.json"
    observed_sessions: list[str] = []
    fake_layouts: list[LayoutConfig] = [
        {
            "layoutName": "alpha",
            "layoutTabs": [
                {
                    "tabName": "main",
                    "startDir": str(tmp_path),
                    "command": "zsh",
                }
            ],
        }
    ]

    def fake_build_layouts_from_tmux_sessions(
        session_names: list[str],
        command_source: tmux_export.TmuxExportCommandSource,
    ) -> list[LayoutConfig]:
        assert command_source == "shell"
        observed_sessions.extend(session_names)
        return fake_layouts

    monkeypatch.setattr(tmux_export, "run_command", _fake_tmux_command)
    monkeypatch.setattr(_tmux_backend, "run_command", _fake_tmux_command)
    monkeypatch.setattr(tmux_export, "build_layouts_from_tmux_sessions", fake_build_layouts_from_tmux_sessions)

    result = CliRunner().invoke(
        terminal.get_app(),
        [
            "export",
            "--sessions",
            "alpha",
            "--output-path",
            str(output_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert observed_sessions == ["alpha"]
    exported = json.loads(output_path.read_text(encoding="utf-8"))
    assert exported["layouts"] == fake_layouts
    assert "stackops terminal run --layouts-file" in result.output
