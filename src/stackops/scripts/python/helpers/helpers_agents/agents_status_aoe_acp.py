import json
import os
from dataclasses import replace
from typing import cast

from stackops.scripts.python.helpers.helpers_agents.agents_status_aoe import query_aoe
from stackops.scripts.python.helpers.helpers_agents.agents_status_models import HistoryEvidence, JsonObject, MessageRecord, StatusOptions
from stackops.scripts.python.helpers.helpers_agents.agents_status_tuios import json_object, text_field


def inspect_aoe_acp(*, options: StatusOptions, session_id: str) -> tuple[JsonObject, JsonObject, HistoryEvidence]:
    source = f"""aoe:acp-history:{session_id}"""
    state: JsonObject = {"state": "unknown", "source": source}
    limitations: list[str] = []
    messages: list[MessageRecord] = []
    latest_reply = ""
    reply_chunks: list[str] = []
    pending: dict[str, JsonObject] = {}
    frames: list[JsonObject] = []
    coverage = "unavailable"
    if options.history == "none":
        coverage = "disabled"
        limitations.append("ACP activity cannot be inferred from worker liveness; retained event inspection was disabled.")
    elif os.environ.get("AOE_DAEMON_URL"):
        limitations.append("ACP history was not queried because AOE_DAEMON_URL overrides the daemon for this local AoE inventory.")
    else:
        status_payload, status_error = query_aoe(options=options, arguments=["acp", "status", session_id, "--json"])
        if status_error is not None:
            limitations.append(status_error)
        else:
            retention = json_object(status_payload)
            lowest = retention.get("lowest_seq")
            if retention.get("lost") is True or isinstance(lowest, int) and lowest > 1:
                limitations.append("AoE's retention window has removed earlier conversation events.")
        payload, history_error = query_aoe(options=options, arguments=["acp", "history", session_id, "--json"])
        if history_error is not None:
            limitations.append(history_error)
        elif not isinstance(payload, list) or any(not isinstance(frame, dict) for frame in payload):
            limitations.append("AoE ACP returned an invalid transcript frame list.")
        else:
            frames = cast(list[JsonObject], payload)
            coverage = "partial"
            limitations.append("ACP evidence covers retained prompt text and agent replies; attachment contents and original prompt timestamps are unavailable.")
            limitations.append("Activity and pending requests are inferred from retained ACP events, not independently verified task progress.")
    for frame in frames:
        if frame.get("session_id") != session_id:
            limitations.append("ACP returned an event for another session; it was not included.")
            continue
        event = frame.get("event")
        if isinstance(event, str):
            kind, data = event, {}
        elif isinstance(event, dict) and len(event) == 1:
            event_object = cast(JsonObject, event)
            kind = next(iter(event_object))
            data = json_object(event_object[kind])
        else:
            limitations.append("An ACP event had an unrecognized event envelope and was not included.")
            continue
        if kind in {"UserPromptSent", "UserDiffCommentsPrompt"}:
            text = text_field(data, ("text", "assembledMarkdown"))
            if text:
                messages.append(MessageRecord(timestamp="", text=text, source=f"""{source}:seq:{frame.get('seq')}""", kind="user", line=None))
            if data.get("attachments"):
                limitations.append("Some retained prompts include attachments whose contents were not extracted.")
            reply_chunks = []
            state.update(state="working", message="Latest retained ACP event: user prompt submitted.")
        elif kind == "AgentMessageChunk":
            text = text_field(data, ("text",))
            reply_chunks.append(text)
            latest_reply = "".join(reply_chunks)
            state.update(state="working", message="")
        elif kind in {"ThinkingStarted", "ToolCallStarted", "ConversationCompactionStarted"}:
            tool = json_object(data.get("tool_call"))
            state.update(state="working", message=f"""Latest retained ACP activity: {text_field(tool, ('name',)) or kind}.""")
        elif kind in {"ApprovalRequested", "ElicitationRequested"}:
            request = json_object(data.get("approval" if kind == "ApprovalRequested" else "elicitation"))
            nonce = text_field(request, ("nonce",))
            if nonce:
                pending[nonce] = request
        elif kind in {"ApprovalResolved", "ElicitationResolved"}:
            pending.pop(text_field(data, ("nonce",)), None)
        elif kind == "RateLimit":
            state.update(state="blocked", message=text_field(json_object(data.get("info")), ("status",)))
        elif kind in {"AgentStartupError", "PromptRuntimeError", "IncompatibleAgent"}:
            state.update(state="failed", message=text_field(data, ("message",)) or kind)
        elif kind == "Stopped":
            reason = text_field(data, ("reason",))
            reported = {"end_turn": "completed", "cancelled": "idle", "rate_limited": "blocked"}.get(reason, "unknown")
            state.update(state=reported, message=f"""Latest retained ACP stop: {reason or 'reason unavailable'}.""")
        elif kind in {"SessionCleared", "SessionContextReset", "AgentSwitched"}:
            pending.clear()
            reply_chunks = []
            state.update(state="unknown", message=f"""Latest retained ACP session change: {kind}.""")
    prompt: JsonObject = {}
    if pending:
        prompt_text = json.dumps(list(pending.values()), ensure_ascii=False)
        if options.text_limit and len(prompt_text) > options.text_limit:
            prompt_text = prompt_text[:options.text_limit] + " [truncated]"
        prompt = {"found": True, "source": source, "text": prompt_text}
        state.update(state="needs_input", message="Retained ACP events contain an unresolved question or approval request.")
    omitted = max(0, len(messages) - options.message_limit) if options.message_limit else 0
    if omitted:
        messages = messages[-options.message_limit:]
        limitations.append(f"""{omitted} older messages omitted by --messages.""")
    if options.text_limit:
        messages = [
            replace(message, text=message.text[:options.text_limit] + " [truncated]") if len(message.text) > options.text_limit else message
            for message in messages
        ]
        if len(latest_reply) > options.text_limit:
            latest_reply = latest_reply[:options.text_limit] + " [truncated]"
        activity = text_field(state, ("message",))
        if len(activity) > options.text_limit:
            state["message"] = activity[:options.text_limit] + " [truncated]"
    history = HistoryEvidence(
        messages=tuple(messages), latest_reply=latest_reply, latest_reply_at="", sources=(source,) if coverage == "partial" else (),
        coverage=coverage, limitations=tuple(dict.fromkeys(limitations)), omitted_messages=omitted,
    )
    return state, prompt, history
