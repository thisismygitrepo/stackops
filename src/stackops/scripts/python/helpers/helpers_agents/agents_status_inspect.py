import os
from dataclasses import dataclass

from stackops.scripts.python.helpers.helpers_agents.agents_status_assessment import assess_status, describe_activity
from stackops.scripts.python.helpers.helpers_agents.agents_status_history import read_history
from stackops.scripts.python.helpers.helpers_agents.agents_status_models import AgentSnapshot, JsonObject, StatusOptions
from stackops.scripts.python.helpers.helpers_agents.agents_status_processes import inspect_processes
from stackops.scripts.python.helpers.helpers_agents.agents_status_tuios import json_object, object_rows, query_tuios, text_field


@dataclass(frozen=True)
class PaneInspection:
    agent: AgentSnapshot | None
    candidate: JsonObject | None
    excluded: str
    limitations: tuple[str, ...]


def inspect_window(
    *, options: StatusOptions, pane: JsonObject, registered: JsonObject, session_id: str,
    workspace_names: dict[int, str], ancestors: set[int],
) -> PaneInspection:
    session = text_field(pane, ("session",))
    window_id = text_field(pane, ("window_id",))
    name = text_field(pane, ("name", "title"))
    if not window_id or not session:
        return PaneInspection(agent=None, candidate=pane, excluded="", limitations=("Window inventory has no stable window/session identity.",))
    observer = os.environ.get("TUIOS_PANE_ID") or os.environ.get("TUIOS_WINDOW_ID")
    if not options.include_self and window_id == observer:
        return PaneInspection(agent=None, candidate=None, excluded=window_id, limitations=())
    target = ["--session", session]
    details_payload, detail_error = query_tuios(options=options, arguments=["get-window", window_id, *target, "--json"])
    details = json_object(details_payload)
    root_value = details.get("pid") or details.get("shell_pgid") or pane.get("pid")
    root_pid = root_value if isinstance(root_value, int) else 0
    if not options.include_self and root_pid in ancestors:
        return PaneInspection(agent=None, candidate=None, excluded=window_id, limitations=())
    detector_payload, detector_error = query_tuios(
        options=options, arguments=["explain-agent-detect", *target, "--window", window_id, "--json"]
    )
    detector = json_object(detector_payload)
    hint = text_field(detector, ("matched_harness", "harness_id")) or text_field(registered, ("harness_id",))
    program_status = registered.get("program_status")
    if not hint and isinstance(program_status, list):
        applications = {row.get("app") for row in program_status if isinstance(row, dict) and isinstance(row.get("app"), str)}
        if len(applications) == 1:
            hint = str(next(iter(applications)))
    cwd = text_field(pane, ("cwd",)) or text_field(registered, ("cwd",)) or text_field(details, ("cwd",))
    registered_id = text_field(registered, ("agent_session_id",))
    process = inspect_processes(
        root_pid=root_pid, harness_hint=hint, agent_session_id=registered_id, cwd=cwd,
        claude_home=options.claude_home, codex_home=options.codex_home, timeout=options.timeout,
    )
    is_agent = bool(registered) or detector.get("matched") is True or bool(process.harness)
    errors = [error for error in (detail_error, detector_error) if error is not None]
    if not is_agent:
        command = text_field(pane, ("command",))
        if process.live is None:
            errors.extend(process.limitations)
        candidate = {"session": session, "window_id": window_id, "name": name, "command": command, "reason": "; ".join(errors)} if errors else None
        return PaneInspection(agent=None, candidate=candidate, excluded="", limitations=tuple(errors))
    evidence_data: dict[str, JsonObject] = {}
    for verb, extra in (
        ("get-agent-state", []), ("peek-prompt", []), ("agent-log", ["--limit", str(options.event_limit)]),
        ("capture-pane", ["--scrollback", "--lines", str(options.capture_lines)]),
    ):
        payload, error = query_tuios(options=options, arguments=[verb, *target, "--window", window_id, *extra, "--json"])
        evidence_data[verb] = json_object(payload)
        if error is not None:
            errors.append(error)
    state = evidence_data["get-agent-state"]
    if not state:
        state = {"state": registered.get("state", "unknown"), "source": registered.get("source", "inventory")}
    prompt = evidence_data["peek-prompt"]
    events = object_rows(payload=evidence_data["agent-log"], key="entries") if "entries" in evidence_data["agent-log"] else []
    capture_data = evidence_data["capture-pane"]
    capture = text_field(capture_data, ("content", "text"))
    if not capture:
        lines = capture_data.get("lines")
        if isinstance(lines, list):
            capture = "\n".join(line for line in lines if isinstance(line, str))
    if options.text_limit and len(capture) > options.text_limit:
        capture = capture[:options.text_limit] + " [capture truncated by --text-limit]"
    harness = process.harness or hint or "unknown"
    history = read_history(
        harness=harness, paths=process.transcript_paths, events=events, mode=options.history,
        message_limit=options.message_limit, text_limit=options.text_limit,
        backend=options.backend,
    )
    status, task_status, evidence, conflicts = assess_status(state=state, prompt=prompt, process=process, detector=detector, backend=options.backend)
    task, activity = describe_activity(state=state, history=history, events=events, text_limit=options.text_limit)
    workspace = pane.get("workspace")
    workspace_number = workspace if isinstance(workspace, int) else None
    limitations = [*errors, *process.limitations, *history.limitations, *conflicts]
    if options.capture_lines:
        limitations.append(f"""Pane capture is limited to the last {options.capture_lines} retained lines, further subject to --text-limit.""")
    if capture:
        evidence.append("Read-only pane capture is included; it is partial terminal evidence, not a conversation transcript.")
    else:
        limitations.append("No pane capture text was available for corroboration.")
    agent = AgentSnapshot(
        session=session, session_id=session_id, workspace=workspace_number, workspace_name=workspace_names.get(workspace_number, "") if workspace_number is not None else "",
        workspace_id="", tab_id="", tab_name="",
        window_id=window_id, window_name=name, harness=harness, cwd=process.cwd or cwd, process=process,
        status=status, task_status=task_status, reported_state=text_field(state, ("state",)), task=task, latest_activity=activity,
        history=history, prompt=prompt, capture=capture, events=tuple(events), evidence=tuple(evidence), limitations=tuple(dict.fromkeys(limitations)),
    )
    return PaneInspection(agent=agent, candidate=None, excluded="", limitations=())
