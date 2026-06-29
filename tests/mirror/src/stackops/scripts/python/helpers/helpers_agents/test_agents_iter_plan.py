import pytest

from stackops.scripts.python.helpers.helpers_agents.agents_iter_models import (
    HerdrAgent,
    HerdrPane,
    HerdrSnapshot,
    HerdrTab,
    HerdrWorkspace,
    PaneId,
    TabId,
    WorkspaceId,
)
from stackops.scripts.python.helpers.helpers_agents.agents_iter_plan import (
    build_iter_workspace_status,
    build_workspace_close_plan,
    iter_workspace_labels,
    resolve_iter_workspace,
    select_iter_workspace_close_plans,
)


def _complete_snapshot(*, workspace: HerdrWorkspace, tabs: tuple[HerdrTab, ...], agents: tuple[HerdrAgent, ...]) -> HerdrSnapshot:
    panes = tuple(HerdrPane(PaneId(f"{tab.tab_id}:p"), workspace.workspace_id, tab.tab_id, tab.agent_status, None, None) for tab in tabs)
    return HerdrSnapshot(workspaces=(workspace,), tabs=tabs, panes=panes, agents=agents)


def test_close_plan_retains_latest_and_three_previous_contiguous_iterations() -> None:
    workspace_id = WorkspaceId("w1")
    tracker = HerdrTab(TabId("tracker"), workspace_id, "iter-alpha-tracker", 1, "idle", False, 1)
    iteration_tabs = tuple(
        HerdrTab(TabId(f"tab-{iteration}"), workspace_id, f"iter-alpha-{iteration:03d}", iteration + 1, "done", False, 1) for iteration in range(1, 7)
    )
    tabs = (tracker, *iteration_tabs)
    workspace = HerdrWorkspace(workspace_id, "iter-alpha", 1, tracker.tab_id, "idle", False, len(tabs), len(tabs))
    snapshot = _complete_snapshot(workspace=workspace, tabs=tabs, agents=())

    plan = build_workspace_close_plan(snapshot=snapshot, workspace=workspace, retain_previous=3)

    assert [tab.label for tab in plan.retained_tabs] == ["iter-alpha-003", "iter-alpha-004", "iter-alpha-005", "iter-alpha-006"]
    assert [(item.tab.label, item.reason) for item in plan.protected_tabs] == [("iter-alpha-tracker", "tracker")]
    assert [tab.label for tab in plan.closable_tabs] == ["iter-alpha-001", "iter-alpha-002"]


def test_close_plan_parses_four_digit_iteration_and_protects_cross_slug_and_zero() -> None:
    workspace_id = WorkspaceId("w1")
    tabs = (
        HerdrTab(TabId("tracker"), workspace_id, "iter-alpha-tracker", 1, "idle", False, 1),
        HerdrTab(TabId("old"), workspace_id, "iter-alpha-999", 2, "done", False, 1),
        HerdrTab(TabId("latest"), workspace_id, "iter-alpha-1000", 3, "done", False, 1),
        HerdrTab(TabId("foreign"), workspace_id, "iter-beta-9000", 4, "done", False, 1),
        HerdrTab(TabId("zero"), workspace_id, "iter-alpha-000", 5, "done", False, 1),
    )
    workspace = HerdrWorkspace(workspace_id, "iter-alpha", 1, tabs[0].tab_id, "idle", False, 5, 5)
    snapshot = _complete_snapshot(workspace=workspace, tabs=tabs, agents=())

    status = build_iter_workspace_status(snapshot=snapshot, workspace=workspace, retain_previous=0)

    assert status.latest_iteration == 1000
    assert [tab.label for tab in status.plan.retained_tabs] == ["iter-alpha-1000"]
    assert [tab.label for tab in status.plan.closable_tabs] == ["iter-alpha-999"]
    assert [(item.tab.label, item.reason) for item in status.plan.protected_tabs] == [
        ("iter-alpha-tracker", "tracker"),
        ("iter-beta-9000", "unmanaged"),
        ("iter-alpha-000", "unmanaged"),
    ]


def test_stale_high_agent_and_older_live_agent_never_become_latest() -> None:
    workspace_id = WorkspaceId("w1")
    tracker = HerdrTab(TabId("tracker"), workspace_id, "iter-alpha-tracker", 1, "idle", False, 1)
    iteration_tabs = tuple(
        HerdrTab(TabId(f"tab-{iteration}"), workspace_id, f"iter-alpha-{iteration:03d}", iteration + 1, "done", False, 1) for iteration in range(1, 5)
    )
    tabs = (tracker, *iteration_tabs)
    workspace = HerdrWorkspace(workspace_id, "iter-alpha", 1, tracker.tab_id, "idle", False, len(tabs), len(tabs))
    older_agent = HerdrAgent(
        "codex", "idle", workspace_id, iteration_tabs[2].tab_id, PaneId(f"{iteration_tabs[2].tab_id}:p"), "/repo", "/repo", False, "iter-alpha-003"
    )
    stale_agent = HerdrAgent("codex", "idle", workspace_id, TabId("missing"), PaneId("missing"), "/repo", "/repo", False, "iter-alpha-999")
    snapshot = _complete_snapshot(workspace=workspace, tabs=tabs, agents=(older_agent, stale_agent))

    status = build_iter_workspace_status(snapshot=snapshot, workspace=workspace, retain_previous=1)

    assert status.latest_iteration == 4
    assert status.latest_agent is None
    assert status.latest_agent_tab is None
    assert [tab.label for tab in status.plan.retained_tabs] == ["iter-alpha-003", "iter-alpha-004"]
    assert [tab.label for tab in status.plan.closable_tabs] == ["iter-alpha-001", "iter-alpha-002"]


def test_incomplete_pane_inventory_fails_closed() -> None:
    workspace_id = WorkspaceId("w1")
    tracker = HerdrTab(TabId("tracker"), workspace_id, "iter-alpha-tracker", 1, "idle", False, 1)
    iteration = HerdrTab(TabId("iteration"), workspace_id, "iter-alpha-001", 2, "done", False, 1)
    workspace = HerdrWorkspace(workspace_id, "iter-alpha", 1, tracker.tab_id, "idle", False, 2, 2)
    tracker_pane = HerdrPane(PaneId("tracker:p"), workspace_id, tracker.tab_id, "idle", None, None)
    snapshot = HerdrSnapshot(workspaces=(workspace,), tabs=(tracker, iteration), panes=(tracker_pane,), agents=())

    plan = build_workspace_close_plan(snapshot=snapshot, workspace=workspace, retain_previous=0)

    assert plan.retained_tabs == ()
    assert plan.closable_tabs == ()
    assert [(item.tab.tab_id, item.reason) for item in plan.protected_tabs] == [
        (tracker.tab_id, "incomplete_snapshot"),
        (iteration.tab_id, "incomplete_snapshot"),
    ]


def test_active_iteration_protects_smallest_higher_iteration_as_successor() -> None:
    workspace_id = WorkspaceId("w1")
    tracker = HerdrTab(TabId("tracker"), workspace_id, "iter-alpha-tracker", 1, "idle", False, 1)
    old = HerdrTab(TabId("old"), workspace_id, "iter-alpha-001", 3, "done", False, 1)
    successor = HerdrTab(TabId("successor"), workspace_id, "iter-alpha-005", 2, "idle", False, 1)
    source = HerdrTab(TabId("source"), workspace_id, "iter-alpha-003", 5, "working", False, 1)
    latest = HerdrTab(TabId("latest"), workspace_id, "iter-alpha-006", 6, "idle", False, 1)
    tabs = (tracker, successor, old, source, latest)
    workspace = HerdrWorkspace(workspace_id, "iter-alpha", 1, tracker.tab_id, "working", False, 5, 5)
    latest_agent = HerdrAgent("codex", "idle", workspace_id, latest.tab_id, PaneId(f"{latest.tab_id}:p"), "/repo", "/repo", False, latest.label)
    snapshot = _complete_snapshot(workspace=workspace, tabs=tabs, agents=(latest_agent,))

    status = build_iter_workspace_status(snapshot=snapshot, workspace=workspace, retain_previous=0)

    protected = {item.tab.tab_id: item.reason for item in status.plan.protected_tabs}
    assert protected[source.tab_id] == "active"
    assert protected[successor.tab_id] == "launch_successor"
    assert status.plan.retained_tabs == (latest,)
    assert status.plan.closable_tabs == (old,)
    assert status.latest_agent == latest_agent
    assert status.latest_agent_tab == latest


def test_duplicate_iteration_numbers_are_protected_as_incomplete() -> None:
    workspace_id = WorkspaceId("w1")
    tabs = (
        HerdrTab(TabId("tracker"), workspace_id, "iter-alpha-tracker", 1, "idle", False, 1),
        HerdrTab(TabId("duplicate-a"), workspace_id, "iter-alpha-001", 2, "done", False, 1),
        HerdrTab(TabId("duplicate-b"), workspace_id, "iter-alpha-001", 3, "done", False, 1),
        HerdrTab(TabId("latest"), workspace_id, "iter-alpha-002", 4, "done", False, 1),
    )
    workspace = HerdrWorkspace(workspace_id, "iter-alpha", 1, tabs[0].tab_id, "idle", False, 4, 4)
    snapshot = _complete_snapshot(workspace=workspace, tabs=tabs, agents=())

    plan = build_workspace_close_plan(snapshot=snapshot, workspace=workspace, retain_previous=0)

    protected = {item.tab.tab_id: item.reason for item in plan.protected_tabs}
    assert protected[tabs[1].tab_id] == "incomplete_snapshot"
    assert protected[tabs[2].tab_id] == "incomplete_snapshot"
    assert plan.retained_tabs == (tabs[3],)
    assert plan.closable_tabs == ()


def test_workspace_discovery_is_exact_and_stable_id_precedes_duplicate_labels() -> None:
    workspaces = (
        HerdrWorkspace(WorkspaceId("iter-duplicate"), "iter-alpha", 1, TabId("a"), "idle", False, 0, 0),
        HerdrWorkspace(WorkspaceId("w2"), "iter-duplicate", 2, TabId("b"), "idle", False, 0, 0),
        HerdrWorkspace(WorkspaceId("w3"), "iter-duplicate", 3, TabId("c"), "idle", False, 0, 0),
        HerdrWorkspace(WorkspaceId("w4"), "iter-collision", 4, TabId("d"), "idle", False, 0, 0),
        HerdrWorkspace(WorkspaceId("w5"), "iter-collision", 5, TabId("e"), "idle", False, 0, 0),
        HerdrWorkspace(WorkspaceId("w6"), "iter", 6, TabId("f"), "idle", False, 0, 0),
        HerdrWorkspace(WorkspaceId("w7"), "iter-", 7, TabId("g"), "idle", False, 0, 0),
        HerdrWorkspace(WorkspaceId("w8"), "iteration-beta", 8, TabId("h"), "idle", False, 0, 0),
    )
    snapshot = HerdrSnapshot(workspaces=workspaces, tabs=(), panes=(), agents=())

    assert iter_workspace_labels(snapshot=snapshot) == ("iter-alpha", "iter-duplicate", "iter-duplicate", "iter-collision", "iter-collision")
    assert resolve_iter_workspace(snapshot=snapshot, workspace_name="iter-duplicate") == workspaces[0]
    with pytest.raises(RuntimeError, match="Multiple Herdr workspaces named 'iter-collision'"):
        resolve_iter_workspace(snapshot=snapshot, workspace_name="iter-collision")


@pytest.mark.parametrize(("workspace_name", "all_workspaces"), ((None, False), ("iter-alpha", True)))
def test_close_plan_selection_requires_exactly_one_scope(workspace_name: str | None, all_workspaces: bool) -> None:
    snapshot = HerdrSnapshot(workspaces=(), tabs=(), panes=(), agents=())

    with pytest.raises(ValueError, match="exactly one"):
        select_iter_workspace_close_plans(snapshot=snapshot, workspace_name=workspace_name, all_workspaces=all_workspaces, retain_previous=3)


def test_close_plan_rejects_negative_retention() -> None:
    snapshot = HerdrSnapshot(workspaces=(), tabs=(), panes=(), agents=())

    with pytest.raises(ValueError, match="must not be negative"):
        select_iter_workspace_close_plans(snapshot=snapshot, workspace_name=None, all_workspaces=True, retain_previous=-1)
