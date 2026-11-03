import json
import sys
from pathlib import Path
from typing import Literal, TypedDict, cast

import typer

from stackops.scripts.python.helpers.helpers_devops.cli_config_setup_email_profile import NewEmailProfile
from stackops.utils.schemas.yaml_schema import JsonValue


class EmailProfileInput(TypedDict):
    name: str
    sender: str
    password: str
    encryption: Literal["tls", "ssl"]
    smtp_host: str
    smtp_port: int


EMAIL_INPUT_SCHEMA: dict[str, object] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": ["name", "sender", "password", "encryption", "smtp_host", "smtp_port"],
    "properties": {
        "name": {"type": "string", "minLength": 1, "pattern": r"\S"},
        "sender": {"type": "string", "minLength": 1, "pattern": r"\S"},
        "password": {"type": "string", "minLength": 1, "pattern": r"\S"},
        "encryption": {"enum": ["tls", "ssl"]},
        "smtp_host": {"type": "string", "minLength": 1, "pattern": r"\S"},
        "smtp_port": {"type": "integer", "minimum": 1, "maximum": 65535},
    },
}


def parse_email_profile(payload: JsonValue) -> NewEmailProfile:
    from jsonschema import Draft202012Validator

    error = next(Draft202012Validator(EMAIL_INPUT_SCHEMA).iter_errors(payload), None)
    if error is not None:
        location = ".".join(str(part) for part in error.path) or "profile"
        raise ValueError(f"Invalid email input at {location}: {error.validator} constraint failed. Use --schema for the format.")
    values = cast(EmailProfileInput, payload)
    return {
        "sender": values["sender"],
        "login": {"name": values["name"], "secrets": [{
            "name": "smtp", "tags": ["email"], "scopes": [], "keyValues": {
                "email_add": values["sender"], "password": values["password"], "encryption": values["encryption"],
                "smtp_host": values["smtp_host"], "smtp_port": str(values["smtp_port"]),
            },
        }]},
    }


def read_email_profile(input_path: Path) -> NewEmailProfile:
    if input_path == Path("-") and sys.stdin.isatty():
        raise typer.BadParameter("--input - requires piped or redirected JSON.")
    try:
        raw = sys.stdin.read() if input_path == Path("-") else input_path.expanduser().read_text(encoding="utf-8")
        payload: JsonValue = json.loads(raw)
    except (OSError, UnicodeError) as error:
        raise typer.BadParameter("Could not read the email input as UTF-8 text.") from error
    except json.JSONDecodeError as error:
        raise typer.BadParameter(f"Invalid email JSON at line {error.lineno}, column {error.colno}.") from error
    try:
        return parse_email_profile(payload)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
