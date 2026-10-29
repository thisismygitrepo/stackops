import pytest

from stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_layout import build_tmux_commands
from stackops.utils.schemas.layouts.layout_types import LayoutConfig, PaneConfig, TabArrangement, TabConfig, single_pane_tab


def _pane(name: str) -> PaneConfig:
    return {"paneName": name, "startDir": "/work", "command": f"run {name}"}


def _layout(tab: TabConfig) -> LayoutConfig:
    return {"layoutName": "demo", "layoutTabs": [tab]}


def test_single_pane_tab_creates_window_without_splitting() -> None:
    commands = build_tmux_commands(
        layout_config=_layout(single_pane_tab(tab_name="solo", start_dir="/work", command="echo hi")),
        session_name="demo",
        exit_mode="backToShell",
    )
    assert commands == [
        "tmux new-session -d -s demo -n solo -c /work",
        "tmux select-pane -t demo:solo -T solo",
        "tmux send-keys -t demo:solo 'echo hi' C-m",
        "tmux select-window -t demo:solo",
    ]


def test_columns_tab_splits_once_per_extra_pane_and_sends_each_command_to_its_own_pane() -> None:
    commands = build_tmux_commands(
        layout_config=_layout({"tabName": "dev", "arrangement": "columns", "panes": [_pane("a"), _pane("b")]}),
        session_name="demo",
        exit_mode="backToShell",
    )
    assert commands == [
        "tmux new-session -d -s demo -n dev -c /work",
        "tmux select-pane -t demo:dev -T a",
        "tmux send-keys -t demo:dev 'run a' C-m",
        "tmux split-window -t demo:dev -c /work",
        "tmux select-pane -t demo:dev -T b",
        "tmux send-keys -t demo:dev 'run b' C-m",
        "tmux select-layout -t demo:dev even-horizontal",
        "tmux select-pane -t 'demo:dev.{top-left}'",
        "tmux select-window -t demo:dev",
    ]


@pytest.mark.parametrize(
    ("arrangement", "tmux_layout"),
    [("columns", "even-horizontal"), ("rows", "even-vertical"), ("grid", "tiled"), (None, "tiled")],
)
def test_arrangement_selects_tmux_layout(arrangement: TabArrangement | None, tmux_layout: str) -> None:
    tab: TabConfig = {"tabName": "dev", "panes": [_pane("a"), _pane("b"), _pane("c")]}
    if arrangement is not None:
        tab["arrangement"] = arrangement
    commands = build_tmux_commands(layout_config=_layout(tab), session_name="demo", exit_mode="backToShell")
    assert f"tmux select-layout -t demo:dev {tmux_layout}" in commands
    assert len([command for command in commands if "split-window" in command]) == 2


def test_exit_mode_wraps_every_pane_command() -> None:
    plain_commands = build_tmux_commands(
        layout_config=_layout({"tabName": "dev", "panes": [_pane("a"), _pane("b")]}),
        session_name="demo",
        exit_mode="backToShell",
    )
    wrapped_commands = build_tmux_commands(
        layout_config=_layout({"tabName": "dev", "panes": [_pane("a"), _pane("b")]}),
        session_name="demo",
        exit_mode="killWindow",
    )
    plain_sends = [command for command in plain_commands if "send-keys" in command]
    wrapped_sends = [command for command in wrapped_commands if "send-keys" in command]
    assert len(wrapped_sends) == 2
    assert all(plain != wrapped and "run" in wrapped for plain, wrapped in zip(plain_sends, wrapped_sends, strict=True))


def test_tab_without_panes_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least one pane"):
        build_tmux_commands(layout_config=_layout({"tabName": "dev", "panes": []}), session_name="demo", exit_mode="backToShell")
