import json
import subprocess

import pytest

from stackops.cluster.sessions_managers import session_conflict
from stackops.scripts.python.helpers.helpers_sessions import sessions_cli_common, sessions_herdr
from stackops.utils.schemas.layouts.layout_types import LayoutConfig


def test_resolve_standard_backend_accepts_herdr_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    import platform

    monkeypatch.setattr(platform, "system", lambda: "Darwin")

    assert sessions_cli_common.resolve_standard_backend("herdr") == "herdr"
    assert sessions_cli_common.resolve_standard_backend("h") == "herdr"


def test_resolve_standard_backend_accepts_aoe_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    import platform

    monkeypatch.setattr(platform, "system", lambda: "Darwin")

    assert sessions_cli_common.resolve_standard_backend("aoe") == "aoe"
    assert sessions_cli_common.resolve_standard_backend("a") == "aoe"
    assert sessions_cli_common.resolve_standard_backend("auto") == "tmux"


def test_herdr_launcher_uses_one_tab_per_layout_tab(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    layout: LayoutConfig = {
        "layoutName": "backendProbe",
        "layoutTabs": [
            {"tabName": "Agent0", "startDir": str(tmp_path), "command": "printf agent-0"},
            {"tabName": "Agent1", "startDir": str(tmp_path), "command": "printf agent-1"},
        ],
    }
    observed_plain_commands: list[list[str]] = []

    def fake_run_herdr_json(args: list[str]) -> sessions_herdr.JsonObject:
        if args[:3] == ["herdr", "workspace", "create"]:
            return {
                "result": {
                    "workspace": {"workspace_id": "workspace-1"},
                    "tab": {"tab_id": "workspace-1:1"},
                    "root_pane": {"pane_id": "workspace-1-pane-1"},
                }
            }
        if args[:3] == ["herdr", "tab", "create"]:
            return {
                "result": {
                    "tab": {"tab_id": "workspace-1:2"},
                    "root_pane": {"pane_id": "workspace-1-pane-2"},
                }
            }
        raise AssertionError(f"Unexpected JSON Herdr command: {args}")

    def fake_run_herdr(args: list[str]) -> str:
        observed_plain_commands.append(args)
        return ""

    monkeypatch.setattr(sessions_herdr, "_run_herdr_json", fake_run_herdr_json)
    monkeypatch.setattr(sessions_herdr, "_run_herdr", fake_run_herdr)

    summary = sessions_herdr.launch_layout_with_herdr(layout=layout)

    assert summary.workspace_id == "workspace-1"
    assert summary.workspace_label == "backendProbe"
    assert [tab.name for tab in summary.tabs] == ["Agent0", "Agent1"]
    assert observed_plain_commands == [
        ["herdr", "tab", "rename", "workspace-1:1", "Agent0"],
        ["herdr", "pane", "run", "workspace-1-pane-1", "printf agent-0"],
        ["herdr", "pane", "run", "workspace-1-pane-2", "printf agent-1"],
    ]


def test_run_layouts_with_herdr_skips_existing_workspace(monkeypatch: pytest.MonkeyPatch) -> None:
    layout: LayoutConfig = {
        "layoutName": "backendProbe",
        "layoutTabs": [
            {"tabName": "Agent0", "startDir": ".", "command": "printf agent-0"},
        ],
    }
    launched: list[LayoutConfig] = []

    monkeypatch.setattr(
        sessions_herdr,
        "build_session_launch_plan",
        lambda requested_session_names, backend, on_conflict: [
            {
                "requested_name": "backendProbe",
                "session_name": "backendProbe",
                "restart_required": False,
                "skip_launch": True,
            }
        ],
    )
    monkeypatch.setattr(
        sessions_herdr,
        "launch_layout_with_herdr",
        lambda layout: launched.append(layout),
    )

    results = sessions_herdr.run_layouts_with_herdr(
        layouts_selected=[layout],
        on_conflict="skip",
    )

    assert results == {
        "backendProbe": {
            "success": True,
            "message": "Skipped existing Herdr workspace 'backendProbe'",
        }
    }
    assert launched == []


def test_session_conflict_lists_herdr_workspace_labels(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        assert args == ["herdr", "workspace", "list"]
        return subprocess.CompletedProcess(
            args,
            0,
            json.dumps(
                {
                    "result": {
                        "workspaces": [
                            {"workspace_id": "workspace-1", "label": "alpha"},
                            {"workspace_id": "workspace-2", "label": ""},
                            {"workspace_id": "workspace-3", "label": "beta"},
                        ]
                    }
                }
            ),
            "",
        )

    monkeypatch.setattr(session_conflict.subprocess, "run", fake_run)

    assert session_conflict.list_existing_sessions("herdr") == {"alpha", "beta"}


def test_kill_existing_session_closes_matching_herdr_workspaces(monkeypatch: pytest.MonkeyPatch) -> None:
    observed_commands: list[list[str]] = []

    def fake_run(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        observed_commands.append(args)
        if args == ["herdr", "workspace", "list"]:
            return subprocess.CompletedProcess(
                args,
                0,
                json.dumps(
                    {
                        "result": {
                            "workspaces": [
                                {"workspace_id": "workspace-1", "label": "alpha"},
                                {"workspace_id": "workspace-2", "label": "beta"},
                                {"workspace_id": "workspace-3", "label": "alpha"},
                            ]
                        }
                    }
                ),
                "",
            )
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(session_conflict.subprocess, "run", fake_run)

    session_conflict.kill_existing_session("herdr", "alpha")

    assert observed_commands == [
        ["herdr", "workspace", "list"],
        ["herdr", "workspace", "close", "workspace-1"],
        ["herdr", "workspace", "close", "workspace-3"],
    ]
