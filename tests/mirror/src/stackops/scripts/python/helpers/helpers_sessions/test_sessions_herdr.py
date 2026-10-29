import pytest

from stackops.scripts.python.helpers.helpers_sessions import sessions_herdr
from stackops.utils.schemas.layouts.layout_types import LayoutConfig, PaneConfig, TabArrangement

type Command = tuple[str, ...]


def _install_fake_herdr(monkeypatch: pytest.MonkeyPatch) -> list[Command]:
    calls: list[Command] = []
    next_pane_number = [2]

    def run_herdr_json(args: list[str]) -> sessions_herdr.JsonObject:
        calls.append(tuple(args))
        if args[1:3] == ["workspace", "create"]:
            return {"result": {"workspace": {"workspace_id": "w1"}, "tab": {"tab_id": "w1:t1"}, "root_pane": {"pane_id": "w1:p1"}}}
        if args[1:3] == ["pane", "split"]:
            pane_id = f"w1:p{next_pane_number[0]}"
            next_pane_number[0] += 1
            return {"result": {"pane": {"pane_id": pane_id}}}
        raise AssertionError(f"Unexpected herdr call: {args}")

    def run_herdr(args: list[str]) -> str:
        calls.append(tuple(args))
        return ""

    monkeypatch.setattr(sessions_herdr, "_run_herdr_json", run_herdr_json)
    monkeypatch.setattr(sessions_herdr, "_run_herdr", run_herdr)
    return calls


def _launch(monkeypatch: pytest.MonkeyPatch, arrangement: TabArrangement, pane_count: int) -> list[Command]:
    calls = _install_fake_herdr(monkeypatch)
    panes: list[PaneConfig] = [{"paneName": f"p{index}", "startDir": "/work", "command": f"cmd{index}"} for index in range(pane_count)]
    layout: LayoutConfig = {"layoutName": "demo", "layoutTabs": [{"tabName": "dev", "arrangement": arrangement, "panes": panes}]}
    sessions_herdr.launch_layout_with_herdr(layout=layout)
    return calls


def _splits(calls: list[Command]) -> list[tuple[str, str, str]]:
    return [(call[3], call[5], call[7]) for call in calls if call[1:3] == ("pane", "split")]


def _runs(calls: list[Command]) -> list[tuple[str, str]]:
    return [(call[3], call[4]) for call in calls if call[1:3] == ("pane", "run")]


def test_columns_split_right_with_even_shares(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _launch(monkeypatch, arrangement="columns", pane_count=3)
    assert _splits(calls) == [("w1:p1", "right", str(1 / 3)), ("w1:p2", "right", "0.5")]
    assert _runs(calls) == [("w1:p1", "cmd0"), ("w1:p2", "cmd1"), ("w1:p3", "cmd2")]


def test_rows_split_down_with_even_shares(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _launch(monkeypatch, arrangement="rows", pane_count=3)
    assert _splits(calls) == [("w1:p1", "down", str(1 / 3)), ("w1:p2", "down", "0.5")]


def test_grid_of_five_makes_rows_of_three_and_two_in_pane_order(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _launch(monkeypatch, arrangement="grid", pane_count=5)
    assert _splits(calls) == [
        ("w1:p1", "down", "0.5"),
        ("w1:p1", "right", str(1 / 3)),
        ("w1:p3", "right", "0.5"),
        ("w1:p2", "right", "0.5"),
    ]
    assert _runs(calls) == [
        ("w1:p1", "cmd0"),
        ("w1:p3", "cmd1"),
        ("w1:p4", "cmd2"),
        ("w1:p2", "cmd3"),
        ("w1:p5", "cmd4"),
    ]


def test_single_pane_is_not_split(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _launch(monkeypatch, arrangement="grid", pane_count=1)
    assert _splits(calls) == []
    assert _runs(calls) == [("w1:p1", "cmd0")]
