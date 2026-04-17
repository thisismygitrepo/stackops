import json
from dataclasses import dataclass
from typing import Final


JSON_ENTRY_KEYS: Final[tuple[str, ...]] = (
    "generalDiagnostics",
    "diagnostics",
    "messages",
    "results",
    "violations",
    "errors",
)


@dataclass(frozen=True, slots=True)
class ParsedJsonOutput:
    prefix_text: str
    payload: object


def split_json_prefix(raw_output: str) -> tuple[str, str | None]:
    lines = raw_output.splitlines()
    for index, line in enumerate(lines):
        stripped_line = line.lstrip()
        if stripped_line.startswith("{") or stripped_line.startswith("["):
            prefix_text = "\n".join(lines[:index]).strip()
            payload_text = "\n".join(lines[index:]).strip()
            return prefix_text, payload_text
    return "", None


def parse_json_output(raw_output: str) -> ParsedJsonOutput:
    stripped_output = raw_output.strip()
    try:
        return ParsedJsonOutput(
            prefix_text="", payload=parse_json_stream(raw_output=stripped_output)
        )
    except json.JSONDecodeError as error:
        prefix_text, payload_text = split_json_prefix(raw_output=raw_output)
        if payload_text is None:
            raise error
        return ParsedJsonOutput(
            prefix_text=prefix_text,
            payload=parse_json_stream(raw_output=payload_text),
        )


def parse_json_stream(raw_output: str) -> object:
    stripped_output = raw_output.strip()
    if stripped_output == "":
        raise json.JSONDecodeError("Expecting value", raw_output, 0)
    decoder = json.JSONDecoder()
    decoded_items: list[object] = []
    index = 0
    while index < len(stripped_output):
        while index < len(stripped_output) and stripped_output[index].isspace():
            index += 1
        if index >= len(stripped_output):
            break
        payload, end_index = decoder.raw_decode(stripped_output, index)
        decoded_items.append(payload)
        index = end_index
    if len(decoded_items) == 1:
        return decoded_items[0]
    return decoded_items


def extract_json_entries(payload: object) -> tuple[str | None, tuple[object, ...] | None]:
    if isinstance(payload, list):
        return None, tuple(payload)
    if isinstance(payload, dict):
        for key in JSON_ENTRY_KEYS:
            candidate = payload.get(key)
            if isinstance(candidate, list):
                return key, tuple(candidate)
    return None, None


def extract_json_metadata(
    payload: object, entry_key: str | None
) -> dict[str, object] | None:
    if not isinstance(payload, dict):
        return None
    metadata: dict[str, object] = {}
    for key, value in payload.items():
        if isinstance(key, str) and key != entry_key:
            metadata[key] = value
    if metadata:
        return metadata
    return None
