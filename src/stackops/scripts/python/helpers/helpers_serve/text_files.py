import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.paths import permitted_resource_path
from stackops.scripts.python.helpers.helpers_serve.constants import MAX_EDITABLE_FILE_BYTES


@dataclass(frozen=True)
class TextFile:
    path: str
    text: str
    version: str


@dataclass(frozen=True)
class FileProblem:
    status: int
    message: str


def read_text_file(path: str) -> TextFile | FileProblem:
    target = Path(path)
    if not target.is_absolute():
        return FileProblem(status=400, message="Give the full path of the file.")
    if not permitted_resource_path(path=target, home_directory=Path.home()):
        return FileProblem(status=403, message="This file is kept in a protected place, so it is not opened here.")
    if not target.is_file():
        return FileProblem(status=404, message=f"""There is no file at {path}. It may be a folder, or it was removed.""")
    if target.stat().st_size > MAX_EDITABLE_FILE_BYTES:
        return FileProblem(status=413, message=f"""This file is larger than {MAX_EDITABLE_FILE_BYTES // 1024} KB, which is more than is opened here.""")
    content = target.read_bytes()
    try:
        text = content.decode(encoding="utf-8")
    except UnicodeDecodeError:
        return FileProblem(status=415, message="This file is not plain text, so it cannot be shown here.")
    return TextFile(path=path, text=text, version=hashlib.sha256(content).hexdigest())


def write_text_file(body: object) -> TextFile | FileProblem:
    if not isinstance(body, dict):
        return FileProblem(status=400, message="Expected a JSON object.")
    payload = cast(dict[str, object], body)
    path = payload.get("path")
    text = payload.get("text")
    version = payload.get("version")
    if not isinstance(path, str) or not isinstance(text, str) or not isinstance(version, str):
        return FileProblem(status=400, message="`path`, `text` and `version` must be text.")
    current = read_text_file(path=path)
    match current:
        case FileProblem():
            return current
        case TextFile():
            # The version is the hash of what the editor was opened on, so a save never silently replaces what something else wrote meanwhile.
            if current.version != version:
                return FileProblem(status=409, message="This file changed on disk after it was opened. Reopen it to see what it holds now, then edit again.")
    content = text.encode(encoding="utf-8")
    if len(content) > MAX_EDITABLE_FILE_BYTES:
        return FileProblem(status=413, message=f"""That is more than the {MAX_EDITABLE_FILE_BYTES // 1024} KB that is saved from here.""")
    Path(path).write_bytes(content)
    return TextFile(path=path, text=text, version=hashlib.sha256(content).hexdigest())
