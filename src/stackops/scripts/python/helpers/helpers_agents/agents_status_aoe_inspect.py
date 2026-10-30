import psutil

from stackops.scripts.python.helpers.helpers_agents.agents_status_aoe import query_aoe
from stackops.scripts.python.helpers.helpers_agents.agents_status_aoe_acp import inspect_aoe_acp
from stackops.scripts.python.helpers.helpers_agents.agents_status_assessment import assess_status, describe_activity
from stackops.scripts.python.helpers.helpers_agents.agents_status_history import read_history
from stackops.scripts.python.helpers.helpers_agents.agents_status_inspect import PaneInspection
from stackops.scripts.python.helpers.helpers_agents.agents_status_models import AgentSnapshot, JsonObject, ProcessEvidence, StatusOptions
from stackops.scripts.python.helpers.helpers_agents.agents_status_processes import inspect_processes
from stackops.scripts.python.helpers.helpers_agents.agents_status_tuios import json_object, text_field


def inspect_aoe_window(
    *, options: StatusOptions, pane: JsonObject, registered: JsonObject, session_id: str,
    workspace_names: dict[int, str], ancestors: set[int],
) -> PaneInspection:
    session = text_field(pane, ("session",))
    window_id = text_field(pane, ("window_id",))
    root_value = registered.get("pid")
    root_pid = root_value if isinstance(root_value, int) else 0
    if not options.include_self and root_pid in ancestors:
        return PaneInspection(agent=None, candidate=None, excluded=f"""{session} / {window_id}""", limitations=())
    harness = text_field(registered, ("agent", "tool")).lower()
    if harness == "claude":
        harness = "claude-code"
    cwd = text_field(registered, ("cwd", "path"))
    errors: list[str] = []
    capture = ""
    state: JsonObject
    if registered.get("substrate") == "acp":
        live: bool | None = None
        if root_pid > 0:
            try:
                worker = psutil.Process(root_pid)
                live = worker.is_running() and worker.status() != psutil.STATUS_ZOMBIE
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                live = False
            except (psutil.AccessDenied, OSError) as error:
                errors.append(f"""AoE worker process inspection unavailable ({type(error).__name__}).""")
        process = ProcessEvidence(
            pid=root_pid or None, live=live, harness="acp-runner", cwd=cwd, command="", session_id="", transcript_paths=(),
            limitations=("The PID identifies the AoE structured-view runner; worker liveness alone does not establish agent activity.",),
        )
        state, prompt, history = inspect_aoe_acp(options=options, session_id=session_id)
        reported_state = text_field(state, ("state",))
        errors.append("AoE structured-view workers have no terminal pane to capture.")
    else:
        process = inspect_processes(
            root_pid=root_pid, harness_hint=harness, agent_session_id="", cwd=cwd,
            claude_home=options.claude_home, codex_home=options.codex_home, timeout=options.timeout,
        )
        harness = process.harness or harness
        payload, capture_error = query_aoe(options=options, arguments=[
            "session", "capture", session_id, "--profile", text_field(registered, ("profile",)),
            "--json", "--strip-ansi", "--lines", str(options.capture_lines),
        ])
        capture_data = json_object(payload)
        capture = text_field(capture_data, ("content",))
        if capture_error is not None:
            errors.append(capture_error)
        if options.capture_lines:
            capture = "\n".join(capture.splitlines()[-options.capture_lines:])
            errors.append(f"""Pane capture is limited to the last {options.capture_lines} retained lines, subject to --text-limit.""")
        else:
            errors.append("AoE --lines 0 captures the visible viewport; its capture command does not offer unlimited scrollback.")
        if options.text_limit and len(capture) > options.text_limit:
            capture = capture[:options.text_limit] + " [capture truncated by --text-limit]"
        reported_state = text_field(capture_data, ("status",)).lower()
        if not reported_state:
            runtime_state = text_field(registered, ("state",))
            reported_state = runtime_state if runtime_state in {"running", "waiting"} else "unknown"
            errors.append("Detailed AoE agent status is unavailable; coarse runtime idle does not establish agent idleness.")
        state = {
            "state": {"running": "working", "waiting": "needs_input", "error": "failed"}.get(reported_state, reported_state),
            "source": "AoE session capture" if text_field(capture_data, ("status",)) else "AoE runtime inventory",
        }
        prompt = {}
        history = read_history(
            harness=harness, paths=process.transcript_paths, events=[], mode=options.history,
            message_limit=options.message_limit, text_limit=options.text_limit, backend=options.backend,
        )
    status, task_status, evidence, conflicts = assess_status(state=state, prompt=prompt, process=process, detector={}, backend=options.backend)
    task, activity = describe_activity(state=state, history=history, events=[], text_limit=options.text_limit)
    if capture:
        evidence.append("Read-only AoE pane capture is included as terminal evidence, not a conversation transcript.")
    elif registered.get("substrate") == "tmux":
        errors.append("No pane capture text was available for corroboration.")
    workspace = pane.get("workspace")
    workspace_number = workspace if isinstance(workspace, int) else None
    agent = AgentSnapshot(
        session=session, session_id=session_id, workspace=workspace_number,
        workspace_name=text_field(registered, ("group",)) or (workspace_names.get(workspace_number, "") if workspace_number is not None else ""),
        workspace_id="", tab_id="", tab_name="", window_id=window_id, window_name=text_field(pane, ("name",)),
        agent_session_name=text_field(registered, ("title",)),
        harness=harness or "unknown", cwd=process.cwd or cwd, process=process, status=status, task_status=task_status,
        reported_state=reported_state, task=task, latest_activity=activity, history=history, prompt=prompt,
        capture=capture, events=(), evidence=tuple(evidence),
        limitations=tuple(dict.fromkeys((*errors, *process.limitations, *history.limitations, *conflicts))),
    )
    return PaneInspection(agent=agent, candidate=None, excluded="", limitations=())
