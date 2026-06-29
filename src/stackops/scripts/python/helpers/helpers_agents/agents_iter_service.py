from collections.abc import Callable

from stackops.scripts.python.helpers.helpers_agents.agents_iter_herdr import (
    capture_herdr_snapshot,
    close_tab,
    close_workspace,
    list_tabs,
    list_workspaces,
)
from stackops.scripts.python.helpers.helpers_agents.agents_iter_models import (
    FailedTabClose,
    HerdrSnapshot,
    HerdrTab,
    HerdrWorkspace,
    IterWorkspaceClose,
    IterWorkspaceClosePlan,
    IterWorkspaceStatus,
    IterWorkspaceTrackCheck,
    IterWorkspaceTrackResult,
    SkippedTabClose,
    TabId,
    WorkspaceId,
)
from stackops.scripts.python.helpers.helpers_agents.agents_iter_plan import (
    build_iter_workspace_status,
    build_iter_workspace_statuses,
    build_workspace_close_plan,
    iter_workspace_labels,
    resolve_iter_workspace as resolve_snapshot_iter_workspace,
    select_iter_workspace_close_plans,
)


def load_active_iter_workspace_labels() -> frozenset[str]:
    return frozenset(iter_workspace_labels(snapshot=capture_herdr_snapshot()))


def resolve_iter_workspace(*, workspace_name: str) -> HerdrWorkspace:
    snapshot = capture_herdr_snapshot()
    return resolve_snapshot_iter_workspace(snapshot=snapshot, workspace_name=workspace_name)


def get_iter_workspace_statuses(*, retain_previous: int) -> tuple[IterWorkspaceStatus, ...]:
    return build_iter_workspace_statuses(snapshot=capture_herdr_snapshot(), retain_previous=retain_previous)


def get_iter_workspace_status(*, workspace_name: str, retain_previous: int) -> IterWorkspaceStatus:
    snapshot = capture_herdr_snapshot()
    workspace = resolve_snapshot_iter_workspace(snapshot=snapshot, workspace_name=workspace_name)
    return build_iter_workspace_status(snapshot=snapshot, workspace=workspace, retain_previous=retain_previous)


def plan_iter_workspace_closes(
    *, workspace_name: str | None, all_workspaces: bool, retain_previous: int
) -> tuple[IterWorkspaceClosePlan, ...]:
    return select_iter_workspace_close_plans(
        snapshot=capture_herdr_snapshot(),
        workspace_name=workspace_name,
        all_workspaces=all_workspaces,
        retain_previous=retain_previous,
    )


def close_iter_workspace_plans(
    *, close_plans: tuple[IterWorkspaceClosePlan, ...], report: Callable[[str], None]
) -> tuple[IterWorkspaceClose, ...]:
    total_to_close = sum(len(plan.closable_tabs) for plan in close_plans)
    attempted = 0
    results: list[IterWorkspaceClose] = []
    for original_plan in close_plans:
        closed_tabs: list[HerdrTab] = []
        already_absent_tabs: list[HerdrTab] = []
        skipped_tabs: list[SkippedTabClose] = []
        failed_tabs: list[FailedTabClose] = []
        for candidate in original_plan.closable_tabs:
            attempted += 1
            report(
                f"Revalidating {attempted}/{total_to_close}: {original_plan.workspace.label} "
                f"tab #{candidate.number} {candidate.label} {candidate.tab_id}"
            )
            try:
                snapshot = capture_herdr_snapshot()
            except RuntimeError as error:
                failed_tabs.append(FailedTabClose(tab=candidate, message=str(error)))
                continue

            current_workspace = _find_workspace(snapshot=snapshot, workspace_id=original_plan.workspace.workspace_id)
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

            current_plan = build_workspace_close_plan(
                snapshot=snapshot,
                workspace=current_workspace,
                retain_previous=original_plan.retain_previous,
            )
            if candidate.tab_id not in {tab.tab_id for tab in current_plan.closable_tabs}:
                skipped_tabs.append(SkippedTabClose(tab=candidate, reason="state_changed"))
                continue

            close_error: RuntimeError | None = None
            try:
                close_tab(tab_id=candidate.tab_id)
            except RuntimeError as error:
                close_error = error
            try:
                tab_still_exists = candidate.tab_id in {tab.tab_id for tab in list_tabs()}
            except RuntimeError as error:
                detail = f"Close verification failed: {error}"
                if close_error is not None:
                    detail = f"{close_error}; {detail}"
                failed_tabs.append(FailedTabClose(tab=candidate, message=detail))
                continue
            if not tab_still_exists:
                if close_error is None:
                    closed_tabs.append(candidate)
                else:
                    already_absent_tabs.append(candidate)
                continue
            if close_error is None:
                failed_tabs.append(FailedTabClose(tab=candidate, message="Herdr reported success but the tab still exists."))
            else:
                failed_tabs.append(FailedTabClose(tab=candidate, message=str(close_error)))

        results.append(
            IterWorkspaceClose(
                workspace=original_plan.workspace,
                retained_tabs=original_plan.retained_tabs,
                protected_tabs=original_plan.protected_tabs,
                closed_tabs=tuple(closed_tabs),
                already_absent_tabs=tuple(already_absent_tabs),
                skipped_tabs=tuple(skipped_tabs),
                failed_tabs=tuple(failed_tabs),
            )
        )
    return tuple(results)


def validate_iter_workspace_track_inputs(
    *, workspace_name: str, max_iterations: int, interval_seconds: int, retain_previous: int
) -> None:
    if workspace_name.strip() == "":
        raise ValueError("Workspace name must not be empty.")
    if max_iterations < 1:
        raise ValueError("Maximum iterations must be greater than zero.")
    if interval_seconds < 1:
        raise ValueError("Track interval must be greater than zero.")
    if retain_previous < 0:
        raise ValueError("Retained previous iterations must not be negative.")


def track_iter_workspace_once(
    *, workspace_id: WorkspaceId, max_iterations: int, retain_previous: int, report: Callable[[str], None]
) -> IterWorkspaceTrackCheck:
    if max_iterations < 1:
        raise ValueError("Maximum iterations must be greater than zero.")
    if retain_previous < 0:
        raise ValueError("Retained previous iterations must not be negative.")
    snapshot = capture_herdr_snapshot()
    workspace = _find_workspace(snapshot=snapshot, workspace_id=workspace_id)
    if workspace is None:
        track_result = IterWorkspaceTrackResult(
            workspace_id=workspace_id,
            workspace=None,
            latest_iteration=None,
            max_iterations=max_iterations,
            phase="closed",
            message="Workspace was already closed externally.",
        )
        return IterWorkspaceTrackCheck(status=None, track_result=track_result, close_result=None)

    status = build_iter_workspace_status(snapshot=snapshot, workspace=workspace, retain_previous=retain_previous)
    latest_iteration = status.latest_iteration
    if latest_iteration is not None and latest_iteration > max_iterations:
        track_result = _close_workspace_after_budget(
            workspace=workspace,
            latest_iteration=latest_iteration,
            max_iterations=max_iterations,
            report=report,
        )
        return IterWorkspaceTrackCheck(status=status, track_result=track_result, close_result=None)

    close_results = close_iter_workspace_plans(close_plans=(status.plan,), report=report)
    close_result = close_results[0]
    failed_count = len(close_result.failed_tabs)
    track_result = IterWorkspaceTrackResult(
        workspace_id=workspace.workspace_id,
        workspace=workspace,
        latest_iteration=latest_iteration,
        max_iterations=max_iterations,
        phase="failed" if failed_count > 0 else "within_budget",
        message=f"{failed_count} old tab close(s) failed; tracking will retry." if failed_count > 0 else None,
    )
    return IterWorkspaceTrackCheck(status=status, track_result=track_result, close_result=close_result)


def _close_workspace_after_budget(
    *, workspace: HerdrWorkspace, latest_iteration: int, max_iterations: int, report: Callable[[str], None]
) -> IterWorkspaceTrackResult:
    report(
        f"{workspace.label}: latest={latest_iteration:03d} exceeded budget={max_iterations:03d}; "
        "closing the pinned workspace."
    )
    close_error: RuntimeError | None = None
    try:
        close_workspace(workspace_id=workspace.workspace_id)
    except RuntimeError as error:
        close_error = error
    try:
        workspace_still_exists = workspace.workspace_id in {item.workspace_id for item in list_workspaces()}
    except RuntimeError as error:
        message = f"Workspace close verification failed: {error}"
        if close_error is not None:
            message = f"{close_error}; {message}"
        return _failed_track_result(
            workspace=workspace,
            latest_iteration=latest_iteration,
            max_iterations=max_iterations,
            message=message,
        )
    if workspace_still_exists:
        message = str(close_error) if close_error is not None else "Herdr reported success but the workspace still exists."
        return _failed_track_result(
            workspace=workspace,
            latest_iteration=latest_iteration,
            max_iterations=max_iterations,
            message=message,
        )
    return IterWorkspaceTrackResult(
        workspace_id=workspace.workspace_id,
        workspace=workspace,
        latest_iteration=latest_iteration,
        max_iterations=max_iterations,
        phase="closed",
        message="Iteration budget exceeded; workspace closure verified.",
    )


def _failed_track_result(
    *, workspace: HerdrWorkspace, latest_iteration: int, max_iterations: int, message: str
) -> IterWorkspaceTrackResult:
    return IterWorkspaceTrackResult(
        workspace_id=workspace.workspace_id,
        workspace=workspace,
        latest_iteration=latest_iteration,
        max_iterations=max_iterations,
        phase="failed",
        message=message,
    )


def _find_workspace(*, snapshot: HerdrSnapshot, workspace_id: WorkspaceId) -> HerdrWorkspace | None:
    return next((workspace for workspace in snapshot.workspaces if workspace.workspace_id == workspace_id), None)


def _find_tab(*, tabs: tuple[HerdrTab, ...], tab_id: TabId) -> HerdrTab | None:
    return next((tab for tab in tabs if tab.tab_id == tab_id), None)
