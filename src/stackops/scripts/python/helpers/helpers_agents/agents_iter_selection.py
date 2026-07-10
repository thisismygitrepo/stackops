from collections import Counter

from stackops.scripts.python.helpers.helpers_agents.agents_iter_constants import ITER_WORKSPACE_PREVIEW_SIZE_PERCENT
from stackops.scripts.python.helpers.helpers_agents.agents_iter_models import IterWorkspaceStatus


def choose_iter_workspace_id(*, statuses: tuple[IterWorkspaceStatus, ...]) -> str:
    if len(statuses) == 0:
        raise RuntimeError("No Herdr iter workspaces are available for interactive selection.")

    status_by_label = {_selection_label(status=status): status for status in statuses}
    if len(status_by_label) != len(statuses):
        raise RuntimeError("Herdr returned duplicate iter workspace IDs.")
    preview_by_label = {
        label: build_iter_workspace_preview(status=status)
        for label, status in status_by_label.items()
    }

    from stackops.utils.options_utils import tv_options

    try:
        selected_label = tv_options.choose_from_dict_with_preview(
            options_to_preview_mapping=preview_by_label,
            extension="md",
            multi=False,
            preview_size_percent=ITER_WORKSPACE_PREVIEW_SIZE_PERCENT,
        )
    except FileNotFoundError as error:
        raise RuntimeError("Interactive iter workspace selection requires `tv` on PATH.") from error
    if selected_label is None:
        raise RuntimeError("Interactive iter workspace selection was cancelled.")
    selected_status = status_by_label.get(selected_label)
    if selected_status is None:
        raise RuntimeError(f"Interactive selection did not map to an iter workspace: {selected_label}")
    return str(selected_status.workspace.workspace_id)


def build_iter_workspace_preview(*, status: IterWorkspaceStatus) -> str:
    workspace = status.workspace
    plan = status.plan
    latest_agent = status.latest_agent
    latest_tab = status.latest_agent_tab
    latest_iteration_label = "-" if status.latest_iteration is None else f"{status.latest_iteration:03d}"
    latest_agent_label = "-"
    latest_agent_status = "-"
    latest_agent_location = "-"
    if latest_agent is not None:
        latest_agent_label = latest_agent.display_agent or latest_agent.agent or latest_agent.name or "-"
        latest_agent_status = latest_agent.agent_status
        latest_agent_location = latest_agent.foreground_cwd or latest_agent.cwd or "-"
    elif latest_tab is not None:
        latest_agent_status = latest_tab.agent_status

    protection_counts = Counter(item.reason for item in plan.protected_tabs)
    protection_summary = ", ".join(f"{reason}={count}" for reason, count in sorted(protection_counts.items())) or "-"
    close_candidates = [
        f"- `#{tab.number}` `{tab.label}` (`{tab.tab_id}`) — {tab.agent_status}"
        for tab in plan.closable_tabs
    ] or ["- None"]
    retained_tabs = [
        f"- `#{tab.number}` `{tab.label}` (`{tab.tab_id}`)"
        for tab in plan.retained_tabs
    ] or ["- None"]
    protected_tabs = [
        f"- `#{item.tab.number}` `{item.tab.label}` (`{item.tab.tab_id}`) — {item.reason}"
        for item in plan.protected_tabs
    ] or ["- None"]

    return "\n".join(
        (
            f"# {workspace.label}",
            "",
            f"- Workspace ID: `{workspace.workspace_id}`",
            f"- Workspace number: `{workspace.number}`",
            f"- Workspace status: `{workspace.agent_status}`",
            f"- Focused: `{str(workspace.focused).lower()}`",
            f"- Tabs: `{workspace.tab_count}`",
            f"- Panes: `{workspace.pane_count}`",
            f"- Latest iteration: `{latest_iteration_label}`",
            f"- Latest agent: `{latest_agent_label}`",
            f"- Latest agent status: `{latest_agent_status}`",
            f"- Latest agent location: `{latest_agent_location}`",
            "",
            "## Close plan",
            "",
            f"- Close: `{len(plan.closable_tabs)}`",
            f"- Retain: `{len(plan.retained_tabs)}`",
            f"- Protect: `{len(plan.protected_tabs)}` ({protection_summary})",
            "",
            "### Close candidates",
            "",
            *close_candidates,
            "",
            "### Retained tabs",
            "",
            *retained_tabs,
            "",
            "### Protected tabs",
            "",
            *protected_tabs,
            "",
        )
    )


def _selection_label(*, status: IterWorkspaceStatus) -> str:
    return f"{status.workspace.label} [{status.workspace.workspace_id}]"
