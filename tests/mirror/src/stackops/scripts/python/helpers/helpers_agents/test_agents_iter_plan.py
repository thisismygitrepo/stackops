import json
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_iter_records, agents_iter_service
from stackops.scripts.python.helpers.helpers_agents.agents_iter_herdr import HerdrApiError
from stackops.scripts.python.helpers.helpers_agents.agents_iter_models import (
    HerdrAgent,
    HerdrPane,
    HerdrSnapshot,
    HerdrStatus,
    HerdrTab,
    HerdrWorkspace,
    PaneId,
    TabId,
    TerminalId,
    WorkspaceId,
)
from stackops.scripts.python.helpers.helpers_agents.agents_iter_plan import build_workspace_close_plan
from stackops.scripts.python.helpers.helpers_agents.agents_iter_records import IterationHandoff
from stackops.scripts.python.helpers.helpers_agents.agents_iter_workspace_records import IterWorkspaceRecords


_RUN_PATH = Path("/repo/.ai/agentops/iterations/alpha")


def _snapshot(*, source_status: HerdrStatus, include_unmanaged_tab: bool) -> tuple[HerdrSnapshot, HerdrWorkspace]:
    workspace_id = WorkspaceId("w1")
    iteration_tabs = (
        HerdrTab(TabId("w1:t1"), workspace_id, "iter-alpha-001", 1, source_status, False, 1),
        HerdrTab(TabId("w1:t2"), workspace_id, "iter-alpha-002", 2, "idle", True, 1),
    )
    unmanaged_tabs = (HerdrTab(TabId("w1:t3"), workspace_id, "iter-alpha-tracker", 3, "idle", False, 1),) if include_unmanaged_tab else ()
    tabs = (*iteration_tabs, *unmanaged_tabs)
    panes = tuple(
        HerdrPane(
            pane_id=PaneId(f"w1:p{tab.number}"),
            terminal_id=TerminalId(f"term_{tab.number}"),
            workspace_id=workspace_id,
            tab_id=tab.tab_id,
            agent_status=tab.agent_status,
            revision=20,
        )
        for tab in tabs
    )
    agents = tuple(
        HerdrAgent(
            terminal_id=TerminalId(f"term_{tab.number}"),
            agent="codex",
            agent_status=tab.agent_status,
            workspace_id=workspace_id,
            tab_id=tab.tab_id,
            pane_id=PaneId(f"w1:p{tab.number}"),
            cwd="/repo",
            foreground_cwd="/repo",
            focused=tab.focused,
            name=tab.label,
            display_agent=None,
            revision=20,
        )
        for tab in iteration_tabs
    )
    workspace = HerdrWorkspace(
        workspace_id=workspace_id,
        label="iter-alpha",
        number=1,
        active_tab_id=iteration_tabs[1].tab_id,
        agent_status="idle",
        focused=True,
        pane_count=len(panes),
        tab_count=len(tabs),
    )
    return HerdrSnapshot(workspaces=(workspace,), tabs=tabs, panes=panes, agents=agents), workspace


def _handoff(*, accepted_revision: int) -> IterationHandoff:
    return IterationHandoff(
        herdr_session="default",
        workspace_id=WorkspaceId("w1"),
        source_iteration=1,
        source_tab_id=TabId("w1:t1"),
        successor_iteration=2,
        successor_tab_id=TabId("w1:t2"),
        successor_pane_id=PaneId("w1:p2"),
        successor_terminal_id=TerminalId("term_2"),
        successor_agent_name="iter-alpha-002",
        accepted_revision=accepted_revision,
    )


def test_idle_or_done_without_current_handoff_is_never_closable() -> None:
    for source_status in ("idle", "done"):
        snapshot, workspace = _snapshot(source_status=source_status, include_unmanaged_tab=False)

        plan = build_workspace_close_plan(snapshot=snapshot, workspace=workspace, run_path=_RUN_PATH, retain_previous=0, handoffs={})

        assert plan.closable_tabs == ()
        assert [(item.tab.tab_id, item.reason) for item in plan.protected_tabs] == [(TabId("w1:t1"), "handoff_unverified")]


def test_current_handoff_and_quiet_source_authorize_close() -> None:
    snapshot, workspace = _snapshot(source_status="done", include_unmanaged_tab=False)

    plan = build_workspace_close_plan(
        snapshot=snapshot, workspace=workspace, run_path=_RUN_PATH, retain_previous=0, handoffs={1: _handoff(accepted_revision=10)}
    )

    assert [tab.tab_id for tab in plan.closable_tabs] == [TabId("w1:t1")]
    assert [tab.tab_id for tab in plan.retained_tabs] == [TabId("w1:t2")]


def test_all_workspace_planning_uses_one_snapshot_and_excludes_non_iter_workspaces(monkeypatch: pytest.MonkeyPatch) -> None:
    snapshot, workspace = _snapshot(source_status="done", include_unmanaged_tab=False)
    non_iter_workspace = HerdrWorkspace(
        workspace_id=WorkspaceId("w2"),
        label="notes",
        number=0,
        active_tab_id=TabId("w2:t1"),
        agent_status="idle",
        focused=False,
        pane_count=0,
        tab_count=0,
    )
    combined_snapshot = HerdrSnapshot(
        workspaces=(non_iter_workspace, *snapshot.workspaces), tabs=snapshot.tabs, panes=snapshot.panes, agents=snapshot.agents
    )
    snapshot_calls = 0
    loaded_labels: list[str] = []

    def current_snapshot() -> HerdrSnapshot:
        nonlocal snapshot_calls
        snapshot_calls += 1
        return combined_snapshot

    def current_records(*, snapshot: HerdrSnapshot, workspace: HerdrWorkspace) -> IterWorkspaceRecords:
        assert snapshot is combined_snapshot
        loaded_labels.append(workspace.label)
        return IterWorkspaceRecords(run_path=_RUN_PATH, handoffs={1: _handoff(accepted_revision=10)})

    monkeypatch.setattr(agents_iter_service, "capture_herdr_snapshot", current_snapshot)
    monkeypatch.setattr(agents_iter_service, "load_iter_workspace_records", current_records)

    plans = agents_iter_service.plan_iter_workspace_closes(workspace_id=None, retain_previous=0)

    assert snapshot_calls == 1
    assert loaded_labels == ["iter-alpha"]
    assert tuple(plan.workspace for plan in plans) == (workspace,)
    assert tuple(tab.tab_id for tab in plans[0].closable_tabs) == (TabId("w1:t1"),)


def test_status_for_explicit_workspace_loads_only_its_handoffs(monkeypatch: pytest.MonkeyPatch) -> None:
    snapshot, workspace = _snapshot(source_status="done", include_unmanaged_tab=False)
    loaded_labels: list[str] = []

    def current_snapshot() -> HerdrSnapshot:
        return snapshot

    def current_records(*, snapshot: HerdrSnapshot, workspace: HerdrWorkspace) -> IterWorkspaceRecords:
        loaded_labels.append(workspace.label)
        return IterWorkspaceRecords(run_path=_RUN_PATH, handoffs={1: _handoff(accepted_revision=10)})

    monkeypatch.setattr(agents_iter_service, "capture_herdr_snapshot", current_snapshot)
    monkeypatch.setattr(agents_iter_service, "load_iter_workspace_records", current_records)

    statuses = agents_iter_service.get_iter_workspace_statuses(workspace_id="w1", retain_previous=0)

    assert loaded_labels == ["iter-alpha"]
    assert tuple(status.workspace for status in statuses) == (workspace,)
    assert tuple(tab.tab_id for tab in statuses[0].plan.closable_tabs) == (TabId("w1:t1"),)


@pytest.mark.parametrize("source_status", ("working", "blocked", "unknown"))
def test_live_source_status_vetoes_handoff(source_status: HerdrStatus) -> None:
    snapshot, workspace = _snapshot(source_status=source_status, include_unmanaged_tab=False)

    plan = build_workspace_close_plan(
        snapshot=snapshot, workspace=workspace, run_path=_RUN_PATH, retain_previous=0, handoffs={1: _handoff(accepted_revision=10)}
    )

    assert plan.closable_tabs == ()
    assert any(item.tab.tab_id == TabId("w1:t1") and item.reason == "active" for item in plan.protected_tabs)


def test_stale_revision_and_legacy_tracker_are_rejected() -> None:
    snapshot, workspace = _snapshot(source_status="done", include_unmanaged_tab=False)
    stale_plan = build_workspace_close_plan(
        snapshot=snapshot, workspace=workspace, run_path=_RUN_PATH, retain_previous=0, handoffs={1: _handoff(accepted_revision=21)}
    )
    assert [(item.tab.tab_id, item.reason) for item in stale_plan.protected_tabs] == [(TabId("w1:t1"), "handoff_unverified")]

    legacy_snapshot, legacy_workspace = _snapshot(source_status="done", include_unmanaged_tab=True)
    legacy_plan = build_workspace_close_plan(
        snapshot=legacy_snapshot, workspace=legacy_workspace, run_path=_RUN_PATH, retain_previous=0, handoffs={1: _handoff(accepted_revision=10)}
    )
    assert legacy_plan.closable_tabs == ()
    assert {item.reason for item in legacy_plan.protected_tabs} == {"incomplete_snapshot", "unmanaged"}


def test_current_handoff_file_is_strictly_parsed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HERDR_SESSION", raising=False)
    run_path = tmp_path.joinpath(".ai", "agentops", "iterations", "alpha", "iter-001")
    run_path.mkdir(parents=True)
    run_path.parent.joinpath("run.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "herdr_session": "default",
                "workspace_id": "w1",
                "workspace_label": "iter-alpha",
            }
        ),
        encoding="utf-8",
    )
    receipt = {
        "schema_version": 1,
        "herdr_session": "default",
        "workspace_id": "w1",
        "source_iteration": 1,
        "source_tab_id": "w1:t1",
        "successor_iteration": 2,
        "successor_tab_id": "w1:t2",
        "successor_pane_id": "w1:p2",
        "successor_terminal_id": "term_2",
        "successor_agent_name": "iter-alpha-002",
        "accepted_revision": 10,
    }
    run_path.joinpath("handoff.json").write_text(json.dumps(receipt), encoding="utf-8")

    handoffs = agents_iter_records.load_iteration_handoffs(run_path=run_path.parent, workspace_id=WorkspaceId("w1"), workspace_label="iter-alpha")

    assert handoffs == {1: _handoff(accepted_revision=10)}
    with pytest.raises(RuntimeError, match="manifest workspace ID"):
        agents_iter_records.load_iteration_handoffs(
            run_path=run_path.parent, workspace_id=WorkspaceId("wrong-workspace"), workspace_label="iter-alpha"
        )


def test_close_revalidates_once_and_accepts_only_tab_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    snapshot, workspace = _snapshot(source_status="done", include_unmanaged_tab=False)
    handoffs = {1: _handoff(accepted_revision=10)}
    close_plan = build_workspace_close_plan(snapshot=snapshot, workspace=workspace, run_path=_RUN_PATH, retain_previous=0, handoffs=handoffs)
    snapshot_calls = 0

    def current_snapshot() -> HerdrSnapshot:
        nonlocal snapshot_calls
        snapshot_calls += 1
        return snapshot

    def current_records(*, snapshot: HerdrSnapshot, workspace: HerdrWorkspace) -> IterWorkspaceRecords:
        return IterWorkspaceRecords(run_path=_RUN_PATH, handoffs=handoffs)

    def concurrently_absent(*, tab_id: TabId) -> None:
        raise HerdrApiError(code="tab_not_found", message=f"{tab_id} is gone")

    monkeypatch.setattr(agents_iter_service, "capture_herdr_snapshot", current_snapshot)
    monkeypatch.setattr(agents_iter_service, "load_iter_workspace_records", current_records)
    monkeypatch.setattr(agents_iter_service, "close_tab", concurrently_absent)

    result = agents_iter_service.close_iter_workspace_plan(close_plan=close_plan, report=lambda _message: None)

    assert snapshot_calls == 1
    assert [tab.tab_id for tab in result.already_absent_tabs] == [TabId("w1:t1")]
    assert result.closed_tabs == ()
    assert result.failed_tabs == ()


def test_close_skips_candidate_when_workspace_run_path_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    snapshot, workspace = _snapshot(source_status="done", include_unmanaged_tab=False)
    handoffs = {1: _handoff(accepted_revision=10)}
    close_plan = build_workspace_close_plan(snapshot=snapshot, workspace=workspace, run_path=_RUN_PATH, retain_previous=0, handoffs=handoffs)
    close_calls: list[TabId] = []

    def current_snapshot() -> HerdrSnapshot:
        return snapshot

    def moved_records(*, snapshot: HerdrSnapshot, workspace: HerdrWorkspace) -> IterWorkspaceRecords:
        assert len(snapshot.workspaces) == 1
        assert workspace.workspace_id == WorkspaceId("w1")
        return IterWorkspaceRecords(run_path=Path("/other-project/.ai/agentops/iterations/alpha"), handoffs=handoffs)

    def capture_close(*, tab_id: TabId) -> None:
        close_calls.append(tab_id)

    monkeypatch.setattr(agents_iter_service, "capture_herdr_snapshot", current_snapshot)
    monkeypatch.setattr(agents_iter_service, "load_iter_workspace_records", moved_records)
    monkeypatch.setattr(agents_iter_service, "close_tab", capture_close)

    result = agents_iter_service.close_iter_workspace_plan(close_plan=close_plan, report=lambda _message: None)

    assert [(item.tab.tab_id, item.reason) for item in result.skipped_tabs] == [(TabId("w1:t1"), "state_changed")]
    assert result.closed_tabs == ()
    assert result.failed_tabs == ()
    assert close_calls == []
