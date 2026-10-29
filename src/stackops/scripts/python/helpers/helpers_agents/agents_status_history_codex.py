import re
from pathlib import Path
from typing import cast

from stackops.scripts.python.helpers.helpers_agents.agents_status_history_common import (
    ParsedTranscript,
    human_text,
    json_object,
    text_content,
)
from stackops.scripts.python.helpers.helpers_agents.agents_status_models import MessageRecord


def _delivery_ids(payload: dict[str, object]) -> frozenset[str]:
    identifiers: set[str] = set()
    metadata = json_object(payload.get("internal_chat_message_metadata_passthrough"))
    for container in (payload, metadata):
        for key, namespace in (("message_id", "message"), ("user_message_id", "message"), ("request_id", "request"), ("delivery_id", "delivery")):
            value = container.get(key)
            if isinstance(value, str) and value:
                identifiers.add(f"""{namespace}:{value}""")
    identifier = payload.get("id")
    if isinstance(identifier, str) and identifier:
        identifiers.add(f"""message:{identifier}""")
    return frozenset(identifiers)


def _record_user(
    *, message: MessageRecord, representation: str, identifiers: frozenset[str], messages: list[MessageRecord],
    recorded: list[tuple[MessageRecord, str, frozenset[str]]], limitations: list[str],
) -> None:
    for previous, previous_representation, previous_ids in recorded:
        linked = bool(identifiers & previous_ids)
        if linked and previous.text == message.text:
            return
        if linked:
            limitations.append(f"""{message.source}:{previous.line},{message.line}: human records share a delivery identifier but differ in text; both retained.""")
        elif previous_representation != representation and previous.text == message.text:
            limitations.append(f"""{message.source}:{previous.line},{message.line}: identical human text occurs in event and response records without a shared delivery identifier; possible duplicate sources, both retained.""")
    messages.append(message)
    recorded.append((message, representation, identifiers))


def parse_codex(*, path: Path, rows: list[tuple[int, dict[str, object]]]) -> ParsedTranscript:
    messages: list[MessageRecord] = []
    limitations: list[str] = []
    goals: set[str] = set()
    latest_reply = ""
    reply_at = ""
    first_metadata = next((json_object(row.get("payload")) for _, row in rows if row.get("type") == "session_meta"), {})
    child = "subagent" in json_object(first_metadata.get("source"))
    if child:
        return ParsedTranscript(
            messages=(), latest_reply="", reply_at="", child=True,
            limitations=(f"""{path}: child transcript excluded; inherited parent and delegated prompts are not independent human messages.""",),
        )
    recorded_users: list[tuple[MessageRecord, str, frozenset[str]]] = []
    for line_number, row in rows:
        payload = json_object(row.get("payload"))
        timestamp = str(row.get("timestamp", ""))
        record_type = row.get("type")
        if record_type == "event_msg" and payload.get("type") == "task_complete":
            reply = payload.get("last_agent_message")
            if isinstance(reply, str) and reply:
                latest_reply, reply_at = reply, timestamp
        if record_type == "response_item" and payload.get("type") == "message" and payload.get("role") == "assistant":
            if payload.get("phase") == "final_answer" or payload.get("channel") == "final":
                reply = text_content(payload.get("content"), ("output_text", "text")).strip()
                if reply:
                    latest_reply, reply_at = reply, timestamp
        if record_type == "event_msg" and payload.get("type") == "user_message":
            raw_message = payload.get("message")
            text = human_text(raw_message) if isinstance(raw_message, str) else ""
            if text:
                _record_user(
                    message=MessageRecord(timestamp=timestamp, text=text, source=str(path), kind="user", line=line_number),
                    representation="event", identifiers=_delivery_ids(payload), messages=messages,
                    recorded=recorded_users, limitations=limitations,
                )
            continue
        if record_type != "response_item" or payload.get("type") != "message" or payload.get("role") != "user":
            continue
        content = payload.get("content")
        blocks: list[object] = cast(list[object], content) if isinstance(content, list) else [{"text": content, "type": "input_text"}]
        texts: list[str] = []
        for raw_block in blocks:
            block = json_object(raw_block)
            if block.get("type") not in ("input_text", "text"):
                continue
            raw_text = block.get("text")
            if not isinstance(raw_text, str):
                continue
            if raw_text.lstrip().startswith("<codex_internal_context"):
                objective = re.search(r"<objective>\s*(.*?)\s*</objective>", raw_text, flags=re.DOTALL)
                retained = re.search(r'User set the goal:\s*"(.*?)"\s*\n', raw_text, flags=re.DOTALL)
                goal = objective.group(1) if objective is not None else retained.group(1) if retained is not None else ""
                if goal and goal not in goals:
                    goals.add(goal)
                    messages.append(MessageRecord(timestamp=timestamp, text=goal, source=str(path), kind="goal_context", line=line_number))
                    limitations.append("A goal is retained as generated context; its original human message and timestamp may be absent.")
                continue
            text = human_text(raw_text)
            if text:
                texts.append(text)
        if texts:
            _record_user(
                message=MessageRecord(timestamp=timestamp, text="\n".join(texts), source=str(path), kind="user", line=line_number),
                representation="response", identifiers=_delivery_ids(payload), messages=messages,
                recorded=recorded_users, limitations=limitations,
            )
    return ParsedTranscript(
        messages=tuple(messages), latest_reply=latest_reply, reply_at=reply_at,
        limitations=tuple(dict.fromkeys(limitations)), child=False,
    )
