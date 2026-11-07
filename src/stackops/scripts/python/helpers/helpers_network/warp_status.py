import json
import subprocess
from dataclasses import dataclass
from typing import Literal, TypeAlias

WARP_STATE: TypeAlias = Literal["connected", "connecting", "disconnected", "unable", "registration_missing", "daemon_down"]


@dataclass(frozen=True, slots=True)
class WarpStatus:
    state: WARP_STATE
    detail: str | None


@dataclass(frozen=True, slots=True)
class WarpRejection:
    code: str
    message: str


def _flatten_reason(reason: object) -> str | None:
    if reason is None or isinstance(reason, str):
        return reason
    return json.dumps(reason)


def parse_warp_status(raw_output: str) -> WarpStatus:
    match json.loads(raw_output):
        case {"code": str(code), "error": str(error)}:
            return WarpStatus(state="daemon_down", detail=f"""{code}: {error}""")
        case {"status": "Unable", "reason": {"RegistrationMissing": cause}}:
            return WarpStatus(state="registration_missing", detail=_flatten_reason(cause))
        case {"status": "Unable", **fields}:
            return WarpStatus(state="unable", detail=_flatten_reason(fields.get("reason")))
        case {"status": "Connected", **fields}:
            return WarpStatus(state="connected", detail=_flatten_reason(fields.get("reason")))
        case {"status": "Connecting", **fields}:
            return WarpStatus(state="connecting", detail=_flatten_reason(fields.get("reason")))
        case {"status": "Disconnected", **fields}:
            return WarpStatus(state="disconnected", detail=_flatten_reason(fields.get("reason")))
        case _:
            raise ValueError(f"""Unrecognized warp-cli status output: {raw_output}""")


def parse_warp_rejection(raw_output: str) -> WarpRejection:
    match json.loads(raw_output):
        case {"code": str(code), "error": str(error)}:
            return WarpRejection(code=code, message=error)
        case _:
            raise ValueError(f"""Unrecognized warp-cli error output: {raw_output}""")


def describe_warp_status(status: WarpStatus) -> str:
    label = status.state.replace("_", " ").capitalize()
    return label if status.detail is None else f"""{label} ({status.detail})"""


def _run_warp_cli(arguments: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["warp-cli", "--accept-tos", "--json", *arguments], check=False, capture_output=True, text=True, encoding="utf-8")


def read_warp_status() -> WarpStatus:
    completed = _run_warp_cli(("status",))
    return parse_warp_status(completed.stdout if completed.returncode == 0 else completed.stderr)


def request_warp_action(arguments: tuple[str, ...]) -> WarpRejection | None:
    completed = _run_warp_cli(arguments)
    return None if completed.returncode == 0 else parse_warp_rejection(completed.stderr)
