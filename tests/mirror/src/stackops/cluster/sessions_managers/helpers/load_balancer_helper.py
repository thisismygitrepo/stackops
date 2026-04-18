from __future__ import annotations

from stackops.cluster.sessions_managers.helpers.load_balancer_helper import (
    combine_tabs_by_weight_into_super_tabs,
    combine_tabs_into_super_tabs,
    restrict_num_tabs_helper1,
    restrict_num_tabs_helper4,
    split_tabs_by_weight,
)
from stackops.utils.schemas.layouts.layout_types import LayoutConfig, TabConfig


def _tab(name: str, weight: int) -> TabConfig:
    return {
        "tabName": name,
        "startDir": "/tmp",
        "command": f"run {name}",
        "tabWeight": weight,
    }


def test_split_tabs_by_weight_starts_new_chunk_after_limit() -> None:
    tabs = [_tab("a", 2), _tab("b", 1), _tab("c", 2)]

    result = split_tabs_by_weight(tabs=tabs, max_weight=3)

    assert [[tab["tabName"] for tab in chunk] for chunk in result] == [["a", "b"], ["c"]]


def test_combine_tabs_into_super_tabs_merges_commands_and_weights() -> None:
    tabs = [_tab("a", 1), _tab("b", 2), _tab("c", 1), _tab("d", 1)]

    result = combine_tabs_into_super_tabs(tabs=tabs, num_super_tabs=2)

    assert [tab["tabName"] for tab in result] == ["super_tab_1", "super_tab_2"]
    assert result[0]["command"] == "run a; run b"
    assert result[0].get("tabWeight") == 3
    assert result[1]["command"] == "run c; run d"


def test_restrict_num_tabs_helper1_splits_large_layout_into_parts() -> None:
    layout: LayoutConfig = {
        "layoutName": "demo",
        "layoutTabs": [_tab("a", 1), _tab("b", 1), _tab("c", 1)],
    }

    result = restrict_num_tabs_helper1(
        layout_configs=[layout],
        max_thresh=2,
        threshold_type="number",
        breaking_method="moreLayouts",
    )

    assert [item["layoutName"] for item in result] == ["demo_part1", "demo_part2"]
    assert [[tab["tabName"] for tab in item["layoutTabs"]] for item in result] == [["a", "b"], ["c"]]


def test_restrict_num_tabs_helper4_combines_weighted_tabs() -> None:
    layout: LayoutConfig = {
        "layoutName": "weighted",
        "layoutTabs": [_tab("a", 2), _tab("b", 1), _tab("c", 2)],
    }

    result = restrict_num_tabs_helper4(
        layout_configs=[layout],
        max_thresh=3,
        threshold_type="weight",
        breaking_method="combineTabs",
    )

    assert [item["layoutName"] for item in result] == ["weighted"]
    combined_tabs = result[0]["layoutTabs"]
    assert [tab["tabName"] for tab in combined_tabs] == ["super_tab_1", "c"]
    assert combined_tabs[0]["command"] == "run a; run b"
    assert combined_tabs[0].get("tabWeight") == 3
    assert combine_tabs_by_weight_into_super_tabs(tabs=layout["layoutTabs"], max_weight=3) == combined_tabs
