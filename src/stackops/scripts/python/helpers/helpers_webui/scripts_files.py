import re
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, cast

from stackops.scripts.python.helpers.helpers_devops.script_discovery import IGNORED_SCRIPT_DIRECTORY_NAMES, SCRIPT_SUFFIXES, is_supported_script_path
from stackops.scripts.python.helpers.helpers_webui.constants import (
    MAX_EDITABLE_FILE_BYTES,
    SCRIPT_DIRECTIVE_PREFIXES,
    SCRIPT_NAME_PATTERN,
    SCRIPT_STARTER_SUMMARY,
    SCRIPT_STARTERS,
    SCRIPT_SUMMARY_LIMIT,
    SCRIPT_SUMMARY_READ_BYTES,
)
from stackops.utils.repos.stackops_paths import workspace_stackops_paths
from stackops.utils.source_of_truth import SCRIPTS_ROOT_LIBRARY, SCRIPTS_ROOT_PRIVATE


@dataclass(frozen=True)
class ScriptProblem:
    status: int
    message: str


# `name` is the script's path inside its place, with forward slashes: what `devops scripts run` takes. `summary` is empty when the file does not say what it does.
class ScriptView(TypedDict):
    name: str
    path: str
    suffix: str
    summary: str
    size: int
    modified: float


class ScriptPlaceView(TypedDict):
    name: str
    path: str
    exists: bool
    scripts: list[ScriptView]


class ScriptsView(TypedDict):
    places: list[ScriptPlaceView]


class ScriptText(TypedDict):
    text: str


class ScriptCreated(TypedDict):
    source: str
    name: str
    path: str


# The folders the CLI looks in from `base_directory` with `--source all`: the project's own, one per member of a workspace, the user's, then the ones that come with StackOps.
def script_places(base_directory: str) -> list[tuple[str, Path]] | ScriptProblem:
    try:
        workspace = workspace_stackops_paths(current_dir=Path(base_directory), path_kind="scripts")
    except ValueError as error:
        return ScriptProblem(status=400, message=str(error))
    return [*workspace, ("user", SCRIPTS_ROOT_PRIVATE), ("library", SCRIPTS_ROOT_LIBRARY)]


def read_scripts(base_directory: str) -> ScriptsView | ScriptProblem:
    places = script_places(base_directory)
    match places:
        case ScriptProblem():
            return places
        case _:
            return {"places": [{"name": name, "path": str(root), "exists": root.is_dir(), "scripts": _scripts_under(root)} for name, root in places]}


# What the CLI lists, less the hidden files it also counts (a `.DS_Store` has no ending, which is how it tells a program from a document).
def _scripts_under(root: Path) -> list[ScriptView]:
    found: list[ScriptView] = []
    for folder, folder_names, file_names in root.walk():
        folder_names[:] = [name for name in folder_names if name not in IGNORED_SCRIPT_DIRECTORY_NAMES]
        for file_name in file_names:
            path = folder / file_name
            relative = path.relative_to(root)
            if file_name.startswith(".") or not path.is_file() or not is_supported_script_path(relative_path=relative, supported_suffixes=SCRIPT_SUFFIXES):
                continue
            facts = path.stat()
            found.append({"name": relative.as_posix(), "path": str(path), "suffix": path.suffix, "summary": _summary(path), "size": facts.st_size, "modified": facts.st_mtime})
    return sorted(found, key=lambda script: script["name"].casefold())


# The first line a script says about itself: a comment at its top, or the start of a Python file's docstring. Lines written for a tool are
# passed over (the shebang, uv's `# /// script` block, linter switches), and the search ends at the first line of code.
def _summary(path: Path) -> str:
    with path.open("rb") as handle:
        head = handle.read(SCRIPT_SUMMARY_READ_BYTES).decode(encoding="utf-8", errors="replace")
    marks = ("rem ", "::") if path.suffix in {".bat", ".cmd"} else ("#",)
    quote = ""
    in_metadata = False
    for line in (raw.strip() for raw in head.splitlines()):
        if quote != "":
            said = line.removesuffix(quote).strip()
            if said != "" or line.endswith(quote):
                return said[:SCRIPT_SUMMARY_LIMIT]
        elif in_metadata:
            in_metadata = line != "# ///"
        elif line.startswith("# /// "):
            in_metadata = True
        elif line.lower().startswith(marks):
            mark = next(mark for mark in marks if line.lower().startswith(mark))
            said = line[len(mark):].strip("#=-*~ \t")
            if any(character.isalnum() for character in said) and not said.lower().startswith(SCRIPT_DIRECTIVE_PREFIXES):
                return said[:SCRIPT_SUMMARY_LIMIT]
        elif path.suffix == ".py" and line[:3] in {'"""', "'''"}:
            quote = line[:3]
            said = line[3:].removesuffix(quote).strip()
            if said != "" or (len(line) > 3 and line.endswith(quote)):
                return said[:SCRIPT_SUMMARY_LIMIT]
        elif line != "" and line.lower() != "@echo off":
            return ""
    return ""


def read_script_text(base_directory: str, source: str, name: str) -> ScriptText | ScriptProblem:
    places = script_places(base_directory)
    match places:
        case ScriptProblem():
            return places
        case _:
            root = dict(places).get(source)
    if root is None:
        return ScriptProblem(status=404, message=f"""There is no place for scripts called {source} here.""")
    relative = Path(name)
    path = root / relative
    # The name comes from the page, so it may only lead down from the place it was listed under. A link kept there is followed, as running it does.
    inside = relative.anchor == "" and ".." not in relative.parts
    if not inside or not is_supported_script_path(relative_path=relative, supported_suffixes=SCRIPT_SUFFIXES) or not path.is_file():
        return ScriptProblem(status=404, message=f"""{name} is no longer there. It may have been renamed or removed.""")
    if path.stat().st_size > MAX_EDITABLE_FILE_BYTES:
        return ScriptProblem(status=413, message=f"""This script is larger than {MAX_EDITABLE_FILE_BYTES // 1024} KB, which is more than is shown here. It can still be run.""")
    try:
        return {"text": path.read_text(encoding="utf-8")}
    except UnicodeDecodeError:
        return ScriptProblem(status=415, message="This file is not plain text, so it is not shown here. It can still be run.")


# A new script in the user's own folder or the project's, written with one line that says what it does and one that shows it ran.
def create_script(body: object) -> ScriptCreated | ScriptProblem:
    if not isinstance(body, dict):
        return ScriptProblem(status=400, message="Expected a JSON object.")
    payload = cast(dict[str, object], body)
    match (payload.get("base"), payload.get("source"), payload.get("name"), payload.get("suffix"), payload.get("summary")):
        case (str() as base_directory, str() as source, str() as name, str() as suffix, str() as summary) if suffix in SCRIPT_STARTERS:
            starter = SCRIPT_STARTERS[suffix]
        case _:
            return ScriptProblem(status=400, message=f"""`base`, `source`, `name` and `summary` must be text, and `suffix` one of {", ".join(SCRIPT_STARTERS)}.""")
    places = script_places(base_directory)
    match places:
        case ScriptProblem():
            return places
        case _:
            root = dict(places).get(source)
    if root is None or source == "library":
        return ScriptProblem(status=404, message=f"""Scripts cannot be added to {source} from here.""")
    relative = Path(name if name.endswith(suffix) else f"""{name}{suffix}""")
    if re.fullmatch(SCRIPT_NAME_PATTERN, name) is None or not is_supported_script_path(relative_path=relative, supported_suffixes=SCRIPT_SUFFIXES):
        return ScriptProblem(status=422, message="Name it with letters, digits, dots, dashes and underscores. A slash puts it in a folder, as in tools/cleanup.")
    path = root / relative
    if path.exists():
        return ScriptProblem(status=409, message=f"""There is already a script called {relative.as_posix()} there.""")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(starter.format(summary=" ".join(summary.split()) or SCRIPT_STARTER_SUMMARY, name=relative.name), encoding="utf-8")
    return {"source": source, "name": relative.as_posix(), "path": str(path)}
