from stackops.scripts.python.helpers.helpers_sessions._attach_common import (
    interactive_choose_with_preview,
)
from stackops.scripts.python.helpers.helpers_sessions.herdr_export_source import (
    JsonObject,
    entry_int,
    list_workspace_entries,
    workspace_display_name,
    workspace_id,
    workspace_label,
)


def _parse_workspace_names(workspace_names: str) -> list[str]:
    parsed_names = [
        token.strip()
        for token in workspace_names.split(",")
        if token.strip()
    ]
    if len(parsed_names) == 0:
        raise ValueError("No Herdr workspaces were provided.")
    return list(dict.fromkeys(parsed_names))


def _workspace_preview(workspace: JsonObject) -> str:
    lines = [
        "backend: herdr",
        f"workspace: {workspace_display_name(workspace)}",
        f"id: {workspace_id(workspace) or ''}",
        f"focused: {'yes' if workspace.get('focused') else 'no'}",
    ]
    tab_count = entry_int(workspace, "tab_count")
    pane_count = entry_int(workspace, "pane_count")
    if tab_count is not None:
        lines.append(f"tabs: {tab_count}")
    if pane_count is not None:
        lines.append(f"panes: {pane_count}")
    return "\n".join(lines)


def _choice_label_for_workspace(
    workspace: JsonObject,
    used_labels: set[str],
) -> str:
    base_label = workspace_display_name(workspace)
    workspace_id_value = workspace_id(workspace)
    label = base_label
    if label in used_labels and workspace_id_value is not None:
        label = f"{base_label} ({workspace_id_value})"
    suffix = 2
    while label in used_labels:
        label = f"{base_label} ({suffix})"
        suffix += 1
    used_labels.add(label)
    return label


def _choose_herdr_workspaces_interactively(workspaces: list[JsonObject]) -> list[JsonObject]:
    used_labels: set[str] = set()
    options_to_workspaces: dict[str, JsonObject] = {}
    options_to_preview: dict[str, str] = {}
    for workspace in workspaces:
        option_label = _choice_label_for_workspace(
            workspace=workspace,
            used_labels=used_labels,
        )
        options_to_workspaces[option_label] = workspace
        options_to_preview[option_label] = _workspace_preview(workspace=workspace)
    selected_labels = interactive_choose_with_preview(
        msg="Choose Herdr workspaces to export:",
        options_to_preview_mapping=options_to_preview,
        multi=True,
    )
    if len(selected_labels) == 0:
        raise ValueError("No Herdr workspaces selected.")
    return [options_to_workspaces[label] for label in selected_labels]


def _workspace_matches_selector(workspace: JsonObject, selector: str) -> bool:
    return selector in {
        workspace_label(workspace),
        workspace_id(workspace),
    }


def _workspace_identity(workspace: JsonObject) -> str:
    identity = workspace_id(workspace) or workspace_label(workspace)
    if identity is None:
        raise ValueError("Herdr workspace cannot be selected because it has no label or workspace_id.")
    return identity


def _validate_requested_workspaces(
    requested_workspaces: list[str],
    available_workspaces: list[JsonObject],
) -> list[JsonObject]:
    selected_workspaces: list[JsonObject] = []
    selected_identities: set[str] = set()
    missing_workspaces: list[str] = []
    for requested_workspace in requested_workspaces:
        matching_workspaces = [
            workspace
            for workspace in available_workspaces
            if _workspace_matches_selector(
                workspace=workspace,
                selector=requested_workspace,
            )
        ]
        if len(matching_workspaces) == 0:
            missing_workspaces.append(requested_workspace)
            continue
        if len(matching_workspaces) > 1:
            raise ValueError(
                f"Herdr workspace selector '{requested_workspace}' matched multiple workspaces. "
                "Use the workspace_id instead."
            )
        matched_workspace = matching_workspaces[0]
        identity = _workspace_identity(workspace=matched_workspace)
        if identity not in selected_identities:
            selected_identities.add(identity)
            selected_workspaces.append(matched_workspace)
    if len(missing_workspaces) == 0:
        return selected_workspaces
    available_names = [
        workspace_display_name(workspace)
        for workspace in available_workspaces
    ]
    raise ValueError(
        f"Unknown Herdr workspace(s): {missing_workspaces}. "
        f"Available workspaces: {available_names}"
    )


def resolve_herdr_workspaces_for_export(
    workspace_names: str | None,
    export_all_workspaces: bool,
) -> list[JsonObject]:
    workspaces = list_workspace_entries()
    if len(workspaces) == 0:
        raise ValueError("No Herdr workspaces are available to export.")
    if export_all_workspaces and workspace_names is not None:
        raise ValueError("--all cannot be used together with --sessions.")
    if export_all_workspaces:
        return workspaces
    if workspace_names is None or workspace_names == "":
        return _choose_herdr_workspaces_interactively(workspaces=workspaces)
    requested_workspaces = _parse_workspace_names(workspace_names=workspace_names)
    return _validate_requested_workspaces(
        requested_workspaces=requested_workspaces,
        available_workspaces=workspaces,
    )
