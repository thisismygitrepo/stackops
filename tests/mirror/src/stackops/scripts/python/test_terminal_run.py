import json
import platform
from pathlib import Path

from typer.testing import CliRunner

from stackops.scripts.python import terminal
from stackops.scripts.python.helpers.helpers_sessions import sessions_aoe_impl
from stackops.utils.schemas.layouts.layout_types import LayoutConfig


def test_terminal_help_does_not_list_run_aoe() -> None:
    result = CliRunner().invoke(terminal.get_app(), ["--help"])

    assert result.exit_code == 0
    assert "run-aoe" not in result.output
    assert "Run selected layout(s) through agent-of-empires" not in result.output


def test_run_help_does_not_list_aoe_specific_options() -> None:
    result = CliRunner().invoke(terminal.get_app(), ["run", "--help"])

    assert result.exit_code == 0
    for option in (
        "aoe-bin",
        "--agent",
        "--model",
        "--provider",
        "--sandbox",
        "--yolo",
        "--cmd",
        "--args",
        "--env",
        "--force",
        "--dry-run",
        "--tab-command-mode",
        "--no-launch",
    ):
        assert option not in result.output


def test_run_aoe_backend_alias_dispatches_to_aoe(
    monkeypatch,
    tmp_path: Path,
) -> None:
    layout_path = tmp_path / "layouts.json"
    layout_path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "layouts": [
                    {
                        "layoutName": "alpha",
                        "layoutTabs": [
                            {"tabName": "one", "startDir": str(tmp_path), "command": "echo one"},
                            {"tabName": "two", "startDir": str(tmp_path), "command": "echo two"},
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    observed: dict[str, object] = {}

    def fake_run_layouts_via_aoe(
        layouts_selected: list[LayoutConfig],
        options: sessions_aoe_impl.AoeLaunchOptions,
    ) -> None:
        observed["layouts_selected"] = layouts_selected
        observed["options"] = options

    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    monkeypatch.setattr(sessions_aoe_impl, "run_layouts_via_aoe", fake_run_layouts_via_aoe)

    result = CliRunner().invoke(
        terminal.get_app(),
        [
            "run",
            "--layouts-file",
            str(layout_path),
            "--backend",
            "a",
            "--choose-tabs",
            "two",
        ],
    )

    assert result.exit_code == 0, result.output
    assert observed["layouts_selected"] == [
        {
            "layoutName": "alpha",
            "layoutTabs": [{"tabName": "two", "startDir": str(tmp_path), "command": "echo two"}],
        }
    ]
    options = observed["options"]
    assert isinstance(options, sessions_aoe_impl.AoeLaunchOptions)
    assert options.aoe_bin == "aoe"
    assert options.agent == "codex"
    assert options.model is None
    assert options.sandbox is None
    assert options.dry_run is False
    assert options.launch is True
