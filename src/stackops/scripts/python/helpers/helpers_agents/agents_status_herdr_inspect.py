import os
from dataclasses import replace
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_status_assessment import assess_status, describe_activity
from stackops.scripts.python.helpers.helpers_agents.agents_status_herdr import query_herdr
from stackops.scripts.python.helpers.helpers_agents.agents_status_history import read_history
from stackops.scripts.python.helpers.helpers_agents.agents_status_inspect import PaneInspection
from stackops.scripts.python.helpers.helpers_agents.agents_status_links import readable_status_path
from stackops.scripts.python.helpers.helpers_agents.agents_status_models import AgentSnapshot, JsonObject, StatusOptions
from stackops.scripts.python.helpers.helpers_agents.agents_status_processes import inspect_processes
from stackops.scripts.python.helpers.helpers_agents.agents_status_tuios import json_object, text_field


def inspect_herdr_window(
    *, options: StatusOptions, pane: JsonObject, registered: JsonObject, session_id: str,
    workspace_names: dict[int, str], ancestors: set[int],
) -> PaneInspection:
    session = text_field(pane, ("session",))
    window_id = text_field(pane, ("window_id",))
    name = text_field(pane, ("name", "label"))
    if not window_id or not session:
        return PaneInspection(agent=None, candidate=pane, excluded="", limitations=("Herdr pane has no stable pane/session identity.",))
    observer_session = os.environ.get("HERDR_SESSION", "default")
    if not options.include_self and session == observer_session and window_id == os.environ.get("HERDR_PANE_ID"):
        return PaneInspection(agent=None, candidate=None, excluded=f"""{session} / {window_id}""", limitations=())
    process_payload, process_error = query_herdr(
        options=options, session=session, arguments=["pane", "process-info", "--pane", window_id],
    )
    process_info = json_object(json_object(json_object(process_payload).get("result")).get("process_info"))
    root_value = process_info.get("shell_pid")
    root_pid = root_value if isinstance(root_value, int) else 0
    if not options.include_self and root_pid in ancestors:
        return PaneInspection(agent=None, candidate=None, excluded=f"""{session} / {window_id}""", limitations=())
    hint = (text_field(registered, ("agent", "display_agent")) or text_field(pane, ("agent", "display_agent"))).lower()
    if hint in {"claude", "claude code"}:
        hint = "claude-code"
    cwd = text_field(registered, ("foreground_cwd", "cwd")) or text_field(pane, ("foreground_cwd", "cwd"))
    identity = json_object(registered.get("agent_session") or pane.get("agent_session"))
    identity_harness = text_field(identity, ("agent",)).lower()
    if identity_harness in {"claude", "claude code"}:
        identity_harness = "claude-code"
    registered_id = text_field(identity, ("value",)) if identity.get("kind") == "id" and identity_harness == hint else ""
    process = inspect_processes(
        root_pid=root_pid, harness_hint=hint, agent_session_id=registered_id, cwd=cwd,
        claude_home=options.claude_home, codex_home=options.codex_home, timeout=options.timeout,
    )
    errors = [process_error] if process_error is not None else []
    if not registered and not hint and not process.harness:
        if process.live is None:
            errors.extend(process.limitations)
        candidate: JsonObject | None = {"session": session, "window_id": window_id, "name": name, "reason": "; ".join(errors)} if errors else None
        return PaneInspection(agent=None, candidate=candidate, excluded="", limitations=tuple(errors))
    harness = process.harness or hint or "unknown"
    if identity and identity_harness != harness:
        errors.append("Herdr's reported transcript harness conflicts with the inspected agent; its reference was not used.")
    elif identity.get("kind") == "path" and (path := text_field(identity, ("value",))):
        try:
            reported_path = readable_status_path(path=Path(path))
            if process.transcript_paths and reported_path not in process.transcript_paths:
                errors.append("Herdr's reported transcript path conflicts with the live process transcript; its path was not used.")
            else:
                process = replace(process, transcript_paths=(reported_path,))
        except (OSError, ValueError) as error:
            errors.append(str(error))
    capture_payload, capture_error = query_herdr(
        options=options, session=session, arguments=["pane", "read", window_id, "--source", "visible", "--format", "text"],
    )
    if capture_error is not None:
        errors.append(capture_error)
    capture_data = json_object(json_object(json_object(capture_payload).get("result")).get("read"))
    capture = text_field(capture_data, ("text",))
    if options.capture_lines:
        capture = "\n".join(capture.splitlines()[-options.capture_lines:])
    if options.text_limit and len(capture) > options.text_limit:
        capture = capture[:options.text_limit] + " [capture truncated by --text-limit]"
    if capture_data.get("truncated") is True:
        errors.append("Herdr marked the pane capture as truncated.")
    state: JsonObject = {
        "state": text_field(registered, ("agent_status",)) or text_field(pane, ("agent_status",)),
        "source": "Herdr session snapshot",
    }
    history = read_history(
        harness=harness, paths=process.transcript_paths, events=[], mode=options.history,
        message_limit=options.message_limit, text_limit=options.text_limit, backend=options.backend,
    )
    status, task_status, evidence, conflicts = assess_status(state=state, prompt={}, process=process, detector={}, backend=options.backend)
    if state["state"] == "idle" and isinstance(registered.get("completion_seq"), int):
        task_status = "reported completed"
        evidence.append("Herdr marks this idle transition as completed work, even after its completion notification was viewed.")
    task, activity = describe_activity(state=state, history=history, events=[], text_limit=options.text_limit)
    workspace = pane.get("workspace")
    workspace_number = workspace if isinstance(workspace, int) else None
    limitations = [*errors, *process.limitations, *history.limitations, *conflicts]
    limitations.append("Herdr capture includes only the visible viewport, subject to --lines and --text-limit; retained scrollback is not inspected.")
    if capture:
        evidence.append("Read-only visible pane capture is included as terminal evidence, not a conversation transcript.")
    else:
        limitations.append("No pane capture text was available for corroboration.")
    agent = AgentSnapshot(
        session=session, session_id=session_id, workspace=workspace_number,
        workspace_name=workspace_names.get(workspace_number, "") if workspace_number is not None else "",
        workspace_id=text_field(pane, ("workspace_id",)), tab_id=text_field(pane, ("tab_id",)), tab_name=text_field(pane, ("tab_name",)),
        window_id=window_id, window_name=name, harness=harness, cwd=process.cwd or cwd, process=process,
        status=status, task_status=task_status, reported_state=text_field(state, ("state",)), task=task, latest_activity=activity,
        history=history, prompt={}, capture=capture, events=(), evidence=tuple(evidence), limitations=tuple(dict.fromkeys(limitations)),
    )
    return PaneInspection(agent=agent, candidate=None, excluded="", limitations=())
