from pathlib import Path
from unittest.mock import Mock, patch

from typer.testing import CliRunner

from machineconfig.scripts.python import terminal
from machineconfig.scripts.python.helpers.helpers_sessions import (
    sessions_cli_run_all,
)


runner = CliRunner()


def test_sessions_help_lists_run_all_command() -> None:
    result = runner.invoke(terminal.get_app(), ["--help"])

    assert result.exit_code == 0
    assert "run-all" in result.output
    assert "<R>" in result.output


def test_run_help_omits_dynamic_mode_options() -> None:
    result = runner.invoke(terminal.get_app(), ["run", "--help"])

    assert result.exit_code == 0
    assert "--max-parallel-tabs" not in result.output
    assert "--kill-finished-tabs" not in result.output
    assert "--all-file" not in result.output
    assert "--parallel-layouts" in result.output


def test_run_rejects_old_dynamic_mode_flag() -> None:
    result = runner.invoke(
        terminal.get_app(),
        ["run", "--max-parallel-tabs", "4"],
    )

    assert result.exit_code != 0
    assert "No such option" in result.output
    assert "--max-parallel-tabs" in result.output


def test_run_all_help_only_exposes_dynamic_options() -> None:
    result = runner.invoke(terminal.get_app(), ["run-all", "--help"])

    assert result.exit_code == 0
    assert "--max-parallel-tabs" in result.output
    assert "--kill-finished-tabs" in result.output
    assert "--choose-layouts" not in result.output
    assert "--choose-tabs" not in result.output
    assert "--parallel-layouts" not in result.output


def test_run_all_dispatches_to_impl() -> None:
    with patch(
        "machineconfig.scripts.python.helpers.helpers_sessions.sessions_cli_run_all.run_all_cli"
    ) as run_all_cli:
        result = runner.invoke(
            terminal.get_app(),
            ["run-all", "--max-parallel-tabs", "6"],
        )

    assert result.exit_code == 0
    assert run_all_cli.call_args.kwargs["max_parallel_tabs"] == 6


def test_run_all_hidden_alias_dispatches_to_impl() -> None:
    with patch(
        "machineconfig.scripts.python.helpers.helpers_sessions.sessions_cli_run_all.run_all_cli"
    ) as run_all_cli:
        result = runner.invoke(
            terminal.get_app(),
            ["R", "--max-parallel-tabs", "3"],
        )

    assert result.exit_code == 0
    assert run_all_cli.call_args.kwargs["max_parallel_tabs"] == 3


def test_run_all_cli_merges_every_layout_before_running_dynamic_scheduler(
    tmp_path: Path,
) -> None:
    layout_path = tmp_path.joinpath("layouts.json")
    layout_path.write_text("{}", encoding="utf-8")
    ctx = Mock()

    with (
        patch.object(
            sessions_cli_run_all,
            "load_all_layouts",
            return_value=[
                {
                    "layoutName": "alpha",
                    "layoutTabs": [
                        {
                            "tabName": "one",
                            "startDir": "/tmp",
                            "command": "echo one",
                        }
                    ],
                },
                {
                    "layoutName": "beta",
                    "layoutTabs": [
                        {
                            "tabName": "two",
                            "startDir": "/tmp",
                            "command": "echo two",
                        }
                    ],
                },
            ],
        ),
        patch(
            "machineconfig.scripts.python.helpers.helpers_sessions.sessions_dynamic.run_dynamic"
        ) as run_dynamic,
    ):
        sessions_cli_run_all.run_all_cli(
            ctx=ctx,
            layouts_file=str(layout_path),
            max_parallel_tabs=2,
            poll_seconds=3.0,
            kill_finished_tabs=True,
            backend="tmux",
            on_conflict="error",
            subsitute_home=False,
        )

    assert run_dynamic.call_args.kwargs == {
        "layout": {
            "layoutName": "all-layouts-dynamic",
            "layoutTabs": [
                {
                    "tabName": "one",
                    "startDir": "/tmp",
                    "command": "echo one",
                },
                {
                    "tabName": "two",
                    "startDir": "/tmp",
                    "command": "echo two",
                },
            ],
        },
        "max_parallel_tabs": 2,
        "kill_finished_tabs": True,
        "backend": "tmux",
        "on_conflict": "error",
        "poll_seconds": 3.0,
    }
