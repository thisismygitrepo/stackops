from pathlib import Path
from typing import cast

from stackops.scripts.python.helpers.helpers_agents.agents_status_history_common import (
    ParsedTranscript,
    human_text,
    json_object,
    text_content,
)
from stackops.scripts.python.helpers.helpers_agents.agents_status_models import MessageRecord


def parse_claude(*, path: Path, rows: list[tuple[int, dict[str, object]]]) -> ParsedTranscript:
    messages: list[MessageRecord] = []
    limitations: list[str] = []
    queued_ids: dict[str, str] = {}
    retained_enqueues: list[tuple[str, str]] = []
    queued_texts: list[str] = []
    pending_queue: list[str] = []
    dequeued_text = ""
    seen_ids: set[str] = set()
    latest_reply = ""
    reply_at = ""
    child = any(row.get("isSidechain") is True for _, row in rows)
    for _, row in rows:
        if row.get("type") != "queue-operation" or row.get("isMeta") is True or row.get("isCompactSummary") is True:
            continue
        queued_raw = text_content(row.get("content"), ("text",))
        queued_human = human_text(queued_raw)
        if row.get("operation") == "enqueue" and queued_human:
            retained_enqueues.append((queued_raw, queued_human))
        elif row.get("operation") == "remove" and queued_human:
            match = next((index for index, (raw, _) in enumerate(retained_enqueues) if raw == queued_raw), None)
            if match is None:
                limitations.append("A human queue removal has no retained matching enqueue; matching direct human records were not suppressed.")
                continue
            _, retained_text = retained_enqueues.pop(match)
            for key in ("commandUuid", "deliveryId"):
                identifier = row.get(key)
                if isinstance(identifier, str) and identifier:
                    queued_ids[identifier] = retained_text
    if child:
        limitations.append(f"""{path}: sidechain transcript; inherited and delegated prompts were not attributed to the human.""")
    for line_number, row in rows:
        timestamp = str(row.get("timestamp", ""))
        record_type = row.get("type")
        if row.get("isCompactSummary") is True:
            limitations.append(f"""{path}:{line_number}: generated compaction summary excluded; it is not an original human message.""")
            continue
        if row.get("isMeta") is True:
            continue
        if record_type == "assistant":
            content = json_object(row.get("message")).get("content")
            reply = text_content(content, ("text",)).strip()
            if reply:
                latest_reply, reply_at = reply, timestamp
            continue
        if child:
            continue
        if record_type == "queue-operation":
            raw_queued = text_content(row.get("content"), ("text",))
            if row.get("operation") == "enqueue":
                pending_queue.append(raw_queued)
                text = human_text(raw_queued)
                if text:
                    messages.append(MessageRecord(timestamp=timestamp, text=text, source=str(path), kind="user", line=line_number))
                    queued_texts.append(text)
            elif row.get("operation") == "remove" and raw_queued in pending_queue:
                pending_queue.remove(raw_queued)
            elif row.get("operation") == "dequeue" and pending_queue:
                dequeued_text = human_text(pending_queue.pop(0))
            continue
        if record_type != "user":
            continue
        delivered_text, dequeued_text = dequeued_text, ""
        identifier = str(row.get("uuid", ""))
        if identifier and identifier in seen_ids:
            continue
        if identifier:
            seen_ids.add(identifier)
        content = json_object(row.get("message")).get("content")
        raw_text = text_content(content, ("text",))
        if raw_text.startswith("[Request interrupted by user"):
            limitations.append(f"""{timestamp}: harness recorded a user interruption; notice excluded from human-message text.""")
            continue
        text = human_text(raw_text)
        if not raw_text and isinstance(content, list):
            attachment_count = sum(json_object(block).get("type") in ("image", "document") for block in cast(list[object], content))
            if attachment_count:
                text = f"""[{attachment_count} human attachment(s); attachment contents not extracted]"""
        if not text:
            continue
        if identifier and queued_ids.get(identifier) == text:
            if text in queued_texts:
                queued_texts.remove(text)
            continue
        if (row.get("isQueued") is True or delivered_text == text) and text in queued_texts:
            queued_texts.remove(text)
            continue
        messages.append(MessageRecord(timestamp=timestamp, text=text, source=str(path), kind="user", line=line_number))
    return ParsedTranscript(
        messages=tuple(messages), latest_reply=latest_reply, reply_at=reply_at,
        limitations=tuple(limitations), child=child,
    )
