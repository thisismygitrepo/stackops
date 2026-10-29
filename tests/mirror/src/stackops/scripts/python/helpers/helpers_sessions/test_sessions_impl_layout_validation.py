import json
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_sessions.sessions_impl import select_layout


def _write_layout_file(tmp_path: Path, tab: dict[str, object]) -> str:
    layout_path = tmp_path / "layout.json"
    layout_path.write_text(json.dumps({"version": "0.1", "layouts": [{"layoutName": "demo", "layoutTabs": [tab]}]}), encoding="utf-8")
    return str(layout_path)


def _pane(name: str) -> dict[str, str]:
    return {"paneName": name, "startDir": "/work", "command": "echo hi"}


def test_valid_multi_pane_tab_is_loaded(tmp_path: Path) -> None:
    layout_file = _write_layout_file(tmp_path, {"tabName": "dev", "arrangement": "rows", "panes": [_pane("a"), _pane("b")]})
    layouts = select_layout(layouts_json_file=layout_file, selected_layouts_names=[], select_interactively=False)
    assert [pane["paneName"] for pane in layouts[0]["layoutTabs"][0]["panes"]] == ["a", "b"]


@pytest.mark.parametrize(
    ("tab", "message"),
    [
        ({"tabName": "dev", "startDir": "/work", "command": "ls"}, "'panes' must be a non-empty list"),
        ({"tabName": "dev", "panes": []}, "'panes' must be a non-empty list"),
        ({"tabName": "dev", "panes": [{"paneName": "a", "startDir": "/work"}]}, "'command' must be a string"),
        ({"tabName": "dev", "panes": [_pane("a"), _pane("a")]}, "duplicate paneName"),
        ({"tabName": "dev", "arrangement": "diagonal", "panes": [_pane("a")]}, "'arrangement' must be one of"),
    ],
)
def test_invalid_tabs_are_rejected(tmp_path: Path, tab: dict[str, object], message: str) -> None:
    layout_file = _write_layout_file(tmp_path, tab)
    with pytest.raises(ValueError, match=message):
        select_layout(layouts_json_file=layout_file, selected_layouts_names=[], select_interactively=False)
