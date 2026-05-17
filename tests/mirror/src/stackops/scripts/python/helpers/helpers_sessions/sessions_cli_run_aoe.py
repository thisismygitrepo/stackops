from pathlib import Path
from typing import cast

import pytest
import typer

from stackops.scripts.python.helpers.helpers_sessions import sessions_cli_run_aoe
from stackops.utils.schemas.layouts.layout_types import LayoutConfig


class _DummyContext:
    def get_help(self) -> str:
        return "help"


def test_run_aoe_cli_converts_tab_selection_errors_to_cli_exit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    layout_file = tmp_path / "layouts.json"
    layout_file.write_text("{}", encoding="utf-8")
    layouts: list[LayoutConfig] = [
        {
            "layoutName": "demo",
            "layoutTabs": [
                {
                    "tabName": "tab-1",
                    "startDir": "/tmp",
                    "command": "echo hello",
                }
            ],
        }
    ]

    def fake_find_layout_file(layout_path: str) -> str:
        return layout_path

    def fake_select_layout(
        layouts_json_file: str,
        selected_layouts_names: list[str],
        select_interactively: bool,
    ) -> list[LayoutConfig]:
        _ = layouts_json_file, selected_layouts_names, select_interactively
        return layouts

    monkeypatch.setattr(sessions_cli_run_aoe, "find_layout_file", fake_find_layout_file)
    monkeypatch.setattr(sessions_cli_run_aoe, "select_layout", fake_select_layout)

    with pytest.raises(typer.Exit) as exc_info:
        sessions_cli_run_aoe.run_aoe_cli(
            ctx=cast(typer.Context, _DummyContext()),
            layouts_file=str(layout_file),
            choose_layouts=None,
            choose_tabs="missing-tab",
            sleep_inbetween=0.0,
            max_tabs=5,
            agent="codex",
            model=None,
            provider=None,
            sandbox=None,
            yolo=False,
            cmd=None,
            args=[],
            env=[],
            force=False,
            dry_run=True,
            aoe_bin="aoe",
            tab_command_mode="prompt",
            subsitute_home=False,
            launch=False,
        )

    assert exc_info.value.exit_code == 1
    captured = capsys.readouterr()
    assert "Tab selector 'missing-tab' matched no tabs." in captured.out
