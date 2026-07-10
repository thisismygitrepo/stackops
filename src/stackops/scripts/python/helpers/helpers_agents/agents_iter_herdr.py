import json
import shlex
import subprocess
from typing import cast

from stackops.scripts.python.helpers.helpers_agents.agents_iter_constants import HERDR_COMMAND_TIMEOUT_SECONDS
from stackops.scripts.python.helpers.helpers_agents.agents_iter_herdr_protocol import (
    HerdrProtocolError,
    JsonObject,
    parse_error_response,
    parse_ok_response,
    parse_snapshot_response,
)
from stackops.scripts.python.helpers.helpers_agents.agents_iter_models import HerdrSnapshot, TabId


class HerdrCommandError(RuntimeError):
    pass


class HerdrApiError(HerdrCommandError):
    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(f"Herdr API error {code!r}: {message}")
        self.code = code
        self.message = message


def capture_herdr_snapshot() -> HerdrSnapshot:
    payload = _run_herdr_json(command=("herdr", "api", "snapshot"), command_id="cli:api:snapshot")
    return parse_snapshot_response(payload=payload)


def close_tab(*, tab_id: TabId) -> None:
    if str(tab_id).strip() == "":
        raise ValueError("Herdr tab id must not be empty.")
    command_id = "cli:tab:close"
    payload = _run_herdr_json(command=("herdr", "tab", "close", str(tab_id)), command_id=command_id)
    parse_ok_response(payload=payload, expected_id=command_id)


def _run_herdr(*, command: tuple[str, ...], command_id: str) -> str:
    try:
        result = subprocess.run(command, capture_output=True, check=False, text=True, timeout=HERDR_COMMAND_TIMEOUT_SECONDS)
    except FileNotFoundError as error:
        raise HerdrCommandError("Iter maintenance requested Herdr, but `herdr` was not found in PATH.") from error
    except subprocess.TimeoutExpired as error:
        raise HerdrCommandError(f"Herdr command timed out after {HERDR_COMMAND_TIMEOUT_SECONDS} second(s): {shlex.join(command)}") from error
    if result.returncode == 0:
        return result.stdout

    detail = (result.stdout or result.stderr).strip()
    try:
        payload = cast(object, json.loads(detail))
    except json.JSONDecodeError as error:
        raise HerdrCommandError(f"Herdr command failed ({shlex.join(command)}): {detail or 'no error response'}") from error
    if not isinstance(payload, dict):
        raise HerdrCommandError(f"Herdr command returned a non-object error response: {shlex.join(command)}")
    code, message = parse_error_response(payload=cast(JsonObject, payload), expected_id=command_id)
    raise HerdrApiError(code=code, message=message)


def _run_herdr_json(*, command: tuple[str, ...], command_id: str) -> JsonObject:
    stdout = _run_herdr(command=command, command_id=command_id).strip()
    if stdout == "":
        raise HerdrProtocolError(f"Herdr command did not return JSON: {shlex.join(command)}")
    try:
        payload = cast(object, json.loads(stdout))
    except json.JSONDecodeError as error:
        raise HerdrProtocolError(f"Herdr command returned invalid JSON: {shlex.join(command)}") from error
    if not isinstance(payload, dict):
        raise HerdrProtocolError(f"Herdr command returned non-object JSON: {shlex.join(command)}")
    return cast(JsonObject, payload)
