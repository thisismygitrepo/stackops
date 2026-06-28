import json
import re
import shlex
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from time import sleep
from typing import Final, TypeAlias, cast

from rich import box
from rich.console import Console
from rich.table import Table

from stackops.scripts.python.helpers.helpers_agents.agents_iter_constants import TRACK_INTERVAL_SECONDS

JsonObject: TypeAlias = dict[str, object]
KEEP_RECENT_TABS: Final[int] = 3
LOOP_INTERVAL_SECONDS: Final[int] = 300
ITER_WORKSPACE_PREFIX: Final[str] = "iter"
ITER_AGENT_LABEL_PATTERN: Final[re.Pattern[str]] = re.compile(r"^iter-.+-(?P<iteration>[0-9]{3})$")
ITER_TRACKER_SUFFIX: Final[str] = "-tracker"
CLOSABLE_AGENT_STATUSES: Final[frozenset[str]] = frozenset({"done", "idle"})
LAUNCH_SOURCE_AGENT_STATUSES: Final[frozenset[str]] = frozenset({"working", "unknown"})
_CONSOLE: Final[Console] = Console()


@dataclass(frozen=True, slots=True)
class HerdrWorkspace:
    workspace_id: str
    label: str
    number: int
    active_tab_id: str
    agent_status: str
    focused: bool
    pane_count: int
    tab_count: int


@dataclass(frozen=True, slots=True)
class HerdrTab:
    tab_id: str
    workspace_id: str
    label: str
    number: int
    agent_status: str
    focused: bool
    pane_count: int


@dataclass(frozen=True, slots=True)
class HerdrAgent:
    agent: str
    agent_status: str
    workspace_id: str
    tab_id: str
    pane_id: str
    cwd: str
    foreground_cwd: str
    focused: bool
    name: str | None


@dataclass(frozen=True, slots=True)
class HerdrPane:
    pane_id: str
    workspace_id: str
    tab_id: str
    agent_status: str
    agent: str | None
    label: str | None


@dataclass(frozen=True, slots=True)
class IterWorkspaceClose:
    workspace: HerdrWorkspace
    kept_tabs: tuple[HerdrTab, ...]
    guarded_tabs: tuple[HerdrTab, ...]
    closed_tabs: tuple[HerdrTab, ...]


@dataclass(frozen=True, slots=True)
class IterWorkspaceClosePlan:
    workspace: HerdrWorkspace
    tabs: tuple[HerdrTab, ...]
    kept_tabs: tuple[HerdrTab, ...]
    guarded_tabs: tuple[HerdrTab, ...]
    closable_tabs: tuple[HerdrTab, ...]


@dataclass(frozen=True, slots=True)
class IterWorkspaceStatus:
    workspace: HerdrWorkspace
    tabs: tuple[HerdrTab, ...]
    kept_tabs: tuple[HerdrTab, ...]
    guarded_tabs: tuple[HerdrTab, ...]
    closable_tabs: tuple[HerdrTab, ...]
    latest_iteration: int | None
    latest_agent: HerdrAgent | None
    latest_agent_tab: HerdrTab | None


@dataclass(frozen=True, slots=True)
class IterWorkspaceTrackResult:
    workspace: HerdrWorkspace
    latest_iteration: int | None
    max_iterations: int
    closed: bool


@dataclass(frozen=True, slots=True)
class IterWorkspaceTrackCheck:
    status: IterWorkspaceStatus
    budget: IterWorkspaceTrackResult
    close_summary: IterWorkspaceClose | None


def close_iter_workspaces_loop(
    *, workspace_name: str | None, all_workspaces: bool, continuous: bool, report: Callable[[str], None]
) -> None:
    validate_iter_workspace_close_scope(workspace_name=workspace_name, all_workspaces=all_workspaces)
    while True:
        summaries = close_iter_workspaces(workspace_name=workspace_name, all_workspaces=all_workspaces, report=report)
        _report_summaries(summaries=summaries, report=report)
        if not continuous:
            return
        report(f"Next close pass in {LOOP_INTERVAL_SECONDS} second(s).")
        sleep(LOOP_INTERVAL_SECONDS)


def show_iter_status() -> None:
    _CONSOLE.print(build_iter_status_table(statuses=get_iter_workspace_statuses()))


def track_iter_workspace_loop(
    *, workspace_name: str, max_iterations: int, interval_seconds: int, close_old_tabs: bool, report: Callable[[str], None]
) -> None:
    validate_iter_workspace_track_inputs(workspace_name=workspace_name, max_iterations=max_iterations, interval_seconds=interval_seconds)
    report(
        f"Tracking iter workspace {workspace_name}: max_iterations={max_iterations}, "
        f"interval={interval_seconds} second(s), close_old_tabs={close_old_tabs}."
    )
    while True:
        check = track_iter_workspace_once(
            workspace_name=workspace_name,
            max_iterations=max_iterations,
            close_old_tabs=close_old_tabs,
            report=report,
        )
        if check.budget.closed:
            return
        report(f"Next track check in {interval_seconds} second(s).")
        sleep(interval_seconds)


def track_iter_workspace_once(
    *, workspace_name: str, max_iterations: int, close_old_tabs: bool, report: Callable[[str], None]
) -> IterWorkspaceTrackCheck:
    validate_iter_workspace_track_inputs(
        workspace_name=workspace_name,
        max_iterations=max_iterations,
        interval_seconds=TRACK_INTERVAL_SECONDS,
    )
    status = get_iter_workspace_status(workspace_name=workspace_name)
    _report_track_status(status=status, report=report)
    budget = check_iter_workspace_budget(workspace_name=workspace_name, max_iterations=max_iterations, report=report)
    close_summary: IterWorkspaceClose | None = None
    if not budget.closed and close_old_tabs:
        summaries = close_iter_workspaces(workspace_name=workspace_name, all_workspaces=False, report=report)
        if len(summaries) != 1:
            raise RuntimeError(f"Expected one close summary for tracked workspace {workspace_name!r}.")
        close_summary = summaries[0]
    return IterWorkspaceTrackCheck(status=status, budget=budget, close_summary=close_summary)


def check_iter_workspace_budget(
    *, workspace_name: str, max_iterations: int, report: Callable[[str], None]
) -> IterWorkspaceTrackResult:
    validate_iter_workspace_track_inputs(
        workspace_name=workspace_name,
        max_iterations=max_iterations,
        interval_seconds=TRACK_INTERVAL_SECONDS,
    )
    workspace = _get_iter_workspace_by_label(workspace_name=workspace_name)
    tabs = tuple(tab for tab in _list_tabs() if tab.workspace_id == workspace.workspace_id)
    agents = tuple(agent for agent in _list_agents() if agent.workspace_id == workspace.workspace_id)
    latest_iteration = _latest_workspace_iteration(tabs=tabs, agents=agents)
    if latest_iteration is None:
        report(f"{workspace.label}: no numbered iter agents or tabs found; budget={max_iterations}.")
        return IterWorkspaceTrackResult(
            workspace=workspace,
            latest_iteration=latest_iteration,
            max_iterations=max_iterations,
            closed=False,
        )
    if latest_iteration <= max_iterations:
        report(f"{workspace.label}: latest={latest_iteration:03d}, budget={max_iterations:03d}; keeping workspace open.")
        return IterWorkspaceTrackResult(
            workspace=workspace,
            latest_iteration=latest_iteration,
            max_iterations=max_iterations,
            closed=False,
        )
    report(f"{workspace.label}: latest={latest_iteration:03d} exceeded budget={max_iterations:03d}; closing workspace.")
    _run_herdr(["herdr", "workspace", "close", workspace.workspace_id])
    return IterWorkspaceTrackResult(
        workspace=workspace,
        latest_iteration=latest_iteration,
        max_iterations=max_iterations,
        closed=True,
    )


def get_iter_workspace_statuses() -> tuple[IterWorkspaceStatus, ...]:
    workspaces = _iter_workspaces(workspaces=_list_workspaces())
    tabs_by_workspace_id = _tabs_by_workspace_id(tabs=_list_tabs())
    panes_by_tab_id = _panes_by_tab_id(panes=_list_panes())
    agents_by_workspace_id = _agents_by_workspace_id(agents=_list_agents())
    statuses: list[IterWorkspaceStatus] = []
    for workspace in workspaces:
        tabs = tuple(sorted(tabs_by_workspace_id.get(workspace.workspace_id, ()), key=lambda tab: tab.number))
        panes = _panes_for_tabs(tabs=tabs, panes_by_tab_id=panes_by_tab_id)
        agents = agents_by_workspace_id.get(workspace.workspace_id, ())
        latest_agent = _latest_iter_agent(agents=agents_by_workspace_id.get(workspace.workspace_id, ()))
        close_plan = _workspace_close_plan(workspace=workspace, tabs=tabs, panes=panes, agents=agents)
        statuses.append(
            IterWorkspaceStatus(
                workspace=workspace,
                tabs=tabs,
                kept_tabs=close_plan.kept_tabs,
                guarded_tabs=close_plan.guarded_tabs,
                closable_tabs=close_plan.closable_tabs,
                latest_iteration=_latest_workspace_iteration(tabs=tabs, agents=agents),
                latest_agent=latest_agent,
                latest_agent_tab=_find_tab(tabs=tabs, tab_id=latest_agent.tab_id) if latest_agent is not None else None,
            )
        )
    return tuple(statuses)


def get_iter_workspace_status(*, workspace_name: str) -> IterWorkspaceStatus:
    matches = tuple(status for status in get_iter_workspace_statuses() if status.workspace.label == workspace_name)
    if len(matches) == 0:
        raise RuntimeError(f"No Herdr iter workspace named {workspace_name!r} was found.")
    if len(matches) > 1:
        raise RuntimeError(f"Multiple Herdr workspaces named {workspace_name!r} were found; labels must be unique for tracking.")
    return matches[0]


def build_iter_status_table(*, statuses: tuple[IterWorkspaceStatus, ...]) -> Table:
    table = Table(title=f"Iter Status ({len(statuses)})", box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Loop", style="bold", overflow="fold", ratio=3)
    table.add_column("Iter", justify="right", no_wrap=True)
    table.add_column("Agent", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Where", overflow="fold", ratio=2)
    table.add_column("Tabs", no_wrap=True)
    for status in statuses:
        table.add_row(
            status.workspace.label,
            _format_iteration(iteration=status.latest_iteration),
            _format_agent(agent=status.latest_agent),
            _format_agent_status(status=status),
            _format_agent_where(tab=status.latest_agent_tab, agent=status.latest_agent),
            _format_tab_counts(status=status),
        )
    return table


def close_iter_workspaces(
    *, workspace_name: str | None, all_workspaces: bool, report: Callable[[str], None]
) -> tuple[IterWorkspaceClose, ...]:
    close_plans = plan_iter_workspace_closes(workspace_name=workspace_name, all_workspaces=all_workspaces)
    _report_close_plan(close_plans=close_plans, report=report)
    return close_iter_workspace_plans(close_plans=close_plans, report=report)


def close_iter_workspace_plans(
    *, close_plans: tuple[IterWorkspaceClosePlan, ...], report: Callable[[str], None]
) -> tuple[IterWorkspaceClose, ...]:
    total_to_close = sum(len(close_plan.closable_tabs) for close_plan in close_plans)
    closed_count = 0
    summaries: list[IterWorkspaceClose] = []
    for close_plan in close_plans:
        closed_tabs: list[HerdrTab] = []
        for tab in close_plan.closable_tabs:
            closed_count += 1
            report(
                f"Closing {closed_count}/{total_to_close}: {close_plan.workspace.label} "
                f"{_format_tab_for_report(tab=tab)}"
            )
            _run_herdr(["herdr", "tab", "close", tab.tab_id])
            closed_tabs.append(tab)
        summaries.append(
            IterWorkspaceClose(
                workspace=close_plan.workspace,
                kept_tabs=close_plan.kept_tabs,
                guarded_tabs=close_plan.guarded_tabs,
                closed_tabs=tuple(closed_tabs),
            )
        )
    return tuple(summaries)


def plan_iter_workspace_closes(*, workspace_name: str | None, all_workspaces: bool) -> tuple[IterWorkspaceClosePlan, ...]:
    validate_iter_workspace_close_scope(workspace_name=workspace_name, all_workspaces=all_workspaces)
    workspaces = _selected_iter_workspaces(workspaces=_list_workspaces(), workspace_name=workspace_name, all_workspaces=all_workspaces)
    tabs_by_workspace_id = _tabs_by_workspace_id(tabs=_list_tabs())
    panes_by_tab_id = _panes_by_tab_id(panes=_list_panes())
    agents_by_workspace_id = _agents_by_workspace_id(agents=_list_agents())
    close_plans: list[IterWorkspaceClosePlan] = []
    for workspace in workspaces:
        tabs = tuple(sorted(tabs_by_workspace_id.get(workspace.workspace_id, ()), key=lambda tab: tab.number))
        panes = _panes_for_tabs(tabs=tabs, panes_by_tab_id=panes_by_tab_id)
        agents = agents_by_workspace_id.get(workspace.workspace_id, ())
        close_plans.append(_workspace_close_plan(workspace=workspace, tabs=tabs, panes=panes, agents=agents))
    return tuple(close_plans)


def _report_close_plan(*, close_plans: tuple[IterWorkspaceClosePlan, ...], report: Callable[[str], None]) -> None:
    if len(close_plans) == 0:
        report("Planning iter close: no iter workspaces found.")
        return
    total_tabs = sum(len(close_plan.tabs) for close_plan in close_plans)
    total_to_close = sum(len(close_plan.closable_tabs) for close_plan in close_plans)
    total_to_keep = sum(len(close_plan.kept_tabs) for close_plan in close_plans)
    total_guarded = sum(len(close_plan.guarded_tabs) for close_plan in close_plans)
    report(
        f"Planning iter close: {len(close_plans)} workspace(s), {total_tabs} tab(s), "
        f"closing {total_to_close}, keeping {total_to_keep}, launch-guarded {total_guarded}."
    )
    for close_plan in close_plans:
        report(
            f"- {close_plan.workspace.label}: tabs={len(close_plan.tabs)} "
            f"close={len(close_plan.closable_tabs)} keep={len(close_plan.kept_tabs)} "
            f"launch_guard={len(close_plan.guarded_tabs)} workspace={close_plan.workspace.workspace_id}"
        )
        for tab in close_plan.closable_tabs:
            report(f"  will close {_format_tab_for_report(tab=tab)}")


def _report_summaries(*, summaries: tuple[IterWorkspaceClose, ...], report: Callable[[str], None]) -> None:
    if len(summaries) == 0:
        report("No iter workspaces found.")
        return
    total_closed = sum(len(summary.closed_tabs) for summary in summaries)
    report(f"Closed {total_closed} tab(s) across {len(summaries)} iter workspace(s).")
    for summary in summaries:
        report(
            f"- {summary.workspace.label}: closed={len(summary.closed_tabs)} kept={len(summary.kept_tabs)} "
            f"launch_guard={len(summary.guarded_tabs)} workspace={summary.workspace.workspace_id}"
        )


def _report_track_status(*, status: IterWorkspaceStatus, report: Callable[[str], None]) -> None:
    report(
        f"{status.workspace.label}: iter={_format_iteration(iteration=status.latest_iteration)} "
        f"agent={_format_agent(agent=status.latest_agent)} status={_format_agent_status(status=status)} "
        f"tabs={len(status.tabs)} close={len(status.closable_tabs)} guard={len(status.guarded_tabs)}."
    )


def _iter_workspaces(*, workspaces: tuple[HerdrWorkspace, ...]) -> tuple[HerdrWorkspace, ...]:
    return tuple(workspace for workspace in workspaces if workspace.label.startswith(ITER_WORKSPACE_PREFIX))


def validate_iter_workspace_close_scope(*, workspace_name: str | None, all_workspaces: bool) -> None:
    if workspace_name is not None and workspace_name.strip() == "":
        raise ValueError("Workspace name must not be empty.")
    if workspace_name is not None and all_workspaces:
        raise ValueError("Pass either SPACE_NAME or --all, not both.")
    if workspace_name is None and not all_workspaces:
        raise ValueError("Pass SPACE_NAME to close one iter workspace, or --all to close every iter workspace.")


def _selected_iter_workspaces(
    *, workspaces: tuple[HerdrWorkspace, ...], workspace_name: str | None, all_workspaces: bool
) -> tuple[HerdrWorkspace, ...]:
    if all_workspaces:
        return _iter_workspaces(workspaces=workspaces)
    if workspace_name is None:
        raise AssertionError("Workspace name is required when all_workspaces is false.")
    matches = tuple(
        workspace
        for workspace in workspaces
        if workspace.label == workspace_name or workspace.workspace_id == workspace_name
    )
    if len(matches) == 0:
        raise RuntimeError(f"No Herdr iter workspace named {workspace_name!r} was found.")
    if len(matches) > 1:
        raise RuntimeError(f"Multiple Herdr workspaces named {workspace_name!r} were found; labels must be unique for cleanup.")
    workspace = matches[0]
    if not workspace.label.startswith(ITER_WORKSPACE_PREFIX):
        raise RuntimeError(f"Herdr workspace {workspace_name!r} is not an iter workspace.")
    return (workspace,)


def validate_iter_workspace_track_inputs(*, workspace_name: str, max_iterations: int, interval_seconds: int) -> None:
    if workspace_name.strip() == "":
        raise ValueError("Workspace name must not be empty.")
    if max_iterations < 1:
        raise ValueError("Maximum iterations must be greater than zero.")
    if interval_seconds < 1:
        raise ValueError("Track interval must be greater than zero.")


def _get_iter_workspace_by_label(*, workspace_name: str) -> HerdrWorkspace:
    matches = tuple(workspace for workspace in _list_workspaces() if workspace.label == workspace_name)
    if len(matches) == 0:
        raise RuntimeError(f"No Herdr iter workspace named {workspace_name!r} was found.")
    if len(matches) > 1:
        raise RuntimeError(f"Multiple Herdr workspaces named {workspace_name!r} were found; labels must be unique for tracking.")
    workspace = matches[0]
    if not workspace.label.startswith(ITER_WORKSPACE_PREFIX):
        raise RuntimeError(f"Herdr workspace {workspace_name!r} is not an iter workspace.")
    return workspace


def _workspace_close_plan(
    *, workspace: HerdrWorkspace, tabs: tuple[HerdrTab, ...], panes: tuple[HerdrPane, ...], agents: tuple[HerdrAgent, ...]
) -> IterWorkspaceClosePlan:
    guarded_tabs = _guarded_tabs(workspace=workspace, tabs=tabs, panes=panes, agents=agents)
    kept_tabs = _unique_tabs(tabs=(*_kept_recent_tabs(tabs=tabs), *guarded_tabs))
    return IterWorkspaceClosePlan(
        workspace=workspace,
        tabs=tabs,
        kept_tabs=kept_tabs,
        guarded_tabs=guarded_tabs,
        closable_tabs=_closable_tabs(tabs=tabs, kept_tabs=kept_tabs),
    )


def _kept_recent_tabs(*, tabs: tuple[HerdrTab, ...]) -> tuple[HerdrTab, ...]:
    return tuple(sorted(tabs, key=lambda tab: tab.number, reverse=True)[:KEEP_RECENT_TABS])


def _guarded_tabs(
    *, workspace: HerdrWorkspace, tabs: tuple[HerdrTab, ...], panes: tuple[HerdrPane, ...], agents: tuple[HerdrAgent, ...]
) -> tuple[HerdrTab, ...]:
    launch_source_tabs = _launch_source_tabs(workspace=workspace, tabs=tabs, agents=agents)
    guarded_tabs: list[HerdrTab] = []
    guarded_tabs.extend(_tracker_tabs(tabs=tabs))
    guarded_tabs.extend(_non_closable_process_tabs(tabs=tabs, panes=panes))
    for tab in launch_source_tabs:
        guarded_tabs.append(tab)
        next_tab = _next_tab(tab=tab, tabs=tabs)
        if next_tab is not None:
            guarded_tabs.append(next_tab)
    return _unique_tabs(tabs=tuple(guarded_tabs))


def _tracker_tabs(*, tabs: tuple[HerdrTab, ...]) -> tuple[HerdrTab, ...]:
    return tuple(tab for tab in tabs if tab.label.endswith(ITER_TRACKER_SUFFIX))


def _non_closable_process_tabs(*, tabs: tuple[HerdrTab, ...], panes: tuple[HerdrPane, ...]) -> tuple[HerdrTab, ...]:
    panes_by_tab_id = _panes_by_tab_id(panes=panes)
    return tuple(tab for tab in tabs if not _tab_has_only_closable_processes(tab=tab, panes=panes_by_tab_id.get(tab.tab_id, ())))


def _tab_has_only_closable_processes(*, tab: HerdrTab, panes: tuple[HerdrPane, ...]) -> bool:
    if tab.agent_status not in CLOSABLE_AGENT_STATUSES:
        return False
    for pane in panes:
        if pane.agent_status not in CLOSABLE_AGENT_STATUSES:
            return False
    return True


def _launch_source_tabs(*, workspace: HerdrWorkspace, tabs: tuple[HerdrTab, ...], agents: tuple[HerdrAgent, ...]) -> tuple[HerdrTab, ...]:
    source_tabs: list[HerdrTab] = []
    for tab in tabs:
        if tab.agent_status in LAUNCH_SOURCE_AGENT_STATUSES:
            source_tabs.append(tab)
    if workspace.agent_status in LAUNCH_SOURCE_AGENT_STATUSES:
        active_tab = _find_tab(tabs=tabs, tab_id=workspace.active_tab_id)
        if active_tab is not None:
            source_tabs.append(active_tab)
    for agent in agents:
        if agent.agent_status not in LAUNCH_SOURCE_AGENT_STATUSES:
            continue
        agent_tab = _find_tab(tabs=tabs, tab_id=agent.tab_id)
        if agent_tab is not None:
            source_tabs.append(agent_tab)
    return _unique_tabs(tabs=tuple(source_tabs))


def _next_tab(*, tab: HerdrTab, tabs: tuple[HerdrTab, ...]) -> HerdrTab | None:
    for candidate in sorted(tabs, key=lambda item: item.number):
        if candidate.number > tab.number:
            return candidate
    return None


def _unique_tabs(*, tabs: tuple[HerdrTab, ...]) -> tuple[HerdrTab, ...]:
    tab_by_id = {tab.tab_id: tab for tab in tabs}
    return tuple(sorted(tab_by_id.values(), key=lambda tab: tab.number))


def _closable_tabs(*, tabs: tuple[HerdrTab, ...], kept_tabs: tuple[HerdrTab, ...]) -> tuple[HerdrTab, ...]:
    kept_tab_ids = {tab.tab_id for tab in kept_tabs}
    return tuple(tab for tab in sorted(tabs, key=lambda tab: tab.number) if tab.tab_id not in kept_tab_ids)


def _tabs_by_workspace_id(*, tabs: tuple[HerdrTab, ...]) -> dict[str, tuple[HerdrTab, ...]]:
    grouped: dict[str, list[HerdrTab]] = {}
    for tab in tabs:
        grouped.setdefault(tab.workspace_id, []).append(tab)
    return {workspace_id: tuple(workspace_tabs) for workspace_id, workspace_tabs in grouped.items()}


def _panes_by_tab_id(*, panes: tuple[HerdrPane, ...]) -> dict[str, tuple[HerdrPane, ...]]:
    grouped: dict[str, list[HerdrPane]] = {}
    for pane in panes:
        grouped.setdefault(pane.tab_id, []).append(pane)
    return {tab_id: tuple(tab_panes) for tab_id, tab_panes in grouped.items()}


def _panes_for_tabs(*, tabs: tuple[HerdrTab, ...], panes_by_tab_id: dict[str, tuple[HerdrPane, ...]]) -> tuple[HerdrPane, ...]:
    panes: list[HerdrPane] = []
    for tab in tabs:
        panes.extend(panes_by_tab_id.get(tab.tab_id, ()))
    return tuple(panes)


def _agents_by_workspace_id(*, agents: tuple[HerdrAgent, ...]) -> dict[str, tuple[HerdrAgent, ...]]:
    grouped: dict[str, list[HerdrAgent]] = {}
    for agent in agents:
        grouped.setdefault(agent.workspace_id, []).append(agent)
    return {workspace_id: tuple(workspace_agents) for workspace_id, workspace_agents in grouped.items()}


def _latest_iter_agent(*, agents: tuple[HerdrAgent, ...]) -> HerdrAgent | None:
    latest_agent: HerdrAgent | None = None
    latest_iteration: int | None = None
    for agent in agents:
        if agent.name is None:
            continue
        iteration = _iteration_from_label(label=agent.name)
        if iteration is None:
            continue
        if latest_iteration is None or iteration > latest_iteration:
            latest_iteration = iteration
            latest_agent = agent
    return latest_agent


def _latest_workspace_iteration(*, tabs: tuple[HerdrTab, ...], agents: tuple[HerdrAgent, ...]) -> int | None:
    iterations: list[int] = []
    for tab in tabs:
        tab_iteration = _iteration_from_label(label=tab.label)
        if tab_iteration is not None:
            iterations.append(tab_iteration)
    for agent in agents:
        if agent.name is None:
            continue
        agent_iteration = _iteration_from_label(label=agent.name)
        if agent_iteration is not None:
            iterations.append(agent_iteration)
    if len(iterations) == 0:
        return None
    return max(iterations)


def _list_workspaces() -> tuple[HerdrWorkspace, ...]:
    payload = _run_herdr_json(["herdr", "workspace", "list"])
    result = _result_object(payload=payload)
    workspaces_value = result.get("workspaces")
    if not isinstance(workspaces_value, list):
        raise RuntimeError("Herdr workspace list response did not include result.workspaces.")
    return tuple(_parse_workspace(value=value) for value in workspaces_value)


def _list_tabs() -> tuple[HerdrTab, ...]:
    payload = _run_herdr_json(["herdr", "tab", "list"])
    result = _result_object(payload=payload)
    tabs_value = result.get("tabs")
    if not isinstance(tabs_value, list):
        raise RuntimeError("Herdr tab list response did not include result.tabs.")
    return tuple(_parse_tab(value=value) for value in tabs_value)


def _list_agents() -> tuple[HerdrAgent, ...]:
    payload = _run_herdr_json(["herdr", "agent", "list"])
    result = _result_object(payload=payload)
    agents_value = result.get("agents")
    if not isinstance(agents_value, list):
        raise RuntimeError("Herdr agent list response did not include result.agents.")
    return tuple(_parse_agent(value=value) for value in agents_value)


def _list_panes() -> tuple[HerdrPane, ...]:
    payload = _run_herdr_json(["herdr", "pane", "list"])
    result = _result_object(payload=payload)
    panes_value = result.get("panes")
    if not isinstance(panes_value, list):
        raise RuntimeError("Herdr pane list response did not include result.panes.")
    return tuple(_parse_pane(value=value) for value in panes_value)


def _parse_workspace(*, value: object) -> HerdrWorkspace:
    if not isinstance(value, dict):
        raise RuntimeError("Herdr workspace list included a non-object workspace.")
    mapping = cast(JsonObject, value)
    return HerdrWorkspace(
        workspace_id=_required_string(mapping=mapping, key="workspace_id"),
        label=_required_string(mapping=mapping, key="label"),
        number=_required_int(mapping=mapping, key="number"),
        active_tab_id=_required_string(mapping=mapping, key="active_tab_id"),
        agent_status=_required_string(mapping=mapping, key="agent_status"),
        focused=_required_bool(mapping=mapping, key="focused"),
        pane_count=_required_int(mapping=mapping, key="pane_count"),
        tab_count=_required_int(mapping=mapping, key="tab_count"),
    )


def _parse_tab(*, value: object) -> HerdrTab:
    if not isinstance(value, dict):
        raise RuntimeError("Herdr tab list included a non-object tab.")
    mapping = cast(JsonObject, value)
    return HerdrTab(
        tab_id=_required_string(mapping=mapping, key="tab_id"),
        workspace_id=_required_string(mapping=mapping, key="workspace_id"),
        label=_required_string(mapping=mapping, key="label"),
        number=_required_int(mapping=mapping, key="number"),
        agent_status=_required_string(mapping=mapping, key="agent_status"),
        focused=_required_bool(mapping=mapping, key="focused"),
        pane_count=_required_int(mapping=mapping, key="pane_count"),
    )


def _parse_agent(*, value: object) -> HerdrAgent:
    if not isinstance(value, dict):
        raise RuntimeError("Herdr agent list included a non-object agent.")
    mapping = cast(JsonObject, value)
    return HerdrAgent(
        agent=_required_string(mapping=mapping, key="agent"),
        agent_status=_required_string(mapping=mapping, key="agent_status"),
        workspace_id=_required_string(mapping=mapping, key="workspace_id"),
        tab_id=_required_string(mapping=mapping, key="tab_id"),
        pane_id=_required_string(mapping=mapping, key="pane_id"),
        cwd=_required_string(mapping=mapping, key="cwd"),
        foreground_cwd=_required_string(mapping=mapping, key="foreground_cwd"),
        focused=_required_bool(mapping=mapping, key="focused"),
        name=_optional_string(mapping=mapping, key="name"),
    )


def _parse_pane(*, value: object) -> HerdrPane:
    if not isinstance(value, dict):
        raise RuntimeError("Herdr pane list included a non-object pane.")
    mapping = cast(JsonObject, value)
    return HerdrPane(
        pane_id=_required_string(mapping=mapping, key="pane_id"),
        workspace_id=_required_string(mapping=mapping, key="workspace_id"),
        tab_id=_required_string(mapping=mapping, key="tab_id"),
        agent_status=_required_string(mapping=mapping, key="agent_status"),
        agent=_optional_string(mapping=mapping, key="agent"),
        label=_optional_string(mapping=mapping, key="label"),
    )


def _find_tab(*, tabs: tuple[HerdrTab, ...], tab_id: str) -> HerdrTab | None:
    for tab in tabs:
        if tab.tab_id == tab_id:
            return tab
    return None


def _iteration_from_label(*, label: str) -> int | None:
    match = ITER_AGENT_LABEL_PATTERN.match(label)
    if match is None:
        return None
    return int(match.group("iteration"))


def _format_iteration(*, iteration: int | None) -> str:
    if iteration is None:
        return "-"
    return f"{iteration:03d}"


def _format_agent(*, agent: HerdrAgent | None) -> str:
    if agent is None:
        return "-"
    return agent.agent


def _format_agent_status(*, status: IterWorkspaceStatus) -> str:
    if status.latest_agent is not None:
        return status.latest_agent.agent_status
    return status.workspace.agent_status


def _format_agent_where(*, tab: HerdrTab | None, agent: HerdrAgent | None) -> str:
    if tab is not None:
        tab_label = f"tab #{tab.number} {tab.tab_id}"
        if agent is None:
            return tab_label
        return f"{tab_label}\n{agent.foreground_cwd}"
    if agent is not None:
        return f"{agent.tab_id}\n{agent.foreground_cwd}"
    return "-"


def _format_tab_counts(*, status: IterWorkspaceStatus) -> str:
    return f"{len(status.tabs)} total {len(status.closable_tabs)} close {len(status.guarded_tabs)} guard"


def _format_tab_for_report(*, tab: HerdrTab) -> str:
    return f"tab #{tab.number} {tab.label} [{tab.agent_status}] {tab.tab_id}"


def _result_object(*, payload: JsonObject) -> JsonObject:
    result = payload.get("result")
    if not isinstance(result, dict):
        raise RuntimeError("Herdr JSON response did not include an object result.")
    return cast(JsonObject, result)


def _required_string(*, mapping: JsonObject, key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or value == "":
        raise RuntimeError(f"Herdr JSON response did not include a usable {key}.")
    return value


def _optional_string(*, mapping: JsonObject, key: str) -> str | None:
    value = mapping.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or value == "":
        raise RuntimeError(f"Herdr JSON response did not include a usable {key}.")
    return value


def _required_int(*, mapping: JsonObject, key: str) -> int:
    value = mapping.get(key)
    if not isinstance(value, int):
        raise RuntimeError(f"Herdr JSON response did not include a usable {key}.")
    return value


def _required_bool(*, mapping: JsonObject, key: str) -> bool:
    value = mapping.get(key)
    if not isinstance(value, bool):
        raise RuntimeError(f"Herdr JSON response did not include a usable {key}.")
    return value


def _run_herdr(args: list[str]) -> str:
    try:
        result = subprocess.run(args, capture_output=True, check=False, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("Iter loop requested Herdr, but `herdr` was not found in PATH.") from exc
    if result.returncode == 0:
        return result.stdout
    detail = (result.stderr or result.stdout or "unknown error").strip()
    raise RuntimeError(f"Herdr command failed ({shlex.join(args)}): {detail}")


def _run_herdr_json(args: list[str]) -> JsonObject:
    stdout = _run_herdr(args).strip()
    if stdout == "":
        raise RuntimeError(f"Herdr command did not return JSON: {shlex.join(args)}")
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Herdr command returned invalid JSON ({shlex.join(args)}): {stdout}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Herdr command returned non-object JSON ({shlex.join(args)}): {stdout}")
    return cast(JsonObject, payload)
