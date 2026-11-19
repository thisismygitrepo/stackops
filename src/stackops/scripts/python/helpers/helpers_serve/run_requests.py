import os
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from stackops.scripts.python.helpers.helpers_serve.constants import MAX_TERMINAL_CELLS, MIN_TERMINAL_CELLS, PATH_SUGGESTION_LIMIT


@dataclass(frozen=True)
class RunRequest:
    arguments: tuple[str, ...]
    working_directory: str
    rows: int
    columns: int
    interactive: bool


@dataclass(frozen=True)
class CaptureRequest:
    arguments: tuple[str, ...]
    working_directory: str


@dataclass(frozen=True)
class RequestProblem:
    message: str


def parse_run_request(body: object) -> RunRequest | RequestProblem:
    if not isinstance(body, dict):
        return RequestProblem(message="Expected a JSON object.")
    payload = cast(dict[str, object], body)
    arguments = payload.get("arguments")
    if not isinstance(arguments, list) or not all(isinstance(argument, str) for argument in cast(list[object], arguments)):
        return RequestProblem(message="`arguments` must be a list of strings.")
    working_directory = payload.get("working_directory")
    if not isinstance(working_directory, str) or not Path(os.path.expanduser(working_directory)).is_dir():
        return RequestProblem(message=f"""Working directory does not exist: {working_directory}""")
    rows = payload.get("rows")
    columns = payload.get("columns")
    if not all(isinstance(size, int) and not isinstance(size, bool) and MIN_TERMINAL_CELLS <= size <= MAX_TERMINAL_CELLS for size in (rows, columns)):
        return RequestProblem(message=f"""`rows` and `columns` must be integers between {MIN_TERMINAL_CELLS} and {MAX_TERMINAL_CELLS}.""")
    interactive = payload.get("interactive")
    if not isinstance(interactive, bool):
        return RequestProblem(message="`interactive` must be true or false.")
    return RunRequest(
        arguments=tuple(cast(list[str], arguments)),
        working_directory=str(Path(os.path.expanduser(working_directory))),
        rows=cast(int, rows),
        columns=cast(int, columns),
        interactive=interactive,
    )


def parse_capture_request(body: object) -> CaptureRequest | RequestProblem:
    if not isinstance(body, dict):
        return RequestProblem(message="Expected a JSON object.")
    payload = cast(dict[str, object], body)
    arguments = payload.get("arguments")
    if not isinstance(arguments, list) or not all(isinstance(argument, str) for argument in cast(list[object], arguments)):
        return RequestProblem(message="`arguments` must be a list of strings.")
    working_directory = payload.get("working_directory")
    if not isinstance(working_directory, str) or not Path(os.path.expanduser(working_directory)).is_dir():
        return RequestProblem(message=f"""Working directory does not exist: {working_directory}""")
    return CaptureRequest(arguments=tuple(cast(list[str], arguments)), working_directory=str(Path(os.path.expanduser(working_directory))))


def suggest_paths(prefix: str, base_directory: str) -> list[str]:
    # os.path.expanduser leaves `~name` as typed when there is no such user, where Path.expanduser raises.
    typed = Path(os.path.expanduser(prefix))
    resolved = typed if typed.is_absolute() else Path(os.path.expanduser(base_directory)) / typed
    complete_directory = prefix == "" or prefix.endswith(("/", os.sep))
    parent = resolved if complete_directory else resolved.parent
    stem = "" if complete_directory else resolved.name
    if not parent.is_dir():
        return []
    try:
        children = sorted(parent.iterdir(), key=lambda child: (not child.is_dir(), child.name.casefold()))
    except PermissionError:
        return []
    shown_parent = prefix[: len(prefix) - len(stem)]
    return [
        f"""{shown_parent}{child.name}{"/" if child.is_dir() else ""}"""
        for child in children
        if child.name.casefold().startswith(stem.casefold()) and (stem.startswith(".") or not child.name.startswith("."))
    ][:PATH_SUGGESTION_LIMIT]
