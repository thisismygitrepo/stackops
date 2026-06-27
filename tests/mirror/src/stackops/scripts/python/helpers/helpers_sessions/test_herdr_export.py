import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from stackops.scripts.python import terminal
from stackops.scripts.python.helpers.helpers_sessions import (
    herdr_export,
    herdr_export_selection,
    herdr_export_source,
    terminal_export,
)


def test_build_layouts_from_herdr_workspaces_exports_tabs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_herdr_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        if command == ["herdr", "workspace", "list"]:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps(
                    {
                        "result": {
                            "workspaces": [
                                {
                                    "workspace_id": "w1",
                                    "label": "build",
                                    "number": 1,
                                    "tab_count": 2,
                                    "pane_count": 2,
                                },
                                {
                                    "workspace_id": "w2",
                                    "label": "other",
                                    "number": 2,
                                },
                            ]
                        }
                    }
                ),
                "",
            )
        if command == ["herdr", "tab", "list", "--workspace", "w1"]:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps(
                    {
                        "result": {
                            "tabs": [
                                {"tab_id": "w1:t2", "label": "worker", "number": 2},
                                {"tab_id": "w1:t1", "label": "main", "number": 1},
                            ]
                        }
                    }
                ),
                "",
            )
        if command == ["herdr", "pane", "list", "--workspace", "w1"]:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps(
                    {
                        "result": {
                            "panes": [
                                {
                                    "pane_id": "w1:p2",
                                    "tab_id": "w1:t2",
                                    "cwd": str(tmp_path / "worker"),
                                },
                                {
                                    "pane_id": "w1:p1",
                                    "tab_id": "w1:t1",
                                    "focused": True,
                                    "foreground_cwd": str(tmp_path / "main"),
                                },
                            ]
                        }
                    }
                ),
                "",
            )
        return subprocess.CompletedProcess(command, 1, "", "unexpected Herdr command")

    monkeypatch.setattr(herdr_export_source, "run_command", fake_herdr_command)

    workspaces = herdr_export_selection.resolve_herdr_workspaces_for_export(
        workspace_names="build",
        export_all_workspaces=False,
    )
    layouts = herdr_export.build_layouts_from_herdr_workspaces(
        workspaces=workspaces,
        command_source="shell",
    )

    assert layouts == [
        {
            "layoutName": "build",
            "layoutTabs": [
                {
                    "tabName": "main",
                    "startDir": str(tmp_path / "main"),
                    "command": """sh -lc 'exec "${SHELL:-/bin/sh}"'""",
                },
                {
                    "tabName": "worker",
                    "startDir": str(tmp_path / "worker"),
                    "command": """sh -lc 'exec "${SHELL:-/bin/sh}"'""",
                },
            ],
        }
    ]


def test_terminal_export_accepts_herdr_backend_alias(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    output_path = tmp_path / "herdr_layout.json"

    def fake_herdr_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        if command == ["herdr", "workspace", "list"]:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps({"result": {"workspaces": [{"workspace_id": "w1", "label": "build"}]}}),
                "",
            )
        if command == ["herdr", "tab", "list", "--workspace", "w1"]:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps({"result": {"tabs": [{"tab_id": "w1:t1", "label": "main", "number": 1}]}}),
                "",
            )
        if command == ["herdr", "pane", "list", "--workspace", "w1"]:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps({"result": {"panes": [{"pane_id": "w1:p1", "tab_id": "w1:t1", "cwd": str(tmp_path)}]}}),
                "",
            )
        return subprocess.CompletedProcess(command, 1, "", "unexpected Herdr command")

    monkeypatch.setattr(herdr_export_source, "run_command", fake_herdr_command)

    result = CliRunner().invoke(
        terminal.get_app(),
        [
            "export",
            "--backend",
            "h",
            "--sessions",
            "build",
            "--output-path",
            str(output_path),
        ],
    )

    assert result.exit_code == 0, result.output
    exported = json.loads(output_path.read_text(encoding="utf-8"))
    assert exported["layouts"][0]["layoutName"] == "build"
    assert "Exported herdr layout" in result.output
    assert "stackops terminal run --backend herdr --layouts-file" in result.output


def test_terminal_export_rejects_herdr_non_shell_command_source() -> None:
    with pytest.raises(ValueError, match="Herdr export only supports --command-source shell"):
        terminal_export.export_terminal_sessions(
            session_names="build",
            export_all_sessions=False,
            output_path=None,
            overwrite=False,
            merge=False,
            command_source="current-command",
            backend="herdr",
        )
