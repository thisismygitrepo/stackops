import json
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_parallel_backend
from stackops.scripts.python.helpers.helpers_agents import agents_parallel_aoe_backend
from stackops.utils.schemas.layouts.layout_types import LayoutConfig


def test_resolve_agent_parallel_backend_accepts_aoe() -> None:
    assert agents_parallel_backend.resolve_agent_parallel_backend("aoe") == "aoe"
    assert agents_parallel_backend.resolve_agent_parallel_backend("e") == "aoe"


def test_resolve_aoe_agent_for_stackops_agent_maps_known_agents() -> None:
    assert agents_parallel_aoe_backend.resolve_aoe_agent_for_stackops_agent("codex") == "codex"
    assert agents_parallel_aoe_backend.resolve_aoe_agent_for_stackops_agent("cursor-agent") == "cursor"
    assert agents_parallel_aoe_backend.resolve_aoe_agent_for_stackops_agent("crush") is None


def test_run_generated_layout_dispatches_to_aoe(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    layout_path = tmp_path / "layout.json"
    observed: dict[str, object] = {}

    def fake_run_generated_layout_with_aoe(*, layout_output_path: Path, agent: str | None = None) -> None:
        observed["layout_output_path"] = layout_output_path
        observed["agent"] = agent

    monkeypatch.setattr(agents_parallel_aoe_backend, "run_generated_layout_with_aoe", fake_run_generated_layout_with_aoe)

    agents_parallel_backend.run_generated_layout(layout_output_path=layout_path, backend="aoe", agent="codex")

    assert observed["layout_output_path"] == layout_path
    assert observed["agent"] == "codex"


def test_herdr_launcher_uses_one_pane_run_per_layout_tab(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    layout_path = tmp_path / "layout.json"
    layout_path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "layouts": [
                    {
                        "layoutName": "backendProbe",
                        "layoutTabs": [
                            {"tabName": "Agent0", "startDir": str(tmp_path), "command": "printf agent-0"},
                            {"tabName": "Agent1", "startDir": str(tmp_path), "command": "printf agent-1"},
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    observed_plain_commands: list[list[str]] = []

    def fake_run_herdr_json(args: list[str]) -> agents_parallel_backend.JsonObject:
        if args[:3] == ["herdr", "workspace", "create"]:
            return {
                "result": {
                    "workspace": {"workspace_id": "workspace-1"},
                    "tab": {"tab_id": "workspace-1:1"},
                    "root_pane": {"pane_id": "workspace-1-pane-1"},
                }
            }
        if args[:3] == ["herdr", "tab", "create"]:
            return {"result": {"tab": {"tab_id": "workspace-1:2"}, "root_pane": {"pane_id": "workspace-1-pane-2"}}}
        raise AssertionError(f"Unexpected JSON Herdr command: {args}")

    def fake_run_herdr(args: list[str]) -> str:
        observed_plain_commands.append(args)
        return ""

    monkeypatch.setattr(agents_parallel_backend, "_run_herdr_json", fake_run_herdr_json)
    monkeypatch.setattr(agents_parallel_backend, "_run_herdr", fake_run_herdr)

    summary = agents_parallel_backend.run_generated_layout_with_herdr(layout_output_path=layout_path)

    assert summary.workspace_id == "workspace-1"
    assert [tab.name for tab in summary.tabs] == ["Agent0", "Agent1"]
    assert observed_plain_commands == [
        ["herdr", "tab", "rename", "workspace-1:1", "Agent0"],
        ["herdr", "pane", "run", "workspace-1-pane-1", "printf agent-0"],
        ["herdr", "pane", "run", "workspace-1-pane-2", "printf agent-1"],
    ]


def test_aoe_launcher_runs_generated_tab_commands_as_commands(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    layout_path = tmp_path / "layout.json"
    layout_path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "layouts": [
                    {
                        "layoutName": "backendProbe",
                        "layoutTabs": [{"tabName": "Agent0", "startDir": str(tmp_path), "command": "bash /tmp/agent_0_cmd.sh"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    observed: dict[str, object] = {}

    def fake_run_layouts_via_aoe(layouts_selected: list[LayoutConfig], options: agents_parallel_aoe_backend.AoeLaunchOptions) -> None:
        observed["layouts_selected"] = layouts_selected
        observed["options"] = options

    monkeypatch.setattr(agents_parallel_aoe_backend, "run_layouts_via_aoe", fake_run_layouts_via_aoe)

    agents_parallel_aoe_backend.run_generated_layout_with_aoe(layout_output_path=layout_path, agent="codex")

    assert observed["layouts_selected"] == [
        {"layoutName": "backendProbe", "layoutTabs": [{"tabName": "Agent0", "startDir": str(tmp_path), "command": "bash /tmp/agent_0_cmd.sh"}]}
    ]
    options = observed["options"]
    assert isinstance(options, agents_parallel_aoe_backend.AoeLaunchOptions)
    assert options.aoe_bin == "aoe"
    assert options.agent == "codex"
    assert options.tab_command_mode == "cmd"
    assert options.launch is True
