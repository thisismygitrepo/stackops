import sys
from types import ModuleType
from typing import Literal

import pytest

from stackops.cluster.sessions_managers.utils import load_balancer
from stackops.utils.schemas.layouts.layout_types import LayoutConfig


type ThresholdType = Literal["number", "weight"]
type BreakingMethod = Literal["moreLayouts", "combineTabs"]


def _layout() -> LayoutConfig:
    return {
        "layoutName": "demo",
        "layoutTabs": [
            {"tabName": "one", "startDir": "/work/app", "command": "run one", "tabWeight": 3},
            {"tabName": "two", "startDir": "/work/app", "command": "run two", "tabWeight": 1},
        ],
    }


def test_limit_tab_num_dispatches_to_matching_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cases: list[tuple[ThresholdType, BreakingMethod]] = [
        ("number", "moreLayouts"),
        ("number", "combineTabs"),
        ("weight", "moreLayouts"),
        ("weight", "combineTabs"),
    ]

    for threshold_type, breaking_method in cases:
        calls: list[str] = []

        def fake_helper(
            layout_configs: list[LayoutConfig],
            max_thresh: int,
            threshold_type: ThresholdType,
            breaking_method: BreakingMethod,
        ) -> list[LayoutConfig]:
            assert layout_configs == [_layout()]
            assert max_thresh == 2
            calls.append(f"{threshold_type}:{breaking_method}")
            return layout_configs

        monkeypatch.setattr(load_balancer, "restrict_num_tabs_helper1", fake_helper)
        monkeypatch.setattr(load_balancer, "restrict_num_tabs_helper2", fake_helper)
        monkeypatch.setattr(load_balancer, "restrict_num_tabs_helper3", fake_helper)
        monkeypatch.setattr(load_balancer, "restrict_num_tabs_helper4", fake_helper)

        result = load_balancer.limit_tab_num(
            layout_configs=[_layout()],
            max_thresh=2,
            threshold_type=threshold_type,
            breaking_method=breaking_method,
        )

        assert result == [_layout()]
        assert calls == [f"{threshold_type}:{breaking_method}"]


def test_limit_tab_weight_splits_only_overweight_tabs() -> None:
    split_calls: list[tuple[str, int]] = []

    def split_command(command: str, to: int) -> list[str]:
        split_calls.append((command, to))
        return ["run one --part 1", "run one --part 2", "run one --part 3"]

    result = load_balancer.limit_tab_weight(
        layout_configs=[_layout()],
        max_weight=1,
        command_splitter=split_command,
    )

    assert split_calls == [("run one", 1)]
    assert result == [
        {
            "layoutName": "demo",
            "layoutTabs": [
                {
                    "tabName": "one_part1",
                    "startDir": "/work/app",
                    "command": "run one --part 1",
                    "tabWeight": 1,
                },
                {
                    "tabName": "one_part2",
                    "startDir": "/work/app",
                    "command": "run one --part 2",
                    "tabWeight": 1,
                },
                {
                    "tabName": "one_part3",
                    "startDir": "/work/app",
                    "command": "run one --part 3",
                    "tabWeight": 1,
                },
                {
                    "tabName": "two",
                    "startDir": "/work/app",
                    "command": "run two",
                    "tabWeight": 1,
                },
            ],
        }
    ]


def test_run_executes_manager_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lifecycle: list[str] = []

    class FakeManager:
        def __init__(self, session_layouts: list[LayoutConfig]) -> None:
            assert session_layouts == [_layout()]
            lifecycle.append("init")

        def start_all_sessions(
            self,
            on_conflict: str,
            poll_interval: int,
            poll_seconds: int,
        ) -> None:
            assert on_conflict == "error"
            assert poll_interval == 2
            assert poll_seconds == 2
            lifecycle.append("start")

        def run_monitoring_routine(self, wait_ms: int) -> None:
            assert wait_ms == 2000
            lifecycle.append("monitor")

        def kill_all_sessions(self) -> None:
            lifecycle.append("kill")

    fake_module = ModuleType("zellij_local_manager")
    setattr(fake_module, "ZellijLocalManager", FakeManager)
    monkeypatch.setitem(
        sys.modules,
        "stackops.cluster.sessions_managers.zellij.zellij_local_manager",
        fake_module,
    )

    load_balancer.run(layouts=[_layout()], on_conflict="error")

    assert lifecycle == ["init", "start", "monitor", "kill"]
