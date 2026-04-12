from __future__ import annotations

from machineconfig.scripts.python.helpers.helpers_sessions import _zellij_backend_focus as focus_backend


def test_selectable_panes_for_tab_filters_runtime_only_panes() -> None:
    panes: list[dict[str, object]] = [
        {
            "id": 2,
            "tab_position": 1,
            "is_selectable": True,
            "is_plugin": False,
            "exited": False,
            "is_suppressed": False,
            "pane_x": 5,
            "pane_y": 0,
        },
        {
            "id": 1,
            "tab_position": 1,
            "is_selectable": True,
            "is_plugin": False,
            "exited": False,
            "is_suppressed": False,
            "pane_x": 0,
            "pane_y": 0,
        },
        {
            "id": 3,
            "tab_position": 1,
            "is_selectable": True,
            "is_plugin": True,
            "exited": False,
            "is_suppressed": False,
            "pane_x": 10,
            "pane_y": 0,
        },
        {
            "id": 4,
            "tab_position": 1,
            "is_selectable": True,
            "is_plugin": False,
            "exited": True,
            "is_suppressed": False,
            "pane_x": 15,
            "pane_y": 0,
        },
        {
            "id": 5,
            "tab_position": 1,
            "is_selectable": True,
            "is_plugin": False,
            "exited": False,
            "is_suppressed": True,
            "pane_x": 20,
            "pane_y": 0,
        },
        {
            "id": 6,
            "tab_position": 2,
            "is_selectable": True,
            "is_plugin": False,
            "exited": False,
            "is_suppressed": False,
            "pane_x": 0,
            "pane_y": 0,
        },
    ]

    selected = focus_backend.selectable_panes_for_tab(panes=panes, tab_position=1)

    assert [pane["id"] for pane in selected] == [1, 2]


def test_focus_path_to_pane_finds_shortest_direction_path() -> None:
    panes: list[dict[str, object]] = [
        {
            "id": 1,
            "is_focused": True,
            "pane_x": 0,
            "pane_y": 0,
            "pane_columns": 10,
            "pane_rows": 10,
        },
        {
            "id": 2,
            "is_focused": False,
            "pane_x": 10,
            "pane_y": 0,
            "pane_columns": 10,
            "pane_rows": 10,
        },
        {
            "id": 3,
            "is_focused": False,
            "pane_x": 0,
            "pane_y": 10,
            "pane_columns": 10,
            "pane_rows": 10,
        },
        {
            "id": 4,
            "is_focused": False,
            "pane_x": 10,
            "pane_y": 10,
            "pane_columns": 10,
            "pane_rows": 10,
        },
    ]

    path = focus_backend.focus_path_to_pane(panes=panes, target_pane=panes[3])

    assert path == ["right", "down"]


def test_focus_path_to_pane_returns_none_without_focus_or_target() -> None:
    panes_without_focus: list[dict[str, object]] = [
        {
            "id": 1,
            "is_focused": False,
            "pane_x": 0,
            "pane_y": 0,
            "pane_columns": 10,
            "pane_rows": 10,
        }
    ]
    invalid_target: dict[str, object] = {
        "pane_x": 0,
        "pane_y": 0,
        "pane_columns": 10,
        "pane_rows": 10,
    }

    assert focus_backend.focus_path_to_pane(panes=panes_without_focus, target_pane=panes_without_focus[0]) is None
    assert focus_backend.focus_path_to_pane(
        panes=[
            {
                "id": 1,
                "is_focused": True,
                "pane_x": 0,
                "pane_y": 0,
                "pane_columns": 10,
                "pane_rows": 10,
            }
        ],
        target_pane=invalid_target,
    ) is None
