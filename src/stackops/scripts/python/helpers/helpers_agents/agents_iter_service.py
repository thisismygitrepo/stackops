from collections.abc import Callable

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
    build_iter_workspace_status,
    build_iter_workspace_statuses,
    build_workspace_close_plan,
    resolve_iter_workspace as resolve_snapshot_iter_workspace,
)
from stackops.scripts.python.helpers.helpers_agents.agents_iter_workspace_records import IterWorkspaceRecords, load_iter_workspace_records


def load_active_workspace_ids() -> frozenset[WorkspaceId]:
    return frozenset(workspace.workspace_id for workspace in capture_herdr_snapshot().workspaces)


def get_iter_workspace_statuses(*, workspace_id: str | None, retain_previous: int) -> tuple[IterWorkspaceStatus, ...]:
    snapshot = capture_herdr_snapshot()
    if workspace_id is not None:
        workspace = resolve_snapshot_iter_workspace(snapshot=snapshot, workspace_id=workspace_id)
        records = load_iter_workspace_records(snapshot=snapshot, workspace=workspace)
        status = build_iter_workspace_status(
            snapshot=snapshot, workspace=workspace, run_path=records.run_path, retain_previous=retain_previous, handoffs=records.handoffs
        )
        return (status,)

    records_by_workspace = _load_records_by_workspace(snapshot=snapshot)
    return build_iter_workspace_statuses(
        snapshot=snapshot,
        retain_previous=retain_previous,
        run_paths_by_workspace={workspace_id: records.run_path for workspace_id, records in records_by_workspace.items()},
        handoffs_by_workspace={workspace_id: records.handoffs for workspace_id, records in records_by_workspace.items()},
    )


def plan_iter_workspace_closes(*, workspace_id: str | None, retain_previous: int) -> tuple[IterWorkspaceClosePlan, ...]:
    statuses = get_iter_workspace_statuses(workspace_id=workspace_id, retain_previous=retain_previous)
    return tuple(status.plan for status in statuses)


def close_iter_workspace_plans(*, close_plans: tuple[IterWorkspaceClosePlan, ...], report: Callable[[str], None]) -> tuple[IterWorkspaceClose, ...]:
    results: list[IterWorkspaceClose] = []
    for close_plan in close_plans:
        results.append(close_iter_workspace_plan(close_plan=close_plan, report=report))
    return tuple(results)


def close_iter_workspace_plan(*, close_plan: IterWorkspaceClosePlan, report: Callable[[str], None]) -> IterWorkspaceClose:
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
            records = load_iter_workspace_records(snapshot=snapshot, workspace=current_workspace)
            if records.run_path != close_plan.run_path:
                skipped_tabs.append(SkippedTabClose(tab=candidate, reason="state_changed"))
                continue
            current_plan = build_workspace_close_plan(
                snapshot=snapshot,
                workspace=current_workspace,
                run_path=records.run_path,
                retain_previous=close_plan.retain_previous,
                handoffs=records.handoffs,
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


def _load_records_by_workspace(*, snapshot: HerdrSnapshot) -> dict[WorkspaceId, IterWorkspaceRecords]:
    records_by_workspace: dict[WorkspaceId, IterWorkspaceRecords] = {}
    for workspace in snapshot.workspaces:
        if not workspace.label.startswith("iter-") or workspace.label.removeprefix("iter-") == "":
            continue
        records_by_workspace[workspace.workspace_id] = load_iter_workspace_records(snapshot=snapshot, workspace=workspace)
    return records_by_workspace


def _find_workspace(*, snapshot: HerdrSnapshot, workspace_id: WorkspaceId) -> HerdrWorkspace | None:
    return next((workspace for workspace in snapshot.workspaces if workspace.workspace_id == workspace_id), None)


def _find_tab(*, tabs: tuple[HerdrTab, ...], tab_id: TabId) -> HerdrTab | None:
    return next((tab for tab in tabs if tab.tab_id == tab_id), None)
