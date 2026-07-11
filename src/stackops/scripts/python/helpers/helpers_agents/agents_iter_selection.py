from collections import Counter
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_agentops_cache import AgentopsCacheCleanResult
from stackops.scripts.python.helpers.helpers_agents.agents_iter_constants import ITER_WORKSPACE_PREVIEW_SIZE_PERCENT
from stackops.scripts.python.helpers.helpers_agents.agents_iter_models import IterWorkspaceStatus, WorkspaceId
from stackops.scripts.python.helpers.helpers_agents.agents_iter_records import IterRunManifest, load_iter_run_manifest


def choose_iter_workspace_id(*, statuses: tuple[IterWorkspaceStatus, ...]) -> str:
    if len(statuses) == 0:
        raise RuntimeError("No Herdr iter workspaces are available for interactive selection.")

    status_by_label = {_selection_label(status=status): status for status in statuses}
    if len(status_by_label) != len(statuses):
        raise RuntimeError("Herdr iter workspaces produce duplicate interactive selection labels.")
    preview_by_label = {label: build_iter_workspace_preview(status=status) for label, status in status_by_label.items()}

    selected_label = _choose_preview_label(preview_by_label=preview_by_label, selection_name="iter workspace")
    selected_status = status_by_label.get(selected_label)
    if selected_status is None:
        raise RuntimeError(f"Interactive selection did not map to an iter workspace: {selected_label}")
    return str(selected_status.workspace.workspace_id)


def choose_agentops_cache_workspace_id(*, result: AgentopsCacheCleanResult) -> WorkspaceId:
    inactive_paths = frozenset(result.removed_runs)
    run_paths = tuple(sorted((*result.removed_runs, *result.protected_runs), key=lambda path: path.name))
    if len(run_paths) == 0:
        raise RuntimeError("No current AgentOps iteration runs are available for interactive selection.")

    manifest_by_label: dict[str, IterRunManifest] = {}
    preview_by_label: dict[str, str] = {}
    workspace_ids: set[WorkspaceId] = set()
    for run_path in run_paths:
        manifest = load_iter_run_manifest(run_path=run_path)
        if manifest is None:
            raise RuntimeError(f"AgentOps iteration run changed before interactive selection: {run_path}")
        label = f"{manifest.workspace_label} [{manifest.workspace_id}]"
        if manifest.workspace_id in workspace_ids:
            raise RuntimeError(f"AgentOps iteration records contain duplicate workspace ID {manifest.workspace_id!r}.")
        if label in manifest_by_label:
            raise RuntimeError(f"AgentOps iteration records produce duplicate selection label {label!r}.")
        workspace_ids.add(manifest.workspace_id)
        manifest_by_label[label] = manifest
        preview_by_label[label] = build_agentops_cache_preview(
            run_path=run_path, manifest=manifest, active=run_path not in inactive_paths, project_root=result.project_root
        )

    selected_label = _choose_preview_label(preview_by_label=preview_by_label, selection_name="AgentOps iteration run")
    selected_manifest = manifest_by_label.get(selected_label)
    if selected_manifest is None:
        raise RuntimeError(f"Interactive selection did not map to an AgentOps iteration run: {selected_label}")
    return selected_manifest.workspace_id


def build_agentops_cache_preview(*, run_path: Path, manifest: IterRunManifest, active: bool, project_root: Path) -> str:
    try:
        display_path = f"./{run_path.relative_to(project_root).as_posix()}"
    except ValueError:
        display_path = run_path.as_posix()
    state = "active" if active else "inactive"
    action = "protect" if active else "remove"
    return "\n".join(
        (
            f"# {manifest.workspace_label}",
            "",
            f"- Workspace ID: `{manifest.workspace_id}`",
            f"- Herdr session: `{manifest.herdr_session}`",
            f"- Record path: `{display_path}`",
            f"- Current state: `{state}`",
            f"- Clean action: `{action}`",
            "",
        )
    )


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
    close_candidates = [f"- `#{tab.number}` `{tab.label}` (`{tab.tab_id}`) — {tab.agent_status}" for tab in plan.closable_tabs] or ["- None"]
    retained_tabs = [f"- `#{tab.number}` `{tab.label}` (`{tab.tab_id}`)" for tab in plan.retained_tabs] or ["- None"]
    protected_tabs = [f"- `#{item.tab.number}` `{item.tab.label}` (`{item.tab.tab_id}`) — {item.reason}" for item in plan.protected_tabs] or [
        "- None"
    ]

    return "\n".join(
        (
            f"# {workspace.label}",
            "",
            f"- Workspace ID: `{workspace.workspace_id}`",
            f"- Workspace number: `{workspace.number}`",
            f"- Workspace status: `{workspace.agent_status}`",
            f"- AgentOps run: `{plan.run_path}`",
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


def _choose_preview_label(*, preview_by_label: dict[str, str], selection_name: str) -> str:
    from stackops.utils.options_utils import tv_options

    try:
        selected_label = tv_options.choose_from_dict_with_preview(
            options_to_preview_mapping=preview_by_label, extension="md", multi=False, preview_size_percent=ITER_WORKSPACE_PREVIEW_SIZE_PERCENT
        )
    except FileNotFoundError as error:
        raise RuntimeError(f"Interactive {selection_name} selection requires `tv` on PATH.") from error
    if selected_label is None:
        raise RuntimeError(f"Interactive {selection_name} selection was cancelled.")
    return selected_label
