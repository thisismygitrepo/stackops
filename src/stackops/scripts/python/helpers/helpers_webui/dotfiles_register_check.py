import os
from itertools import islice
from pathlib import Path
from typing import Literal, TypedDict

import yaml

from stackops.profile.dotfiles_mapper import MapperDocument, RawMapperEntry
from stackops.profile.linking.operations import files_are_identical
from stackops.profile.linking.options import METHOD_STRICT
from stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_mapper import (
    _build_mapper_entry,  # pyright: ignore[reportPrivateUsage]
    _build_mapper_preview,  # pyright: ignore[reportPrivateUsage]
    _resolve_entry_name,  # pyright: ignore[reportPrivateUsage]
    get_backup_path,
)
from stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_status_data import load_mappers
from stackops.scripts.python.helpers.helpers_webui.dotfiles_constants import DOTFILES_MEASURE_FILE_LIMIT
from stackops.scripts.python.helpers.helpers_webui.dotfiles_model import DotfilesProblem, typed_path
from stackops.utils.source_of_truth import DOTFILES_ROOT, DOTFILES_USER_MAPPER_PATH

type PathKind = Literal["file", "folder", "link", "broken_link", "other", "missing"]
# Where the two sides stand, which decides what the register command does. The cases are the ones `copy_map` and `symlink_map` tell apart:
# `collect` is a file here with nothing kept yet, `restore` a kept copy with nothing here, `empty` a link here that points at nothing, and
# `linked` a file that already is its kept copy, which the command refuses.
type RegisterState = Literal["missing", "empty", "restore", "collect", "collect_link", "linked", "relink", "identical", "conflict"]


# `measured_whole` is false for a folder with more files than the page counts; `files` and `size_bytes` then cover the part that was counted.
class PathFacts(TypedDict):
    path: str
    kind: PathKind
    files: int
    size_bytes: int
    measured_whole: bool
    points_to: str


class ListedEntry(TypedDict):
    source: Literal["user", "library"]
    group: str
    name: str
    copy: bool


# `listed` holds the entries that already manage this path. `replaces` is the path of the entry this one would overwrite in the list, when the
# group already has one of that name. `preview` is the entry as the command will write it, made by the command's own functions.
class RegisterCheck(TypedDict):
    file: PathFacts
    kept: PathFacts
    state: RegisterState
    inside_store: bool
    listed: list[ListedEntry]
    group: str
    name: str
    replaces: str
    note: str
    preview: str
    groups: list[str]
    list_path: str
    list_problem: str


class RegisterQuestion(TypedDict):
    file: str
    base: str
    method: METHOD_STRICT
    destination: str
    shared: bool
    name: str
    group: str
    os_filter: str
    note: str | None


def _describe(path: Path) -> PathFacts:
    points_to = str(path.readlink()) if path.is_symlink() else ""
    if not path.exists():
        return {"path": str(path), "kind": "broken_link" if path.is_symlink() else "missing", "files": 0, "size_bytes": 0, "measured_whole": True, "points_to": points_to}
    kind: PathKind = "link" if path.is_symlink() else "folder" if path.is_dir() else "file" if path.is_file() else "other"
    if not path.is_dir():
        return {"path": str(path), "kind": kind, "files": 1, "size_bytes": path.stat().st_size, "measured_whole": True, "points_to": points_to}
    sizes = list(
        islice((Path(directory, name).lstat().st_size for directory, _directory_names, names in os.walk(path) for name in names), DOTFILES_MEASURE_FILE_LIMIT + 1)
    )
    counted = sizes[:DOTFILES_MEASURE_FILE_LIMIT]
    return {"path": str(path), "kind": kind, "files": len(counted), "size_bytes": sum(counted), "measured_whole": len(sizes) <= DOTFILES_MEASURE_FILE_LIMIT, "points_to": points_to}


def _state(original: Path, kept: Path) -> RegisterState:
    if not original.exists() and not kept.exists():
        return "empty" if original.is_symlink() else "missing"
    if not original.exists():
        return "restore"
    if not kept.exists():
        return "collect_link" if original.is_symlink() else "collect"
    if original.resolve() == kept.resolve():
        return "linked"
    if original.is_symlink():
        return "relink"
    return "identical" if files_are_identical(original, kept) else "conflict"


# What adding this file would do, before anything is done: what is at the typed path, where its copy would be kept and what is there now,
# whether it is managed already, and the entry that would be written to the list.
def check_register(question: RegisterQuestion) -> RegisterCheck | DotfilesProblem:
    original = typed_path(text=question["file"], base_directory=question["base"])
    kept = get_backup_path(orig_path=original, destination=question["destination"].strip() or None, shared=question["shared"])
    user: MapperDocument = {}
    library: MapperDocument = {}
    list_problem = ""
    try:
        mappers = load_mappers()
        user, library = mappers.user, mappers.library
    except (OSError, TypeError, ValueError, yaml.YAMLError) as error:
        list_problem = str(error)
    group = question["group"].strip() or "default"
    name = _resolve_entry_name(original, question["name"])
    try:
        entry: RawMapperEntry = _build_mapper_entry(original_path=original, self_managed_path=kept, method=question["method"], is_contents=False, os_filter=question["os_filter"])
    except ValueError as error:
        return DotfilesProblem(status=400, message=str(error))
    existing = user.get(group, {}).get(name)
    # The command keeps the note an entry already has unless it is given one, and an empty one clears it.
    note = (existing or {}).get("note", "") if question["note"] is None else question["note"].strip()
    if note != "":
        entry["note"] = note
    sources: tuple[tuple[Literal["user", "library"], MapperDocument], ...] = (("user", user), ("library", library))
    listed: list[ListedEntry] = [
        {"source": source, "group": listed_group, "name": listed_name, "copy": listed_entry.get("copy", False)}
        for source, mapper in sources
        for listed_group, section in mapper.items()
        for listed_name, listed_entry in section.items()
        if Path(os.path.expanduser(listed_entry["original"])) == original
    ]
    try:
        return {
            "file": _describe(original),
            "kept": _describe(kept),
            "state": _state(original=original, kept=kept),
            "inside_store": original.is_relative_to(DOTFILES_ROOT),
            "listed": listed,
            "group": group,
            "name": name,
            "replaces": "" if existing is None else existing["original"],
            "note": note,
            "preview": _build_mapper_preview(section=group, entry_name=name, entry=entry),
            "groups": sorted(user),
            "list_path": str(DOTFILES_USER_MAPPER_PATH),
            "list_problem": list_problem,
        }
    except OSError as error:
        return DotfilesProblem(status=500, message=f"""That path could not be read: {error}""")
