import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from stackops.scripts.python.helpers.helpers_agents.agents_status_models import MessageRecord


@dataclass(frozen=True)
class ParsedTranscript:
    messages: tuple[MessageRecord, ...]
    latest_reply: str
    reply_at: str
    limitations: tuple[str, ...]
    child: bool


def json_object(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return cast(dict[str, object], value)
    return {}


def text_content(value: object, accepted_types: tuple[str, ...]) -> str:
    if isinstance(value, str):
        return value
    if not isinstance(value, list):
        return ""
    texts: list[str] = []
    for raw_block in cast(list[object], value):
        block = json_object(raw_block)
        text = block.get("text")
        if block.get("type") in accepted_types and isinstance(text, str):
            texts.append(text)
    return "\n".join(texts)


def human_text(text: str) -> str:
    text = text.strip()
    generated_prefixes = (
        "<local-command-stdout>", "<local-command-caveat>", "<task-notification>",
        "<system-reminder>", "<environment_context>", "<codex_internal_context",
        "<collaboration_mode>", "<permissions instructions>", "<turn_aborted>",
        "# AGENTS.md instructions", "[Request interrupted by user",
        "This session is being continued from a previous conversation",
        "You are now a newly spawned child agent.", "<subagent_notification>",
    )
    if not text or text.startswith(generated_prefixes):
        return ""
    command = re.search(r"<command-args>(.*?)</command-args>", text, flags=re.DOTALL)
    if command is not None and "<command-name>/goal</command-name>" in text:
        return command.group(1).strip()
    return text


def read_jsonl(path: Path) -> tuple[list[tuple[int, dict[str, object]]], tuple[str, ...]]:
    rows: list[tuple[int, dict[str, object]]] = []
    limitations: list[str] = []
    forbidden = Path.home() / "dotfiles"
    if path.expanduser().absolute().is_relative_to(forbidden) or path.resolve().is_relative_to(forbidden):
        return rows, (f"""Transcript under the excluded dotfiles directory was not read: {path}""",)
    try:
        with path.open(encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                if not line.strip():
                    continue
                try:
                    value: object = json.loads(line)
                except json.JSONDecodeError:
                    limitations.append(f"""Invalid JSON at {path}:{line_number}; record omitted (possibly an incomplete live write).""")
                    continue
                if not isinstance(value, dict):
                    limitations.append(f"""Non-object transcript record at {path}:{line_number} was omitted.""")
                    continue
                rows.append((line_number, cast(dict[str, object], value)))
    except (OSError, UnicodeError) as error:
        limitations.append(f"""Could not finish reading transcript {path}: {error}""")
    return rows, tuple(limitations)
