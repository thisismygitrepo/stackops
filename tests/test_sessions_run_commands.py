from pathlib import Path
import subprocess
from unittest.mock import Mock, patch

import pytest
import typer
from typer.testing import CliRunner

from machineconfig.scripts.python import terminal
from machineconfig.scripts.python.helpers.helpers_sessions import (
    sessions_cli_run,
    sessions_cli_run_all,
)
from machineconfig.scripts.python.helpers.helpers_sessions.sessions_test_layouts import (
    build_test_layouts,
    count_tabs_in_layouts,
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
    assert "--test-layout" in result.output
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
    assert "--test-layout" in result.output
    assert "--max-parallel-tabs" in result.output
    assert "--kill-finished-tabs" in result.output
    assert "--choose-layouts" not in result.output
    assert "--choose-tabs" not in result.output
    assert "--parallel-layouts" not in result.output


def test_run_dispatches_test_layout_option_to_impl() -> None:
    with patch(
        "machineconfig.scripts.python.helpers.helpers_sessions.sessions_cli_run.run_cli"
    ) as run_cli:
        result = runner.invoke(
            terminal.get_app(),
            ["run", "--test-layout"],
        )

    assert result.exit_code == 0
    assert run_cli.call_args.kwargs["test_layout"] is True


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


def test_run_all_dispatches_test_layout_option_to_impl() -> None:
    with patch(
        "machineconfig.scripts.python.helpers.helpers_sessions.sessions_cli_run_all.run_all_cli"
    ) as run_all_cli:
        result = runner.invoke(
            terminal.get_app(),
            ["run-all", "--test-layout", "--max-parallel-tabs", "4"],
        )

    assert result.exit_code == 0
    assert run_all_cli.call_args.kwargs["test_layout"] is True


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
    resolved_source = Mock(
        all_layouts=[
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
        ]
    )

    with (
        patch.object(
            sessions_cli_run_all,
            "resolve_layout_source",
            return_value=resolved_source,
        ),
        patch.object(
            sessions_cli_run_all,
            "load_all_layouts_from_source",
            return_value=resolved_source.all_layouts,
        ),
        patch(
            "machineconfig.scripts.python.helpers.helpers_sessions.sessions_dynamic.run_dynamic"
        ) as run_dynamic,
    ):
        sessions_cli_run_all.run_all_cli(
            ctx=ctx,
            layouts_file=str(layout_path),
            test_layout=False,
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


def test_run_cli_uses_generated_test_layouts_when_requested() -> None:
    ctx = Mock()

    with patch.object(sessions_cli_run, "run_layouts") as run_layouts:
        sessions_cli_run.run_cli(
            ctx=ctx,
            layouts_file=None,
            test_layout=True,
            choose_layouts=None,
            choose_tabs=None,
            sleep_inbetween=0.0,
            parallel_layouts=None,
            max_tabs=25,
            max_layouts=25,
            backend="tmux",
            on_conflict="error",
            monitor=False,
            kill_upon_completion=False,
            subsitute_home=False,
        )

    layouts_selected = run_layouts.call_args.kwargs["layouts_selected"]
    assert len(layouts_selected) == 4
    assert count_tabs_in_layouts(layouts=layouts_selected) == 48


def test_run_all_cli_uses_generated_test_layouts_when_requested() -> None:
    ctx = Mock()

    with patch(
        "machineconfig.scripts.python.helpers.helpers_sessions.sessions_dynamic.run_dynamic"
    ) as run_dynamic:
        sessions_cli_run_all.run_all_cli(
            ctx=ctx,
            layouts_file=None,
            test_layout=True,
            max_parallel_tabs=5,
            poll_seconds=1.5,
            kill_finished_tabs=False,
            backend="tmux",
            on_conflict="error",
            subsitute_home=False,
        )

    dynamic_layout = run_dynamic.call_args.kwargs["layout"]
    assert dynamic_layout["layoutName"] == "all-layouts-dynamic"
    assert len(dynamic_layout["layoutTabs"]) == 48


def test_generated_test_layout_command_is_self_contained_and_runs_outside_repo(
    tmp_path: Path,
) -> None:
    layouts = build_test_layouts(base_dir=tmp_path)
    first_command = layouts[1]["layoutTabs"][0]["command"]

    assert "machineconfig.scripts.python.helpers.helpers_sessions" not in first_command
    assert " -c " in first_command
    assert "\n" not in first_command

    result = subprocess.run(
        first_command,
        shell=True,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "finished" in result.stdout


def test_run_cli_rejects_test_layout_with_explicit_layouts_file() -> None:
    ctx = Mock()

    with patch.object(sessions_cli_run, "run_layouts") as run_layouts:
        with patch.object(sessions_cli_run.typer, "echo") as echo:
            with pytest.raises(typer.Exit):
                sessions_cli_run.run_cli(
                    ctx=ctx,
                    layouts_file="layouts.json",
                    test_layout=True,
                    choose_layouts=None,
                    choose_tabs=None,
                    sleep_inbetween=0.0,
                    parallel_layouts=None,
                    max_tabs=25,
                    max_layouts=25,
                    backend="tmux",
                    on_conflict="error",
                    monitor=False,
                    kill_upon_completion=False,
                    subsitute_home=False,
                )

    run_layouts.assert_not_called()
    assert any(
        "--test-layout cannot be used together with --layouts-file."
        in str(call.args[0])
        for call in echo.call_args_list
    )
