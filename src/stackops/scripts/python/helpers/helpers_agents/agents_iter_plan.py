from typing import Final

from stackops.scripts.python.helpers.helpers_agents.agents_iter_models import (
    HerdrAgent,
    HerdrSnapshot,
    HerdrStatus,
    HerdrTab,
    HerdrWorkspace,
    IterWorkspaceClosePlan,
    IterWorkspaceStatus,
    KeepReason,
    ProtectedTab,
    TabId,
)


_ITER_PREFIX: Final[str] = "iter-"
_CLOSED_STATUSES: Final[frozenset[HerdrStatus]] = frozenset(("done", "idle"))


def iter_workspace_labels(*, snapshot: HerdrSnapshot) -> tuple[str, ...]:
    return tuple(workspace.label for workspace in _iter_workspaces(snapshot=snapshot))


def resolve_iter_workspace(*, snapshot: HerdrSnapshot, workspace_name: str) -> HerdrWorkspace:
    if workspace_name.strip() == "":
        raise ValueError("Workspace name must not be empty.")
    workspaces = _iter_workspaces(snapshot=snapshot)
    id_matches = tuple(workspace for workspace in workspaces if str(workspace.workspace_id) == workspace_name)
    if len(id_matches) == 1:
        return id_matches[0]
    if len(id_matches) > 1:
        raise RuntimeError(f"Multiple Herdr workspaces use ID {workspace_name!r}.")
    label_matches = tuple(workspace for workspace in workspaces if workspace.label == workspace_name)
    if len(label_matches) == 1:
        return label_matches[0]
    if len(label_matches) == 0:
        raise RuntimeError(f"No Herdr iter workspace named {workspace_name!r} was found.")
    raise RuntimeError(f"Multiple Herdr workspaces named {workspace_name!r} were found; use a workspace ID.")


def select_iter_workspace_close_plans(
    *, snapshot: HerdrSnapshot, workspace_name: str | None, all_workspaces: bool, retain_previous: int
) -> tuple[IterWorkspaceClosePlan, ...]:
    _validate_retain_previous(retain_previous=retain_previous)
    _validate_scope(workspace_name=workspace_name, all_workspaces=all_workspaces)
    if all_workspaces:
        workspaces = _iter_workspaces(snapshot=snapshot)
    else:
        if workspace_name is None:
            raise AssertionError("Validated single-workspace scope did not include a workspace name.")
        workspaces = (resolve_iter_workspace(snapshot=snapshot, workspace_name=workspace_name),)
    return tuple(build_workspace_close_plan(snapshot=snapshot, workspace=workspace, retain_previous=retain_previous) for workspace in workspaces)


def build_iter_workspace_statuses(*, snapshot: HerdrSnapshot, retain_previous: int) -> tuple[IterWorkspaceStatus, ...]:
    _validate_retain_previous(retain_previous=retain_previous)
    return tuple(
        build_iter_workspace_status(snapshot=snapshot, workspace=workspace, retain_previous=retain_previous)
        for workspace in _iter_workspaces(snapshot=snapshot)
    )


def build_iter_workspace_status(*, snapshot: HerdrSnapshot, workspace: HerdrWorkspace, retain_previous: int) -> IterWorkspaceStatus:
    plan = build_workspace_close_plan(snapshot=snapshot, workspace=workspace, retain_previous=retain_previous)
    numbered_tabs = tuple((tab, iteration) for tab in plan.tabs if (iteration := _iteration_from_tab(workspace=workspace, tab=tab)) is not None)
    latest_iteration = max((iteration for _tab, iteration in numbered_tabs), default=None)
    latest_agent: HerdrAgent | None = None
    latest_agent_tab: HerdrTab | None = None
    if latest_iteration is not None:
        latest_tabs = tuple(tab for tab, iteration in numbered_tabs if iteration == latest_iteration)
        if len(latest_tabs) == 1:
            candidate_tab = latest_tabs[0]
            candidates = tuple(
                agent
                for agent in snapshot.agents
                if agent.workspace_id == workspace.workspace_id and agent.tab_id == candidate_tab.tab_id and agent.name == candidate_tab.label
            )
            if len(candidates) == 1:
                latest_agent = candidates[0]
                latest_agent_tab = candidate_tab
    return IterWorkspaceStatus(
        workspace=workspace, plan=plan, latest_iteration=latest_iteration, latest_agent=latest_agent, latest_agent_tab=latest_agent_tab
    )


def build_workspace_close_plan(*, snapshot: HerdrSnapshot, workspace: HerdrWorkspace, retain_previous: int) -> IterWorkspaceClosePlan:
    _validate_retain_previous(retain_previous=retain_previous)
    if not _is_iter_workspace(workspace=workspace):
        raise ValueError(f"Herdr workspace {workspace.label!r} is not an iter workspace.")
    tabs = tuple(sorted((tab for tab in snapshot.tabs if tab.workspace_id == workspace.workspace_id), key=lambda tab: (tab.number, str(tab.tab_id))))
    if len({tab.tab_id for tab in tabs}) != len(tabs):
        raise ValueError(f"Herdr workspace {workspace.label!r} contains duplicate tab IDs.")
    numbered = {tab.tab_id: iteration for tab in tabs if (iteration := _iteration_from_tab(workspace=workspace, tab=tab)) is not None}
    latest_iteration = max(numbered.values(), default=None)
    incomplete = _inventory_is_incomplete(snapshot=snapshot, workspace=workspace, tabs=tabs)
    duplicate_iterations = {iteration for iteration in numbered.values() if sum(candidate == iteration for candidate in numbered.values()) > 1}
    active_tab_ids = _active_tab_ids(snapshot=snapshot, workspace=workspace, tabs=tabs)
    launch_successor_ids: set[TabId] = set()
    for source in tabs:
        source_iteration = numbered.get(source.tab_id)
        if source.tab_id not in active_tab_ids or source_iteration is None:
            continue
        later_iterations = tuple(iteration for iteration in numbered.values() if iteration > source_iteration)
        if len(later_iterations) == 0:
            continue
        successor_iteration = min(later_iterations)
        launch_successor_ids.update(tab.tab_id for tab in tabs if numbered.get(tab.tab_id) == successor_iteration)
    retained_tabs: list[HerdrTab] = []
    protected_tabs: list[ProtectedTab] = []
    closable_tabs: list[HerdrTab] = []
    for tab in tabs:
        reason = _protection_reason(
            workspace=workspace,
            tab=tab,
            iteration=numbered.get(tab.tab_id),
            incomplete=incomplete,
            duplicate_iterations=duplicate_iterations,
            active_tab_ids=active_tab_ids,
            launch_successor_ids=launch_successor_ids,
        )
        if reason is not None:
            protected_tabs.append(ProtectedTab(tab=tab, reason=reason))
            continue
        iteration = numbered[tab.tab_id]
        if latest_iteration is not None and iteration >= latest_iteration - retain_previous:
            retained_tabs.append(tab)
        else:
            closable_tabs.append(tab)
    return IterWorkspaceClosePlan(
        workspace=workspace,
        tabs=tabs,
        retained_tabs=tuple(retained_tabs),
        protected_tabs=tuple(protected_tabs),
        closable_tabs=tuple(closable_tabs),
        retain_previous=retain_previous,
    )


def _protection_reason(
    *,
    workspace: HerdrWorkspace,
    tab: HerdrTab,
    iteration: int | None,
    incomplete: bool,
    duplicate_iterations: set[int],
    active_tab_ids: set[TabId],
    launch_successor_ids: set[TabId],
) -> KeepReason | None:
    if incomplete:
        return "incomplete_snapshot"
    if tab.label == f"{workspace.label}-tracker":
        return "tracker"
    if iteration is None:
        return "unmanaged"
    if iteration in duplicate_iterations:
        return "incomplete_snapshot"
    if tab.tab_id in active_tab_ids:
        return "active"
    if tab.tab_id in launch_successor_ids:
        return "launch_successor"
    return None


def _active_tab_ids(*, snapshot: HerdrSnapshot, workspace: HerdrWorkspace, tabs: tuple[HerdrTab, ...]) -> set[TabId]:
    tab_ids = {tab.tab_id for tab in tabs}
    active_ids: set[TabId] = {workspace.active_tab_id} & tab_ids
    active_ids.update(tab.tab_id for tab in tabs if tab.focused or tab.agent_status not in _CLOSED_STATUSES)
    active_ids.update(
        pane.tab_id
        for pane in snapshot.panes
        if pane.workspace_id == workspace.workspace_id and pane.tab_id in tab_ids and pane.agent_status not in _CLOSED_STATUSES
    )
    active_ids.update(
        agent.tab_id
        for agent in snapshot.agents
        if agent.workspace_id == workspace.workspace_id and agent.tab_id in tab_ids and (agent.focused or agent.agent_status not in _CLOSED_STATUSES)
    )
    return active_ids


def _inventory_is_incomplete(*, snapshot: HerdrSnapshot, workspace: HerdrWorkspace, tabs: tuple[HerdrTab, ...]) -> bool:
    tab_ids = {tab.tab_id for tab in tabs}
    panes = tuple(pane for pane in snapshot.panes if pane.workspace_id == workspace.workspace_id)
    if (
        workspace.tab_count != len(tabs)
        or workspace.pane_count != len(panes)
        or sum(tab.pane_count for tab in tabs) != workspace.pane_count
        or workspace.active_tab_id not in tab_ids
    ):
        return True
    if len({pane.pane_id for pane in panes}) != len(panes):
        return True
    for tab in tabs:
        attached_panes = tuple(pane for pane in panes if pane.tab_id == tab.tab_id)
        if len(attached_panes) == 0 or tab.pane_count != len(attached_panes):
            return True
    valid_panes = {pane.pane_id: pane for pane in panes if pane.tab_id in tab_ids}
    if any(pane.tab_id not in tab_ids for pane in panes):
        return True
    for agent in snapshot.agents:
        if agent.workspace_id != workspace.workspace_id or agent.agent_status in _CLOSED_STATUSES and not agent.focused:
            continue
        pane = valid_panes.get(agent.pane_id)
        if agent.tab_id not in tab_ids or pane is None or pane.tab_id != agent.tab_id:
            return True
    return False


def _iteration_from_tab(*, workspace: HerdrWorkspace, tab: HerdrTab) -> int | None:
    prefix = f"{workspace.label}-"
    if not tab.label.startswith(prefix):
        return None
    digits = tab.label.removeprefix(prefix)
    if len(digits) < 3 or any(character < "0" or character > "9" for character in digits):
        return None
    iteration = int(digits)
    if iteration == 0:
        return None
    return iteration


def _iter_workspaces(*, snapshot: HerdrSnapshot) -> tuple[HerdrWorkspace, ...]:
    return tuple(
        sorted(
            (workspace for workspace in snapshot.workspaces if _is_iter_workspace(workspace=workspace)),
            key=lambda item: (item.number, str(item.workspace_id)),
        )
    )


def _is_iter_workspace(*, workspace: HerdrWorkspace) -> bool:
    return workspace.label.startswith(_ITER_PREFIX) and workspace.label.removeprefix(_ITER_PREFIX).strip() != ""


def _validate_retain_previous(*, retain_previous: int) -> None:
    if retain_previous < 0:
        raise ValueError("Retained previous iterations must not be negative.")


def _validate_scope(*, workspace_name: str | None, all_workspaces: bool) -> None:
    if workspace_name is not None and workspace_name.strip() == "":
        raise ValueError("Workspace name must not be empty.")
    if (workspace_name is None) == (not all_workspaces):
        raise ValueError("Pass exactly one workspace name or --all.")
