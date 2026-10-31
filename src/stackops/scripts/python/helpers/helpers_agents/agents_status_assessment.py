from datetime import datetime

from stackops.utils.schemas.config.multiplexer_types import AgentMultiplexer
from stackops.scripts.python.helpers.helpers_agents.agents_status_models import (
    AgentStatus,
    HistoryEvidence,
    JsonObject,
    ProcessEvidence,
)
from stackops.scripts.python.helpers.helpers_agents.agents_status_tuios import text_field


def assess_status(
    *, state: JsonObject, prompt: JsonObject, process: ProcessEvidence, detector: JsonObject, backend: AgentMultiplexer
) -> tuple[AgentStatus, str, list[str], list[str]]:
    reported = text_field(state, ("state",))
    evidence: list[str] = []
    limitations: list[str] = []
    if reported:
        source = text_field(state, ("source",)) or "unknown source"
        age = state.get("evidence_age_ms")
        evidence.append(f"""{backend.upper()} reports {reported} ({source}; evidence age {age if age is not None else 'unknown'} ms).""")
    if process.live is True:
        evidence.append(f"""Live {process.harness or 'agent'} process PID {process.pid}; process presence alone does not prove progress.""")
    elif process.live is False:
        evidence.append("No matching live agent process remains in this window's process tree.")
    else:
        limitations.append("Agent process liveness could not be verified.")
    verdict = text_field(detector, ("verdict",))
    if verdict:
        evidence.append(verdict)
    task_status = "reported completed" if reported in {"done", "completed"} else "reported failed" if reported in {"error", "errored", "failed"} else "unknown"
    if process.live is False:
        if reported not in {"", "none"}:
            limitations.append("Reported agent state conflicts with the missing process and may be stale.")
        return "unavailable", task_status, evidence, limitations
    if prompt.get("found") is True or prompt.get("blocked") is True:
        evidence.append("A pending question or approval was reported; no answer was sent.")
        if reported not in {"needs_input", "blocked"}:
            limitations.append("Pending prompt conflicts with the reported state; the prompt takes precedence.")
        return "waiting", task_status, evidence, limitations
    mapped: dict[str, AgentStatus] = {
        "working": "working", "needs_input": "waiting", "blocked": "blocked", "idle": "idle",
        "done": "idle", "completed": "idle", "error": "failed", "errored": "failed", "failed": "failed",
    }
    status = mapped.get(reported, "unknown")
    detected = text_field(detector, ("state",))
    detected_status = mapped.get(detected, "unknown")
    activity = text_field(detector, ("activity",))
    if detected_status != "unknown" and status != "unknown" and detected_status != status:
        limitations.append(f"""Conflicting live reads: detector reported {detected}, while agent state reported {reported}; current activity is uncertain.""")
        evidence.append(f"""Detector activity: {activity or 'unavailable'}; detector state: {detected}.""")
        return "unknown", task_status, evidence, limitations
    if status == "unknown" and detected_status != "unknown":
        status = detected_status
        evidence.append(f"""Activity state supplied by the live detector: {detected}.""")
    if reported == "working":
        task_status = "in progress (reported)"
    elif status == "unknown":
        limitations.append("No reliable activity state is available; a running harness does not imply active work.")
    return status, task_status, evidence, limitations


def describe_activity(*, state: JsonObject, history: HistoryEvidence, events: list[JsonObject], text_limit: int) -> tuple[str, str]:
    requests = [message for message in history.messages if message.kind in {"user", "goal_context"}]
    request_label = "Retained goal context" if requests and requests[0].kind == "goal_context" else "First retained request"
    task = f"""{request_label}: {requests[0].text}""" if requests else "Task unknown: no retained user request available."
    activity = text_field(state, ("message",))
    if not activity:
        tools = [event for event in events if event.get("kind") in {"tool", "tool_done", "tool_failed", "command"}]
        try:
            reply_at = datetime.fromisoformat(history.latest_reply_at).timestamp() if history.latest_reply_at else None
        except ValueError:
            reply_at = None
        tool_at = tools[-1].get("at") if tools else None
        reply_is_newer = reply_at is not None and isinstance(tool_at, int) and reply_at >= tool_at / 1_000_000_000
        if history.latest_reply and (not tools or reply_is_newer):
            activity = f"""Latest retained agent reply: {history.latest_reply}"""
        elif tools:
            event = tools[-1]
            activity = f"""Latest retained hook event ({event.get('kind')}): {text_field(event, ('text', 'target', 'tool'))}"""
        else:
            activity = "No activity text available; see pane capture and reported state."
    if text_limit:
        task = task[:text_limit] + (" [truncated]" if len(task) > text_limit else "")
        activity = activity[:text_limit] + (" [truncated]" if len(activity) > text_limit else "")
    return task, activity
