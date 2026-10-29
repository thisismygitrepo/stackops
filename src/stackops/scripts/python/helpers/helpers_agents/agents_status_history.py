from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_status_history_claude import parse_claude
from stackops.scripts.python.helpers.helpers_agents.agents_status_history_codex import parse_codex
from stackops.scripts.python.helpers.helpers_agents.agents_status_history_common import read_jsonl
from stackops.scripts.python.helpers.helpers_agents.agents_status_models import HistoryEvidence, MessageRecord, StatusBackend


def _hook_history(events: list[dict[str, object]]) -> HistoryEvidence:
    messages: list[MessageRecord] = []
    latest_reply = ""
    latest_reply_at = ""
    for event in events:
        text = event.get("text")
        if not isinstance(text, str) or not text:
            continue
        timestamp_value = event.get("at")
        timestamp = ""
        if isinstance(timestamp_value, int) and timestamp_value > 0:
            timestamp = datetime.fromtimestamp(timestamp_value / 1_000_000_000, tz=UTC).isoformat()
        if event.get("kind") == "prompt":
            messages.append(MessageRecord(timestamp=timestamp, text=text, source="tuios:agent-log", kind="user", line=None))
        elif event.get("kind") == "turn_end":
            latest_reply = text
            latest_reply_at = timestamp
    return HistoryEvidence(
        messages=tuple(messages), latest_reply=latest_reply, latest_reply_at=latest_reply_at, sources=("tuios:agent-log",),
        coverage="partial" if events else "unavailable", omitted_messages=0,
        limitations=("TUIOS keeps at most 256 in-memory hook events; prompts/replies are masked, clipped first lines, not a full conversation.",)
        if events else ("TUIOS returned no hook history; human-message history is unavailable.",),
    )


def read_history(
    *, harness: str, paths: tuple[Path, ...], events: list[dict[str, object]], mode: str,
    message_limit: int, text_limit: int, backend: StatusBackend,
) -> HistoryEvidence:
    if mode == "none":
        return HistoryEvidence(messages=(), latest_reply="", latest_reply_at="", sources=(), coverage="disabled", limitations=(), omitted_messages=0)
    messages: list[MessageRecord] = []
    sources: list[str] = []
    limitations: list[str] = []
    replies: list[tuple[str, str]] = []
    transcript_read = False
    if mode in ("auto", "transcripts"):
        for path in dict.fromkeys(paths):
            rows, errors = read_jsonl(path)
            limitations.extend(errors)
            sources.append(str(path))
            if not rows:
                continue
            if harness in ("claude", "claude-code"):
                parsed = parse_claude(path=path, rows=rows)
            elif harness == "codex":
                parsed = parse_codex(path=path, rows=rows)
            else:
                limitations.append(f"""No transcript parser for harness {harness!r}.""")
                continue
            limitations.extend(parsed.limitations)
            if parsed.child:
                continue
            transcript_read = True
            messages.extend(parsed.messages)
            if parsed.latest_reply:
                replies.append((parsed.reply_at, parsed.latest_reply))
        if transcript_read:
            limitations.append("History covers retained, readable transcript records only; earlier conversations and deleted records cannot be verified.")
        elif not paths:
            limitations.append("No existing transcript could be reliably linked to this live agent.")
    latest_reply_at, latest_reply = max(replies, default=("", ""))
    coverage = "partial" if transcript_read else "unavailable"
    if mode == "hooks" or mode == "auto" and not transcript_read:
        hooks = _hook_history(events) if backend == "tuios" else HistoryEvidence(
            messages=(), latest_reply="", latest_reply_at="", sources=(), coverage="unavailable", omitted_messages=0,
            limitations=(f"""{'Herdr' if backend == 'herdr' else 'AoE'} does not expose retained hook history; human messages require a reliably linked transcript.""",),
        )
        messages = list(hooks.messages)
        latest_reply = hooks.latest_reply
        latest_reply_at = hooks.latest_reply_at
        sources.extend(hooks.sources)
        limitations.extend(hooks.limitations)
        coverage = hooks.coverage
    messages.sort(key=lambda message: message.timestamp)
    omitted_messages = max(0, len(messages) - message_limit) if message_limit else 0
    if omitted_messages:
        messages = messages[-message_limit:]
        limitations.append(f"""{omitted_messages} older message/context records omitted by --messages.""")
    if text_limit:
        clipped: list[MessageRecord] = []
        for message in messages:
            if len(message.text) > text_limit:
                omitted = len(message.text) - text_limit
                message = replace(message, text=f"""{message.text[:text_limit]} [truncated; {omitted} characters omitted]""")
            clipped.append(message)
        messages = clipped
        if len(latest_reply) > text_limit:
            omitted = len(latest_reply) - text_limit
            latest_reply = f"""{latest_reply[:text_limit]} [truncated; {omitted} characters omitted]"""
    return HistoryEvidence(
        messages=tuple(messages), latest_reply=latest_reply, latest_reply_at=latest_reply_at, sources=tuple(dict.fromkeys(sources)), coverage=coverage,
        limitations=tuple(dict.fromkeys(limitations)), omitted_messages=omitted_messages,
    )
