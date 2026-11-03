import json
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from pathlib import Path

import typer


def serialize_agent_result(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: getattr(value, field.name) for field in fields(value)}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (set, frozenset)):
        return sorted(value)
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def emit_agent_json(value: object) -> None:
    typer.echo(json.dumps(value, default=serialize_agent_result, indent=2))
