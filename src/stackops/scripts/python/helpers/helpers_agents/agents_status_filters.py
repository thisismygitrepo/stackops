from typing import Literal

from stackops.scripts.python.helpers.helpers_agents.agents_status_models import AgentSnapshot, JsonObject, StatusBackend, StatusOptions
from stackops.scripts.python.helpers.helpers_agents.agents_status_tuios import text_field


type LayoutLevel = Literal["layout", "tab", "pane"]


def _layout_identities(
    *, pane: JsonObject, session: JsonObject, workspace_names: dict[int, str], backend: StatusBackend,
) -> dict[LayoutLevel, set[str]]:
    session_values = {text_field(session, (key,)) for key in ("name", "id", "title")}
    workspace_values = {text_field(pane, (key,)) for key in ("workspace_id", "workspace_name")}
    if isinstance(number := pane.get("workspace"), int):
        workspace_values.update((str(number), workspace_names.get(number, "")))
    pane_values = {text_field(pane, (key,)) for key in ("window_id", "name", "display_name", "title", "label")}
    match backend:
        case "tuios":
            layout_values, tab_values = session_values, workspace_values
        case "herdr":
            layout_values = workspace_values
            tab_values = {text_field(pane, (key,)) for key in ("tab_id", "tab_name")}
        case "aoe":
            layout_values, tab_values = {text_field(pane, ("group",))}, session_values
    identities: dict[LayoutLevel, set[str]] = {"layout": layout_values, "tab": tab_values, "pane": pane_values}
    for values in identities.values():
        values.discard("")
    return identities


def select_status_panes(
    *, panes: list[JsonObject], sessions: dict[str, JsonObject], workspace_names: dict[str, dict[int, str]], options: StatusOptions,
) -> tuple[list[JsonObject], list[str]]:
    candidates = [
        (pane, _layout_identities(
            pane=pane, session=sessions[text_field(pane, ("session",))],
            workspace_names=workspace_names[text_field(pane, ("session",))], backend=options.backend,
        ))
        for pane in panes
    ]
    selections: tuple[tuple[LayoutLevel, tuple[str, ...]], ...] = (
        ("layout", options.layouts), ("tab", options.tabs), ("pane", options.windows),
    )
    for level, requested_values in selections:
        for requested in requested_values:
            if not any(requested in identities[level] for _pane, identities in candidates):
                raise ValueError(f"""Requested --{level} is not present in the selected live scope: {requested}""")
        if requested_values:
            candidates = [(pane, identities) for pane, identities in candidates if identities[level].intersection(requested_values)]
    selected: list[JsonObject] = []
    excluded: list[str] = []
    for pane, identities in candidates:
        if identities["pane"].intersection(options.exclude_windows):
            session, window_id = text_field(pane, ("session",)), text_field(pane, ("window_id",))
            excluded.append(window_id if options.backend == "tuios" else f"""{session} / {window_id}""")
        else:
            selected.append(pane)
    return selected, sorted(excluded)


def selected_agent(*, agent: AgentSnapshot, options: StatusOptions) -> bool:
    harnesses = {"claude-code" if value == "claude" else value for value in options.harnesses}
    state_matches = not options.states or agent.status in options.states
    if "completed" in options.states and agent.task_status == "reported completed":
        state_matches = True
    identities = {agent.agent_session_name, agent.process.session_id}
    if options.backend == "aoe":
        identities.add(agent.session_id)
    identities.discard("")
    session_matches = not options.agent_sessions or bool(identities.intersection(options.agent_sessions))
    return (not harnesses or agent.harness in harnesses) and state_matches and session_matches
