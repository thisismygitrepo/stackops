from collections.abc import Mapping
from pathlib import Path
from typing import Final

from stackops.scripts.python.helpers.helpers_agents.agents_iter_contract import (
    handoff_matches_snapshot,
    inventory_is_incomplete,
    mutation_veto_tab_ids,
)
from stackops.scripts.python.helpers.helpers_agents.agents_iter_models import (
    HerdrAgent,
    HerdrSnapshot,
    HerdrTab,
    HerdrWorkspace,
    IterWorkspaceClosePlan,
    IterWorkspaceStatus,
    KeepReason,
    ProtectedTab,
    WorkspaceId,
)
from stackops.scripts.python.helpers.helpers_agents.agents_iter_records import IterationHandoff


_ITER_PREFIX: Final[str] = "iter-"


def resolve_iter_workspace(*, snapshot: HerdrSnapshot, workspace_id: str) -> HerdrWorkspace:
    if workspace_id.strip() == "":
        raise ValueError("Workspace ID must not be empty.")
    matches = tuple(workspace for workspace in _iter_workspaces(snapshot=snapshot) if str(workspace.workspace_id) == workspace_id)
    if len(matches) == 1:
        return matches[0]
    if len(matches) == 0:
        raise RuntimeError(f"No Herdr iter workspace with ID {workspace_id!r} was found.")
    raise RuntimeError(f"Herdr returned duplicate workspace ID {workspace_id!r}.")


def build_iter_workspace_statuses(
    *,
    snapshot: HerdrSnapshot,
    retain_previous: int,
    repo_roots_by_workspace: Mapping[WorkspaceId, Path],
    handoffs_by_workspace: Mapping[WorkspaceId, Mapping[int, IterationHandoff]],
) -> tuple[IterWorkspaceStatus, ...]:
    _validate_retain_previous(retain_previous=retain_previous)
    return tuple(
        build_iter_workspace_status(
            snapshot=snapshot,
            workspace=workspace,
            repo_root=repo_roots_by_workspace[workspace.workspace_id],
            retain_previous=retain_previous,
            handoffs=handoffs_by_workspace.get(workspace.workspace_id, {}),
        )
        for workspace in _iter_workspaces(snapshot=snapshot)
    )


def build_iter_workspace_status(
    *, snapshot: HerdrSnapshot, workspace: HerdrWorkspace, repo_root: Path, retain_previous: int, handoffs: Mapping[int, IterationHandoff]
) -> IterWorkspaceStatus:
    plan = build_workspace_close_plan(snapshot=snapshot, workspace=workspace, repo_root=repo_root, retain_previous=retain_previous, handoffs=handoffs)
    numbered_tabs = tuple((tab, iteration) for tab in plan.tabs if (iteration := _iteration_from_tab(workspace=workspace, tab=tab)) is not None)
    latest_iteration = max((iteration for _tab, iteration in numbered_tabs), default=None)
    latest_agent: HerdrAgent | None = None
    latest_agent_tab: HerdrTab | None = None
    if latest_iteration is not None:
        latest_tabs = tuple(tab for tab, iteration in numbered_tabs if iteration == latest_iteration)
        if len(latest_tabs) == 1:
            latest_agent_tab = latest_tabs[0]
            candidates = tuple(
                agent
                for agent in snapshot.agents
                if agent.workspace_id == workspace.workspace_id and agent.tab_id == latest_agent_tab.tab_id and agent.name == latest_agent_tab.label
            )
            if len(candidates) == 1:
                latest_agent = candidates[0]
    return IterWorkspaceStatus(
        workspace=workspace, plan=plan, latest_iteration=latest_iteration, latest_agent=latest_agent, latest_agent_tab=latest_agent_tab
    )


def build_workspace_close_plan(
    *, snapshot: HerdrSnapshot, workspace: HerdrWorkspace, repo_root: Path, retain_previous: int, handoffs: Mapping[int, IterationHandoff]
) -> IterWorkspaceClosePlan:
    _validate_retain_previous(retain_previous=retain_previous)
    if not _is_iter_workspace(workspace=workspace):
        raise ValueError(f"Herdr workspace {workspace.label!r} is not an iter workspace.")
    tabs = tuple(sorted((tab for tab in snapshot.tabs if tab.workspace_id == workspace.workspace_id), key=lambda tab: (tab.number, str(tab.tab_id))))
    numbered = {tab.tab_id: iteration for tab in tabs if (iteration := _iteration_from_tab(workspace=workspace, tab=tab)) is not None}
    duplicate_iterations = len(numbered) != len(set(numbered.values()))
    workspace_has_unmanaged_tabs = len(numbered) != len(tabs)
    incomplete = duplicate_iterations or inventory_is_incomplete(snapshot=snapshot, workspace=workspace, tabs=tabs, numbered=numbered)
    latest_iteration = max(numbered.values(), default=None)
    active_tab_ids = mutation_veto_tab_ids(snapshot=snapshot, workspace=workspace, tabs=tabs)

    retained_tabs: list[HerdrTab] = []
    protected_tabs: list[ProtectedTab] = []
    closable_tabs: list[HerdrTab] = []
    for tab in tabs:
        iteration = numbered.get(tab.tab_id)
        reason = _protection_reason(tab=tab, iteration=iteration, incomplete=incomplete, workspace_has_unmanaged_tabs=workspace_has_unmanaged_tabs)
        if reason is not None:
            protected_tabs.append(ProtectedTab(tab=tab, reason=reason))
            continue
        if latest_iteration is not None and iteration is not None and iteration >= latest_iteration - retain_previous:
            retained_tabs.append(tab)
            continue
        if tab.tab_id in active_tab_ids:
            protected_tabs.append(ProtectedTab(tab=tab, reason="active"))
            continue
        if tab.focused:
            protected_tabs.append(ProtectedTab(tab=tab, reason="selected"))
            continue
        if iteration is None or not handoff_matches_snapshot(
            snapshot=snapshot, workspace=workspace, source_tab=tab, source_iteration=iteration, handoff=handoffs.get(iteration)
        ):
            protected_tabs.append(ProtectedTab(tab=tab, reason="handoff_unverified"))
            continue
        closable_tabs.append(tab)
    return IterWorkspaceClosePlan(
        workspace=workspace,
        repo_root=repo_root,
        tabs=tabs,
        retained_tabs=tuple(retained_tabs),
        protected_tabs=tuple(protected_tabs),
        closable_tabs=tuple(closable_tabs),
        retain_previous=retain_previous,
    )


def _protection_reason(*, tab: HerdrTab, iteration: int | None, incomplete: bool, workspace_has_unmanaged_tabs: bool) -> KeepReason | None:
    if iteration is None:
        return "unmanaged"
    if incomplete or workspace_has_unmanaged_tabs:
        return "incomplete_snapshot"
    return None


def _iteration_from_tab(*, workspace: HerdrWorkspace, tab: HerdrTab) -> int | None:
    prefix = f"{workspace.label}-"
    if not tab.label.startswith(prefix):
        return None
    digits = tab.label.removeprefix(prefix)
    if len(digits) < 3 or not digits.isascii() or not digits.isdecimal():
        return None
    iteration = int(digits)
    return iteration if iteration > 0 else None


def _iter_workspaces(*, snapshot: HerdrSnapshot) -> tuple[HerdrWorkspace, ...]:
    return tuple(
        sorted(
            (workspace for workspace in snapshot.workspaces if _is_iter_workspace(workspace=workspace)),
            key=lambda item: (item.number, str(item.workspace_id)),
        )
    )


def _is_iter_workspace(*, workspace: HerdrWorkspace) -> bool:
    return workspace.label.startswith(_ITER_PREFIX) and workspace.label.removeprefix(_ITER_PREFIX) != ""


def _validate_retain_previous(*, retain_previous: int) -> None:
    if retain_previous < 0:
        raise ValueError("Retained previous iterations must not be negative.")
