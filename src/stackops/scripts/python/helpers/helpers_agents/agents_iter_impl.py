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


JsonObject: TypeAlias = dict[str, object]
KEEP_RECENT_TABS: Final[int] = 3
LOOP_INTERVAL_SECONDS: Final[int] = 300
ITER_WORKSPACE_PREFIX: Final[str] = "iter"
ITER_AGENT_LABEL_PATTERN: Final[re.Pattern[str]] = re.compile(r"^iter-.+-(?P<iteration>[0-9]{3})$")
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
class IterWorkspaceCleanup:
    workspace: HerdrWorkspace
    kept_tabs: tuple[HerdrTab, ...]
    closed_tabs: tuple[HerdrTab, ...]


@dataclass(frozen=True, slots=True)
class IterWorkspaceStatus:
    workspace: HerdrWorkspace
    tabs: tuple[HerdrTab, ...]
    kept_tabs: tuple[HerdrTab, ...]
    closable_tabs: tuple[HerdrTab, ...]
    latest_iteration: int | None
    latest_agent: HerdrAgent | None
    latest_agent_tab: HerdrTab | None


def clean_iter_workspaces_loop(*, continuous: bool, report: Callable[[str], None]) -> None:
    while True:
        summaries = clean_iter_workspaces()
        _report_summaries(summaries=summaries, report=report)
        if not continuous:
            return
        sleep(LOOP_INTERVAL_SECONDS)


def show_iter_status() -> None:
    _CONSOLE.print(build_iter_status_table(statuses=get_iter_workspace_statuses()))


def get_iter_workspace_statuses() -> tuple[IterWorkspaceStatus, ...]:
    workspaces = _iter_workspaces(workspaces=_list_workspaces())
    tabs_by_workspace_id = _tabs_by_workspace_id(tabs=_list_tabs())
    agents_by_workspace_id = _agents_by_workspace_id(agents=_list_agents())
    statuses: list[IterWorkspaceStatus] = []
    for workspace in workspaces:
        tabs = tuple(sorted(tabs_by_workspace_id.get(workspace.workspace_id, ()), key=lambda tab: tab.number))
        latest_agent = _latest_iter_agent(agents=agents_by_workspace_id.get(workspace.workspace_id, ()))
        kept_tabs = _kept_tabs(tabs=tabs)
        closable_tabs = _closable_tabs(tabs=tabs, kept_tabs=kept_tabs)
        statuses.append(
            IterWorkspaceStatus(
                workspace=workspace,
                tabs=tabs,
                kept_tabs=kept_tabs,
                closable_tabs=closable_tabs,
                latest_iteration=_latest_iteration(agent=latest_agent),
                latest_agent=latest_agent,
                latest_agent_tab=_find_tab(tabs=tabs, tab_id=latest_agent.tab_id) if latest_agent is not None else None,
            )
        )
    return tuple(statuses)


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


def clean_iter_workspaces() -> tuple[IterWorkspaceCleanup, ...]:
    workspaces = _iter_workspaces(workspaces=_list_workspaces())
    tabs_by_workspace_id = _tabs_by_workspace_id(tabs=_list_tabs())
    summaries: list[IterWorkspaceCleanup] = []
    for workspace in workspaces:
        tabs = tabs_by_workspace_id.get(workspace.workspace_id, ())
        kept_tabs = _kept_tabs(tabs=tabs)
        closed_tabs = _closable_tabs(tabs=tabs, kept_tabs=kept_tabs)
        for tab in closed_tabs:
            _run_herdr(["herdr", "tab", "close", tab.tab_id])
        summaries.append(IterWorkspaceCleanup(workspace=workspace, kept_tabs=kept_tabs, closed_tabs=closed_tabs))
    return tuple(summaries)


def _report_summaries(*, summaries: tuple[IterWorkspaceCleanup, ...], report: Callable[[str], None]) -> None:
    if len(summaries) == 0:
        report("No iter workspaces found.")
        return
    total_closed = sum(len(summary.closed_tabs) for summary in summaries)
    report(f"Closed {total_closed} tab(s) across {len(summaries)} iter workspace(s).")
    for summary in summaries:
        report(
            f"- {summary.workspace.label}: closed={len(summary.closed_tabs)} kept={len(summary.kept_tabs)} "
            f"workspace={summary.workspace.workspace_id}"
        )


def _iter_workspaces(*, workspaces: tuple[HerdrWorkspace, ...]) -> tuple[HerdrWorkspace, ...]:
    return tuple(workspace for workspace in workspaces if workspace.label.startswith(ITER_WORKSPACE_PREFIX))


def _kept_tabs(*, tabs: tuple[HerdrTab, ...]) -> tuple[HerdrTab, ...]:
    return tuple(sorted(tabs, key=lambda tab: tab.number, reverse=True)[:KEEP_RECENT_TABS])


def _closable_tabs(*, tabs: tuple[HerdrTab, ...], kept_tabs: tuple[HerdrTab, ...]) -> tuple[HerdrTab, ...]:
    kept_tab_ids = {tab.tab_id for tab in kept_tabs}
    return tuple(tab for tab in sorted(tabs, key=lambda tab: tab.number) if tab.tab_id not in kept_tab_ids)


def _tabs_by_workspace_id(*, tabs: tuple[HerdrTab, ...]) -> dict[str, tuple[HerdrTab, ...]]:
    grouped: dict[str, list[HerdrTab]] = {}
    for tab in tabs:
        grouped.setdefault(tab.workspace_id, []).append(tab)
    return {workspace_id: tuple(workspace_tabs) for workspace_id, workspace_tabs in grouped.items()}


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


def _find_tab(*, tabs: tuple[HerdrTab, ...], tab_id: str) -> HerdrTab | None:
    for tab in tabs:
        if tab.tab_id == tab_id:
            return tab
    return None


def _latest_iteration(*, agent: HerdrAgent | None) -> int | None:
    if agent is None or agent.name is None:
        return None
    return _iteration_from_label(label=agent.name)


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
    return f"{len(status.tabs)} old {len(status.closable_tabs)}"


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
