import pytest

from stackops.cluster.sessions_managers.helpers.load_balancer_helper import combine_tabs_into_super_tabs
from stackops.utils.schemas.layouts.layout_types import TabConfig, single_pane_tab


def test_combining_single_pane_tabs_joins_their_commands_in_one_pane() -> None:
    tabs: list[TabConfig] = [
        {**single_pane_tab(tab_name="one", start_dir="/work", command="echo 1"), "tabWeight": 2},
        {**single_pane_tab(tab_name="two", start_dir="/other", command="echo 2"), "tabWeight": 3},
    ]
    assert combine_tabs_into_super_tabs(tabs, num_super_tabs=1) == [
        {
            "tabName": "super_tab_1",
            "panes": [{"paneName": "super_tab_1", "startDir": "/work", "command": "echo 1; echo 2"}],
            "tabWeight": 5,
        }
    ]


def test_combining_multi_pane_tabs_is_rejected() -> None:
    multi_pane_tab: TabConfig = {
        "tabName": "dev",
        "panes": [
            {"paneName": "a", "startDir": "/work", "command": "echo a"},
            {"paneName": "b", "startDir": "/work", "command": "echo b"},
        ],
    }
    with pytest.raises(ValueError, match="needs single-pane tabs"):
        combine_tabs_into_super_tabs([multi_pane_tab, single_pane_tab(tab_name="x", start_dir="/work", command="echo x")], num_super_tabs=1)
