from typing import cast
from unittest.mock import patch
import pytest

from typer.testing import CliRunner

from machineconfig.cluster.sessions_managers import session_conflict
from machineconfig.scripts.python import sessions
from machineconfig.scripts.python.helpers.helpers_sessions import sessions_impl
from machineconfig.utils.schemas.layouts.layout_types import LayoutConfig


runner = CliRunner()


def _layout(name: str) -> LayoutConfig:
    return {
        "layoutName": name,
        "layoutTabs": [
            {
                "tabName": f"{name}-tab",
                "startDir": "/tmp",
                "command": "echo test",
            }
        ],
    }


def test_build_session_launch_plan_rejects_removed_merge_new_windows_policy() -> None:
    with pytest.raises(ValueError, match="Unsupported on_conflict policy: mergeNewWindows"):
        session_conflict.build_session_launch_plan(
            requested_session_names=["demo"],
            backend="windows-terminal",
            on_conflict=cast(session_conflict.SessionConflictAction, "mergeNewWindows"),
        )


@pytest.mark.parametrize(
    "on_conflict",
    [
        "mergeNewWindowsOverwriteMatchingWindows",
        "mergeNewWindowsSkipMatchingWindows",
    ],
)
def test_build_session_launch_plan_rejects_merge_modes_for_zellij(
    on_conflict: session_conflict.SessionConflictAction,
) -> None:
    with pytest.raises(ValueError) as exc_info:
        session_conflict.build_session_launch_plan(
            requested_session_names=["demo"],
            backend="zellij",
            on_conflict=on_conflict,
        )
    assert "tmux" in str(exc_info.value)
    assert "windows-terminal" in str(exc_info.value)


@pytest.mark.parametrize(
    "on_conflict",
    [
        "mergeNewWindowsOverwriteMatchingWindows",
        "mergeNewWindowsSkipMatchingWindows",
    ],
)
def test_build_session_launch_plan_accepts_tmux_merge_modes(
    on_conflict: session_conflict.SessionConflictAction,
) -> None:
    with patch.object(
        session_conflict,
        "list_existing_sessions",
        return_value={"demo"},
    ):
        launch_plan = session_conflict.build_session_launch_plan(
            requested_session_names=["demo"],
            backend="tmux",
            on_conflict=on_conflict,
        )

    assert launch_plan == [
        {
            "requested_name": "demo",
            "session_name": "demo",
            "restart_required": False,
            "conflict_source": "existing",
        }
    ]


def test_build_session_launch_plan_overwrites_matching_windows_once() -> None:
    with patch.object(
        session_conflict,
        "list_existing_sessions",
        return_value={"Alpha"},
    ):
        launch_plan = session_conflict.build_session_launch_plan(
            requested_session_names=["Alpha", "Alpha", "Beta"],
            backend="windows-terminal",
            on_conflict="mergeNewWindowsOverwriteMatchingWindows",
        )

    assert [item["restart_required"] for item in launch_plan] == [True, False, False]
    assert launch_plan[0].get("conflict_source") == "existing"
    assert launch_plan[1].get("conflict_source") == "duplicate"


def test_build_session_launch_plan_skips_existing_windows_but_keeps_new_duplicates() -> None:
    with patch.object(
        session_conflict,
        "list_existing_sessions",
        return_value={"Alpha"},
    ):
        launch_plan = session_conflict.build_session_launch_plan(
            requested_session_names=["Alpha", "Beta", "Beta"],
            backend="windows-terminal",
            on_conflict="mergeNewWindowsSkipMatchingWindows",
        )

    assert launch_plan[0].get("skip_launch", False) is True
    assert launch_plan[0].get("conflict_source") == "existing"
    assert "skip_launch" not in launch_plan[1]
    assert launch_plan[2].get("conflict_source") == "duplicate"


def test_resolve_conflicts_for_batch_applies_skip_restart_and_rename() -> None:
    with patch.object(
        sessions_impl,
        "build_session_launch_plan",
        return_value=[
            {
                "requested_name": "Alpha",
                "session_name": "Alpha",
                "restart_required": False,
                "conflict_source": "existing",
                "skip_launch": True,
            },
            {
                "requested_name": "Beta",
                "session_name": "Beta",
                "restart_required": True,
                "conflict_source": "existing",
            },
            {
                "requested_name": "Gamma",
                "session_name": "Gamma_1",
                "restart_required": False,
                "conflict_source": "duplicate",
            },
        ],
    ):
        layouts_to_run, sessions_to_restart = sessions_impl.resolve_conflicts_for_batch(
            layouts_batch=[_layout("Alpha"), _layout("Beta"), _layout("Gamma")],
            backend="windows-terminal",
            on_conflict="mergeNewWindowsOverwriteMatchingWindows",
        )

    assert [layout["layoutName"] for layout in layouts_to_run] == ["Beta", "Gamma_1"]
    assert sessions_to_restart == {"Beta"}


def test_run_command_accepts_merge_overwrite_conflict_policy() -> None:
    with patch(
        "machineconfig.scripts.python.helpers.helpers_sessions.sessions_cli_run.run_cli"
    ) as run_cli:
        result = runner.invoke(
            sessions.get_app(),
            ["run", "--on-conflict", "mergeNewWindowsOverwriteMatchingWindows"],
        )

    assert result.exit_code == 0
    assert (
        run_cli.call_args.kwargs["on_conflict"]
        == "mergeNewWindowsOverwriteMatchingWindows"
    )


def test_run_layouts_kills_matching_windows_for_overwrite_policy() -> None:
    with (
        patch.object(
            sessions_impl,
            "resolve_conflicts_for_batch",
            return_value=([_layout("Alpha")], {"Alpha"}),
        ),
        patch.object(sessions_impl, "kill_existing_session") as kill_existing_session,
        patch(
            "machineconfig.cluster.sessions_managers.windows_terminal.wt_local_manager.WTLocalManager"
        ) as wt_local_manager,
    ):
        wt_local_manager.return_value.start_all_sessions.return_value = {
            "Alpha": {"success": True, "message": "started"}
        }
        sessions_impl.run_layouts(
            sleep_inbetween=0.0,
            monitor=False,
            parallel_layouts=None,
            kill_upon_completion=False,
            backend="windows-terminal",
            on_conflict="mergeNewWindowsOverwriteMatchingWindows",
            layouts_selected=[_layout("Alpha")],
        )

    kill_existing_session.assert_called_once_with("windows-terminal", "Alpha")
