from collections.abc import Callable
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_iter_rich_output
from stackops.scripts.python.helpers.helpers_agents.agents_agentops_cache import AgentopsCacheCleanResult
from stackops.scripts.python.helpers.helpers_agents.agents_iter_models import (
    HerdrWorkspace,
    IterWorkspaceClose,
    IterWorkspaceClosePlan,
    IterWorkspaceStatus,
    TabId,
    WorkspaceId,
)


def _empty_close_plan(*, workspace_id: str, label: str, number: int, repo_root: Path) -> IterWorkspaceClosePlan:
    workspace = HerdrWorkspace(
        workspace_id=WorkspaceId(workspace_id),
        label=label,
        number=number,
        active_tab_id=TabId(f"{workspace_id}:t1"),
        agent_status="idle",
        focused=False,
        pane_count=0,
        tab_count=0,
    )
    return IterWorkspaceClosePlan(
        workspace=workspace, repo_root=repo_root, tabs=(), retained_tabs=(), protected_tabs=(), closable_tabs=(), retain_previous=3
    )


def test_close_all_passes_every_planned_workspace_to_bulk_closer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    close_plans = (
        _empty_close_plan(workspace_id="w1", label="iter-alpha", number=1, repo_root=tmp_path),
        _empty_close_plan(workspace_id="w2", label="iter-beta", number=2, repo_root=tmp_path),
    )
    closed_batches: list[tuple[IterWorkspaceClosePlan, ...]] = []

    def plan_closes(*, workspace_id: str | None, retain_previous: int) -> tuple[IterWorkspaceClosePlan, ...]:
        assert workspace_id is None
        assert retain_previous == 3
        return close_plans

    def close_planned(*, close_plans: tuple[IterWorkspaceClosePlan, ...], report: Callable[[str], None]) -> tuple[IterWorkspaceClose, ...]:
        report("checked")
        closed_batches.append(close_plans)
        return ()

    monkeypatch.setattr(agents_iter_rich_output, "plan_iter_workspace_closes", plan_closes)
    monkeypatch.setattr(agents_iter_rich_output, "close_iter_workspace_plans", close_planned)

    agents_iter_rich_output.show_close_iter_workspaces_loop(
        workspace_id=None, all_workspaces=True, interactive=False, continuous=False, retain_previous=3, dry_run=False, interval_seconds=300
    )

    assert closed_batches == [close_plans]


def test_interactive_status_selects_once_then_refreshes_selected_workspace(monkeypatch: pytest.MonkeyPatch) -> None:
    requested_workspace_ids: list[str | None] = []

    def load_statuses(*, workspace_id: str | None, retain_previous: int) -> tuple[IterWorkspaceStatus, ...]:
        assert retain_previous == 2
        requested_workspace_ids.append(workspace_id)
        return ()

    def choose_workspace(*, statuses: tuple[IterWorkspaceStatus, ...]) -> str:
        assert statuses == ()
        return "w1"

    monkeypatch.setattr(agents_iter_rich_output, "get_iter_workspace_statuses", load_statuses)
    monkeypatch.setattr(agents_iter_rich_output, "choose_iter_workspace_id", choose_workspace)

    agents_iter_rich_output.show_iter_status(workspace_id=None, all_workspaces=False, interactive=True, retain_previous=2)

    assert requested_workspace_ids == [None, "w1"]


def test_interactive_clean_inventories_then_cleans_selected_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clean_calls: list[tuple[WorkspaceId | None, bool]] = []
    empty_result = AgentopsCacheCleanResult(
        repo_root=tmp_path,
        iterations_path=tmp_path.joinpath(".ai", "agentops", "iterations"),
        removed_runs=(),
        protected_runs=(),
        unmanaged_entries=(),
        removed_entries=0,
        dry_run=True,
    )

    def clean_cache(
        *,
        cwd: Path,
        workspace_id: WorkspaceId | None,
        dry_run: bool,
        load_active_workspace_ids: Callable[[], frozenset[WorkspaceId]],
        report: Callable[[str], None],
    ) -> AgentopsCacheCleanResult:
        assert cwd == tmp_path
        assert load_active_workspace_ids() == frozenset()
        report("checked")
        clean_calls.append((workspace_id, dry_run))
        return empty_result

    def no_active_ids() -> frozenset[WorkspaceId]:
        return frozenset()

    def choose_run(*, result: AgentopsCacheCleanResult) -> WorkspaceId:
        assert result is empty_result
        return WorkspaceId("w9")

    monkeypatch.setattr(agents_iter_rich_output, "clean_agentops_cache", clean_cache)
    monkeypatch.setattr(agents_iter_rich_output, "load_active_workspace_ids", no_active_ids)
    monkeypatch.setattr(agents_iter_rich_output, "choose_agentops_cache_workspace_id", choose_run)

    agents_iter_rich_output.show_clean_agentops_cache(cwd=tmp_path, workspace_id=None, all_workspaces=False, interactive=True, dry_run=False)

    assert clean_calls == [(None, True), (WorkspaceId("w9"), False)]
