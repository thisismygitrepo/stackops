import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_iter_service
from stackops.scripts.python.helpers.helpers_agents.agents_iter_models import (
    HerdrPane,
    HerdrSnapshot,
    HerdrStatus,
    HerdrTab,
    HerdrWorkspace,
    IterWorkspaceClosePlan,
    PaneId,
    TabId,
    WorkspaceId,
)
from stackops.scripts.python.helpers.helpers_agents.agents_iter_plan import build_workspace_close_plan


def _snapshot(
    *, iterations: tuple[int, ...], statuses: dict[int, HerdrStatus], active_iteration: int
) -> HerdrSnapshot:
    workspace_id = WorkspaceId("w1")
    tabs = tuple(
        HerdrTab(
            tab_id=TabId(f"w1:t{iteration}"),
            workspace_id=workspace_id,
            label=f"iter-alpha-{iteration:03d}",
            number=index,
            agent_status=statuses[iteration],
            focused=iteration == active_iteration,
            pane_count=1,
        )
        for index, iteration in enumerate(iterations, start=1)
    )
    panes = tuple(
        HerdrPane(
            pane_id=PaneId(f"w1:p{iteration}"),
            workspace_id=workspace_id,
            tab_id=TabId(f"w1:t{iteration}"),
            agent_status=statuses[iteration],
            agent="codex",
            label=f"iter-alpha-{iteration:03d}",
        )
        for iteration in iterations
    )
    workspace = HerdrWorkspace(
        workspace_id=workspace_id,
        label="iter-alpha",
        number=1,
        active_tab_id=TabId(f"w1:t{active_iteration}"),
        agent_status=statuses[active_iteration],
        focused=True,
        pane_count=len(panes),
        tab_count=len(tabs),
    )
    return HerdrSnapshot(workspaces=(workspace,), tabs=tabs, panes=panes, agents=())


def _plan(*, snapshot: HerdrSnapshot, retain_previous: int) -> IterWorkspaceClosePlan:
    return build_workspace_close_plan(
        snapshot=snapshot,
        workspace=snapshot.workspaces[0],
        retain_previous=retain_previous,
    )


def test_close_revalidates_and_skips_tab_that_became_working(monkeypatch: pytest.MonkeyPatch) -> None:
    initial = _snapshot(iterations=(1, 2), statuses={1: "done", 2: "done"}, active_iteration=2)
    changed = _snapshot(iterations=(1, 2), statuses={1: "working", 2: "done"}, active_iteration=2)
    close_calls: list[TabId] = []
    monkeypatch.setattr(agents_iter_service, "capture_herdr_snapshot", lambda: changed)
    monkeypatch.setattr(agents_iter_service, "close_tab", lambda *, tab_id: close_calls.append(tab_id))

    results = agents_iter_service.close_iter_workspace_plans(
        close_plans=(_plan(snapshot=initial, retain_previous=0),),
        report=lambda _message: None,
    )

    assert close_calls == []
    assert [(item.tab.label, item.reason) for item in results[0].skipped_tabs] == [
        ("iter-alpha-001", "state_changed")
    ]
    assert results[0].failed_tabs == ()


def test_close_continues_after_failure_and_verifies_success(monkeypatch: pytest.MonkeyPatch) -> None:
    initial = _snapshot(iterations=(1, 2, 3), statuses={1: "done", 2: "done", 3: "done"}, active_iteration=3)
    present = {1, 2, 3}
    close_calls: list[TabId] = []

    def current_snapshot() -> HerdrSnapshot:
        iterations = tuple(iteration for iteration in (1, 2, 3) if iteration in present)
        return _snapshot(
            iterations=iterations,
            statuses={iteration: "done" for iteration in iterations},
            active_iteration=3,
        )

    def fake_close_tab(*, tab_id: TabId) -> None:
        close_calls.append(tab_id)
        iteration = int(str(tab_id).removeprefix("w1:t"))
        if iteration == 1:
            raise RuntimeError("close refused")
        present.remove(iteration)

    monkeypatch.setattr(agents_iter_service, "capture_herdr_snapshot", current_snapshot)
    monkeypatch.setattr(agents_iter_service, "close_tab", fake_close_tab)
    monkeypatch.setattr(agents_iter_service, "list_tabs", lambda: current_snapshot().tabs)

    results = agents_iter_service.close_iter_workspace_plans(
        close_plans=(_plan(snapshot=initial, retain_previous=0),),
        report=lambda _message: None,
    )

    assert close_calls == [TabId("w1:t1"), TabId("w1:t2")]
    assert [item.tab.label for item in results[0].failed_tabs] == ["iter-alpha-001"]
    assert [tab.label for tab in results[0].closed_tabs] == ["iter-alpha-002"]


def test_close_treats_concurrently_removed_tab_as_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    initial = _snapshot(iterations=(1, 2), statuses={1: "done", 2: "done"}, active_iteration=2)
    current = _snapshot(iterations=(2,), statuses={2: "done"}, active_iteration=2)
    monkeypatch.setattr(agents_iter_service, "capture_herdr_snapshot", lambda: current)

    results = agents_iter_service.close_iter_workspace_plans(
        close_plans=(_plan(snapshot=initial, retain_previous=0),),
        report=lambda _message: None,
    )

    assert [tab.label for tab in results[0].already_absent_tabs] == ["iter-alpha-001"]
    assert results[0].failed_tabs == ()


def test_close_error_is_idempotent_when_verification_shows_absence(monkeypatch: pytest.MonkeyPatch) -> None:
    initial = _snapshot(iterations=(1, 2), statuses={1: "done", 2: "done"}, active_iteration=2)
    current = _snapshot(iterations=(1, 2), statuses={1: "done", 2: "done"}, active_iteration=2)

    def fail_close(*, tab_id: TabId) -> None:
        raise RuntimeError(f"Tab {tab_id} was not found.")

    monkeypatch.setattr(agents_iter_service, "capture_herdr_snapshot", lambda: current)
    monkeypatch.setattr(agents_iter_service, "close_tab", fail_close)
    monkeypatch.setattr(agents_iter_service, "list_tabs", lambda: tuple(tab for tab in current.tabs if tab.label.endswith("002")))

    results = agents_iter_service.close_iter_workspace_plans(
        close_plans=(_plan(snapshot=initial, retain_previous=0),),
        report=lambda _message: None,
    )

    assert [tab.label for tab in results[0].already_absent_tabs] == ["iter-alpha-001"]
    assert results[0].failed_tabs == ()


def test_track_uses_pinned_workspace_and_verifies_budget_close(monkeypatch: pytest.MonkeyPatch) -> None:
    snapshot = _snapshot(iterations=(100, 101), statuses={100: "done", 101: "working"}, active_iteration=101)
    close_calls: list[WorkspaceId] = []
    monkeypatch.setattr(agents_iter_service, "capture_herdr_snapshot", lambda: snapshot)
    monkeypatch.setattr(agents_iter_service, "close_workspace", lambda *, workspace_id: close_calls.append(workspace_id))
    monkeypatch.setattr(agents_iter_service, "list_workspaces", lambda: ())

    check = agents_iter_service.track_iter_workspace_once(
        workspace_id=WorkspaceId("w1"),
        max_iterations=100,
        retain_previous=3,
        report=lambda _message: None,
    )

    assert close_calls == [WorkspaceId("w1")]
    assert check.track_result.phase == "closed"
    assert check.track_result.latest_iteration == 101
    assert check.close_result is None


def test_track_treats_externally_closed_workspace_as_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        agents_iter_service,
        "capture_herdr_snapshot",
        lambda: HerdrSnapshot(workspaces=(), tabs=(), panes=(), agents=()),
    )

    check = agents_iter_service.track_iter_workspace_once(
        workspace_id=WorkspaceId("w1"),
        max_iterations=100,
        retain_previous=3,
        report=lambda _message: None,
    )

    assert check.status is None
    assert check.track_result.phase == "closed"
    assert check.track_result.workspace is None
