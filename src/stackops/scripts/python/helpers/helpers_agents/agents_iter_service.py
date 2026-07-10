from collections.abc import Callable
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_iter_herdr import HerdrApiError, capture_herdr_snapshot, close_tab
from stackops.scripts.python.helpers.helpers_agents.agents_iter_models import (
    FailedTabClose,
    HerdrSnapshot,
    HerdrTab,
    HerdrWorkspace,
    IterWorkspaceClose,
    IterWorkspaceClosePlan,
    IterWorkspaceStatus,
    SkippedTabClose,
    TabId,
    WorkspaceId,
)
from stackops.scripts.python.helpers.helpers_agents.agents_iter_plan import (
    build_iter_workspace_statuses,
    build_workspace_close_plan,
    resolve_iter_workspace as resolve_snapshot_iter_workspace,
)
from stackops.scripts.python.helpers.helpers_agents.agents_iter_records import IterationHandoff, load_iteration_handoffs


def load_active_workspace_ids() -> frozenset[WorkspaceId]:
    return frozenset(workspace.workspace_id for workspace in capture_herdr_snapshot().workspaces)


def get_iter_workspace_statuses(*, cwd: Path, retain_previous: int) -> tuple[IterWorkspaceStatus, ...]:
    snapshot = capture_herdr_snapshot()
    handoffs_by_workspace = _load_handoffs_by_workspace(cwd=cwd, snapshot=snapshot)
    return build_iter_workspace_statuses(snapshot=snapshot, retain_previous=retain_previous, handoffs_by_workspace=handoffs_by_workspace)


def plan_iter_workspace_closes(*, cwd: Path, workspace_id: str | None, retain_previous: int) -> tuple[IterWorkspaceClosePlan, ...]:
    snapshot = capture_herdr_snapshot()
    if workspace_id is None:
        handoffs_by_workspace = _load_handoffs_by_workspace(cwd=cwd, snapshot=snapshot)
        statuses = build_iter_workspace_statuses(
            snapshot=snapshot,
            retain_previous=retain_previous,
            handoffs_by_workspace=handoffs_by_workspace,
        )
        return tuple(status.plan for status in statuses)

    workspace = resolve_snapshot_iter_workspace(snapshot=snapshot, workspace_id=workspace_id)
    handoffs = load_iteration_handoffs(cwd=cwd, workspace_label=workspace.label)
    close_plan = build_workspace_close_plan(
        snapshot=snapshot,
        workspace=workspace,
        retain_previous=retain_previous,
        handoffs=handoffs,
    )
    return (close_plan,)


def close_iter_workspace_plans(
    *, cwd: Path, close_plans: tuple[IterWorkspaceClosePlan, ...], report: Callable[[str], None]
) -> tuple[IterWorkspaceClose, ...]:
    results: list[IterWorkspaceClose] = []
    for close_plan in close_plans:
        results.append(close_iter_workspace_plan(cwd=cwd, close_plan=close_plan, report=report))
    return tuple(results)


def close_iter_workspace_plan(*, cwd: Path, close_plan: IterWorkspaceClosePlan, report: Callable[[str], None]) -> IterWorkspaceClose:
    closed_tabs: list[HerdrTab] = []
    already_absent_tabs: list[HerdrTab] = []
    skipped_tabs: list[SkippedTabClose] = []
    failed_tabs: list[FailedTabClose] = []
    for attempted, candidate in enumerate(close_plan.closable_tabs, start=1):
        report(
            f"Revalidating {attempted}/{len(close_plan.closable_tabs)}: {close_plan.workspace.label} "
            f"tab #{candidate.number} {candidate.label} {candidate.tab_id}"
        )
        try:
            snapshot = capture_herdr_snapshot()
            current_workspace = _find_workspace(snapshot=snapshot, workspace_id=close_plan.workspace.workspace_id)
            current_tab = _find_tab(tabs=snapshot.tabs, tab_id=candidate.tab_id)
            if current_workspace is None:
                if current_tab is None:
                    already_absent_tabs.append(candidate)
                else:
                    skipped_tabs.append(SkippedTabClose(tab=candidate, reason="workspace_absent"))
                continue
            if current_tab is None:
                already_absent_tabs.append(candidate)
                continue
            if current_tab.workspace_id != current_workspace.workspace_id:
                skipped_tabs.append(SkippedTabClose(tab=candidate, reason="state_changed"))
                continue
            handoffs = load_iteration_handoffs(cwd=cwd, workspace_label=current_workspace.label)
            current_plan = build_workspace_close_plan(
                snapshot=snapshot, workspace=current_workspace, retain_previous=close_plan.retain_previous, handoffs=handoffs
            )
            if candidate.tab_id not in {tab.tab_id for tab in current_plan.closable_tabs}:
                skipped_tabs.append(SkippedTabClose(tab=candidate, reason="state_changed"))
                continue
            close_tab(tab_id=candidate.tab_id)
        except HerdrApiError as error:
            if error.code == "tab_not_found":
                already_absent_tabs.append(candidate)
            else:
                failed_tabs.append(FailedTabClose(tab=candidate, message=str(error)))
        except RuntimeError as error:
            failed_tabs.append(FailedTabClose(tab=candidate, message=str(error)))
        else:
            closed_tabs.append(candidate)

    return IterWorkspaceClose(
        workspace=close_plan.workspace,
        retained_tabs=close_plan.retained_tabs,
        protected_tabs=close_plan.protected_tabs,
        closed_tabs=tuple(closed_tabs),
        already_absent_tabs=tuple(already_absent_tabs),
        skipped_tabs=tuple(skipped_tabs),
        failed_tabs=tuple(failed_tabs),
    )


def _load_handoffs_by_workspace(*, cwd: Path, snapshot: HerdrSnapshot) -> dict[WorkspaceId, dict[int, IterationHandoff]]:
    handoffs: dict[WorkspaceId, dict[int, IterationHandoff]] = {}
    for workspace in snapshot.workspaces:
        if not workspace.label.startswith("iter-") or workspace.label.removeprefix("iter-") == "":
            continue
        handoffs[workspace.workspace_id] = load_iteration_handoffs(cwd=cwd, workspace_label=workspace.label)
    return handoffs


def _find_workspace(*, snapshot: HerdrSnapshot, workspace_id: WorkspaceId) -> HerdrWorkspace | None:
    return next((workspace for workspace in snapshot.workspaces if workspace.workspace_id == workspace_id), None)


def _find_tab(*, tabs: tuple[HerdrTab, ...], tab_id: TabId) -> HerdrTab | None:
    return next((tab for tab in tabs if tab.tab_id == tab_id), None)
