from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime

from stackops.scripts.python.helpers.helpers_agents.agents_status_aoe import read_aoe_inventory, read_aoe_panes
from stackops.scripts.python.helpers.helpers_agents.agents_status_aoe_inspect import inspect_aoe_window
from stackops.scripts.python.helpers.helpers_agents.agents_status_herdr import read_herdr_inventory, read_herdr_panes
from stackops.scripts.python.helpers.helpers_agents.agents_status_herdr_inspect import inspect_herdr_window
from stackops.scripts.python.helpers.helpers_agents.agents_status_inspect import PaneInspection, inspect_window
from stackops.scripts.python.helpers.helpers_agents.agents_status_models import AgentSnapshot, JsonObject, StatusOptions, StatusSnapshot
from stackops.scripts.python.helpers.helpers_agents.agents_status_tuios import (
    object_rows,
    observer_ancestors,
    query_tuios,
    read_inventory,
    text_field,
    validate_history_roots,
)


def _window_matches(*, pane: JsonObject, names: tuple[str, ...]) -> bool:
    identities = {text_field(pane, (key,)) for key in ("window_id", "name", "title", "label")}
    return not names or bool(identities.intersection(names))


def _selected_agent(*, agent: AgentSnapshot, options: StatusOptions) -> bool:
    harnesses = {"claude-code" if value == "claude" else value for value in options.harnesses}
    state_matches = not options.states or agent.status in options.states
    if "completed" in options.states and agent.task_status == "reported completed":
        state_matches = True
    return (not harnesses or agent.harness in harnesses) and state_matches


def collect_status(options: StatusOptions) -> StatusSnapshot:
    started_at = datetime.now(UTC).isoformat()
    validate_history_roots(options=options)
    inventory = {"tuios": read_inventory, "herdr": read_herdr_inventory, "aoe": read_aoe_inventory}[options.backend]
    sessions, all_panes, registrations, limitations = inventory(options=options)
    live_sessions = [session for session in sessions if not session.get("saved")]
    selected_sessions = [
        session for session in live_sessions
        if not options.sessions or {text_field(session, (key,)) for key in ("name", "id", "title")}.intersection(options.sessions)
    ]
    for requested in options.sessions:
        if not any(requested in {session.get("name"), session.get("id"), session.get("title")} for session in selected_sessions):
            raise ValueError(f"""Requested session is not live: {requested}. Saved sessions are never restored.""")
    session_by_name = {text_field(session, ("name",)): session for session in selected_sessions}
    panes = [pane for pane in all_panes if pane.get("session") in session_by_name]
    for requested in options.windows:
        if not any(_window_matches(pane=pane, names=(requested,)) for pane in panes):
            raise ValueError(f"""Requested window is not present in the selected live sessions: {requested}""")
    excluded_keys = {
        (text_field(pane, ("session",)), text_field(pane, ("window_id",)))
        for pane in panes if options.exclude_windows and _window_matches(pane=pane, names=options.exclude_windows)
    }
    explicitly_excluded = [f"""{session} / {window_id}""" if options.backend != "tuios" else window_id for session, window_id in sorted(excluded_keys)]
    panes = [
        pane for pane in panes if _window_matches(pane=pane, names=options.windows)
        and (text_field(pane, ("session",)), text_field(pane, ("window_id",))) not in excluded_keys
    ]
    registered_by_window = {
        (text_field(agent, ("session",)) if options.backend != "tuios" else "", text_field(agent, ("window_id",))): agent
        for agent in registrations
    }
    workspace_names: dict[str, dict[int, str]] = {}
    workspace_count = 0
    workspace_results: list[tuple[object, str | None]]
    if options.backend != "tuios":
        workspace_results = [({"workspaces": session["workspaces"]}, None) for session in selected_sessions]
    else:
        with ThreadPoolExecutor(max_workers=options.workers) as executor:
            workspace_results = list(executor.map(
                lambda name: query_tuios(options=options, arguments=["list-workspaces", "--session", name, "--json"]), session_by_name
            ))
    for name, (payload, error) in zip(session_by_name, workspace_results, strict=True):
        if error is not None:
            limitations.append(f"""Session {name}: {error}""")
        workspaces = object_rows(payload=payload, key="workspaces") if error is None else []
        workspace_count += len(workspaces)
        workspace_names[name] = {
            number: text_field(workspace, ("name", "label"))
            for workspace in workspaces if isinstance(number := workspace.get("number" if options.backend == "herdr" else "workspace"), int)
        }
    if options.backend == "aoe":
        workspace_count = len({
            text_field(pane, ("group",)) for pane in panes if text_field(pane, ("group",))
        })
    ancestors, ancestry_error = observer_ancestors()
    if ancestry_error is not None and not options.include_self:
        limitations.append(ancestry_error)

    def inspect(pane: JsonObject) -> PaneInspection:
        name = text_field(pane, ("session",))
        inspector = {"tuios": inspect_window, "herdr": inspect_herdr_window, "aoe": inspect_aoe_window}[options.backend]
        return inspector(
            options=options, pane=pane, registered=registered_by_window.get((name if options.backend != "tuios" else "", text_field(pane, ("window_id",))), {}),
            session_id=text_field(session_by_name[name], ("id",)), workspace_names=workspace_names[name], ancestors=ancestors,
        )

    with ThreadPoolExecutor(max_workers=options.workers) as executor:
        inspected = list(executor.map(inspect, panes))
    agents = [result.agent for result in inspected if result.agent is not None]
    candidates = [result.candidate for result in inspected if result.candidate is not None]
    excluded = [*explicitly_excluded, *(result.excluded for result in inspected if result.excluded)]
    for result in inspected:
        limitations.extend(result.limitations)
    vanished: list[JsonObject] = []
    new_windows: list[JsonObject] = []
    if live_sessions:
        if options.backend == "herdr":
            final_panes, final_error = read_herdr_panes(options=options, sessions=tuple(session_by_name))
        elif options.backend == "aoe":
            final_panes, final_error = read_aoe_panes(options=options, sessions=tuple(selected_sessions))
        else:
            final_payload, final_error = query_tuios(options=options, arguments=["list-windows", "--all", "--json"])
            final_panes = object_rows(payload=final_payload, key="panes") if final_error is None else []
        if final_error is not None:
            limitations.append(f"""Final window inventory unavailable; disappearance could not be checked: {final_error}""")
        else:
            initial_ids = {(text_field(pane, ("session",)), text_field(pane, ("window_id",))) for pane in all_panes}
            final_ids = {(text_field(pane, ("session",)), text_field(pane, ("window_id",))) for pane in final_panes}
            vanished = [
                {"session": pane.get("session"), "window_id": pane.get("window_id"), "name": pane.get("name"), "status": "unavailable"}
                for pane in panes if (text_field(pane, ("session",)), text_field(pane, ("window_id",))) not in final_ids
            ]
            new_windows = [
                {"session": pane.get("session"), "window_id": pane.get("window_id"), "name": pane.get("name")}
                for pane in final_panes if (text_field(pane, ("session",)), text_field(pane, ("window_id",))) not in initial_ids and pane.get("session") in session_by_name
            ]
            vanished_ids = {(row.get("session"), row.get("window_id")) for row in vanished}
            agents = [
                replace(agent, status="unavailable", limitations=(*agent.limitations, "Window disappeared before the final inventory; exit reason unknown."))
                if (agent.session, agent.window_id) in vanished_ids else agent for agent in agents
            ]
    if new_windows:
        limitations.append("New windows appeared after initial discovery; listed in coverage but not inspected in this snapshot.")
    if any(pane.get("command") == "ssh" for pane in panes):
        limitations.append("Remote background processes behind SSH windows cannot be identified through local process metadata.")
    selected = tuple(agent for agent in agents if _selected_agent(agent=agent, options=options))
    coverage: JsonObject = {
        "live_sessions": len(live_sessions), "sessions_inspected": len(selected_sessions),
        "sessions": [{key: session.get(key) for key in ("name", "id", "attached", "window_count")} for session in selected_sessions], "workspace_records": workspace_count,
        "windows_discovered": len(all_panes), "windows_inspected": len(panes), "agents_found": len(agents), "agents_shown": len(selected),
        "status_counts": dict(Counter(agent.status for agent in selected)),
        "task_status_counts": dict(Counter(agent.task_status for agent in selected)),
        "saved_sessions_skipped": [session for session in sessions if session.get("saved")], "excluded_windows": excluded,
        "ambiguous_candidates": candidates, "vanished_windows": vanished, "new_windows_not_inspected": new_windows,
        "capture_line_limit": options.capture_lines, "message_limit": options.message_limit, "text_limit": options.text_limit,
        "scope": {
            "tuios": "Local TUIOS daemon only; detached sessions and background workspaces included. Separate tabs/nested pane IDs are unavailable.",
            "herdr": "Local Herdr sessions; detached sessions, background workspaces, tabs and panes included.",
            "aoe": "Current local AoE profile; tmux sessions and structured-view workers included. Each AoE session is one runtime target.",
        }[options.backend],
    }
    return StatusSnapshot(
        backend=options.backend, started_at=started_at, observed_at=datetime.now(UTC).isoformat(), server=options.server,
        agents=selected, coverage=coverage, limitations=tuple(dict.fromkeys(limitations)),
    )
