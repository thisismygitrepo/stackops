import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypedDict, get_args

from stackops.scripts.python.helpers.helpers_webui.settings_constants import FOLDER_FILE_KINDS, FileScope, SchemaStanding
from stackops.utils.managed_agent_files import resolve_agent_managed_file_path
from stackops.utils.managed_file_operations import initialize_managed_file, render_managed_file_content, validate_managed_file
from stackops.utils.managed_files import ManagedFileKind, ManagedFileSpec, get_managed_file_spec, managed_schema_path
from stackops.utils.repos.project import resolve_project_root
from stackops.utils.repos.stackops_paths import WORKSPACE_SOURCE_LABEL, RepoStackopsPathKind, workspace_stackops_paths

FILE_KINDS: tuple[ManagedFileKind, ...] = get_args(ManagedFileKind)


@dataclass(frozen=True, slots=True)
class SettingsProblem:
    status: int
    message: str


# One settings file the CLI manages. `kind` and `scope` together say which file: prompts and MCP servers have one of each scope.
# `available` is false for a project's file while the working folder is in no project: there is then no place
# for it, and `path` is empty. `blocked` says something other than a file lies at the path. `private` is a file only its owner may read.
class SettingsFile(TypedDict):
    kind: ManagedFileKind
    scope: FileScope
    available: bool
    path: str
    exists: bool
    blocked: bool
    size: int
    modified_at: float | None
    format: Literal["yaml", "json"]
    private: bool
    schema_path: str
    schema: SchemaStanding


class SettingsFiles(TypedDict):
    folder: str
    project: str
    files: list[SettingsFile]


class FileCheck(TypedDict):
    kind: ManagedFileKind
    ok: bool
    problem: str


class SettingsExample(TypedDict):
    kind: ManagedFileKind
    file_name: str
    schema_name: str
    text: str


# The one file a request is about.
@dataclass(frozen=True, slots=True)
class FileTarget:
    kind: ManagedFileKind
    scope: FileScope
    folder: Path


def read_working_folder(text: str) -> Path | SettingsProblem:
    folder = Path(os.path.expanduser(text))
    if text == "" or not folder.is_dir():
        return SettingsProblem(status=400, message=f"""There is no folder at {text or "an empty path"}.""")
    return folder


# Where files of a kind can belong, with the place `devops config` works on first.
def file_scopes(kind: ManagedFileKind) -> tuple[FileScope, ...]:
    return ("folder", "home") if kind in FOLDER_FILE_KINDS else ("home",)


def parse_file_kind(text: object) -> ManagedFileKind | SettingsProblem:
    for kind in FILE_KINDS:
        if kind == text:
            return kind
    return SettingsProblem(status=400, message=f"""`kind` must be one of {", ".join(FILE_KINDS)}.""")


# Which file a request means, from what it sent. A request that names no scope means the file `devops config` works on.
def read_file_target(kind: object, scope: object, base: object) -> FileTarget | SettingsProblem:
    parsed_kind = parse_file_kind(text=kind)
    folder = read_working_folder(text=base if isinstance(base, str) else "")
    match parsed_kind, folder:
        case (SettingsProblem() as problem, _) | (_, SettingsProblem() as problem):
            return problem
        case _:
            scopes = file_scopes(parsed_kind)
    if scope is None:
        return FileTarget(kind=parsed_kind, scope=scopes[0], folder=folder)
    for known in scopes:
        if known == scope:
            return FileTarget(kind=parsed_kind, scope=known, folder=folder)
    return SettingsProblem(status=400, message=f"""`scope` for a {parsed_kind} file must be one of {", ".join(scopes)}.""")


# Where the CLI keeps a file of this kind. A project's file is looked for the way the CLI does from inside `folder`; the CLI reads its own
# working folder for that, which for this server is not the folder the page works in. A person's own prompts and MCP servers are where
# `agents config path --source user` says.
def locate_settings_file(kind: ManagedFileKind, scope: FileScope, folder: Path) -> tuple[ManagedFileSpec, Path | None]:
    spec = get_managed_file_spec(kind)
    match kind:
        case "prompts" | "mcp":
            if scope == "home":
                return spec, resolve_agent_managed_file_path(kind=kind, source="user")
            path_kind: RepoStackopsPathKind = "prompts_yaml" if kind == "prompts" else "mcp_json"
            return spec, dict(workspace_stackops_paths(current_dir=folder, path_kind=path_kind)).get(WORKSPACE_SOURCE_LABEL)
        case _:
            return spec, spec.user_path


def describe_settings_file(kind: ManagedFileKind, scope: FileScope, folder: Path) -> SettingsFile:
    spec, data_path = locate_settings_file(kind=kind, scope=scope, folder=folder)
    file_format: Literal["yaml", "json"] = "yaml" if spec.user_path.suffix in {".yaml", ".yml"} else "json"
    if data_path is None:
        return {
            "kind": kind, "scope": scope, "available": False, "path": "", "exists": False, "blocked": False, "size": 0, "modified_at": None,
            "format": file_format, "private": False, "schema_path": "", "schema": "missing",
        }
    schema_path = managed_schema_path(spec=spec, data_path=data_path)
    schema: SchemaStanding = "missing"
    if schema_path.is_file():
        schema = "current" if schema_path.read_text(encoding="utf-8") == spec.schema_source_path.read_text(encoding="utf-8") else "outdated"
    exists = data_path.is_file()
    facts = data_path.stat() if exists else None
    return {
        "kind": kind, "scope": scope, "available": True, "path": str(data_path), "exists": exists, "blocked": data_path.exists() and not exists,
        "size": 0 if facts is None else facts.st_size, "modified_at": None if facts is None else facts.st_mtime, "format": file_format,
        "private": spec.file_mode & 0o077 == 0, "schema_path": str(schema_path), "schema": schema,
    }


# Every settings file and where it stands, without opening one: that is quick. Whether each passes its check is asked for one file at a time.
# The person's own files come first, then the project's.
def read_settings_files(folder: Path) -> SettingsFiles:
    project = resolve_project_root(current_dir=folder)
    scopes: tuple[FileScope, ...] = ("home", "folder")
    files = [describe_settings_file(kind=kind, scope=scope, folder=folder) for scope in scopes for kind in FILE_KINDS if scope in file_scopes(kind)]
    return {"folder": str(folder), "project": "" if project is None else str(project), "files": files}


def _located_path(target: FileTarget) -> Path | SettingsProblem:
    _spec, data_path = locate_settings_file(kind=target.kind, scope=target.scope, folder=target.folder)
    if data_path is None:
        return SettingsProblem(status=409, message=f"""{target.folder} is not part of a project, so there is no {target.kind} file for it.""")
    return data_path


# The check `devops config validate` runs: the schema first, then the reader the CLI itself uses for that file. Takes about half a second,
# because the schema check runs in a process of its own.
def check_settings_file(target: FileTarget) -> FileCheck | SettingsProblem:
    data_path = _located_path(target=target)
    match data_path:
        case SettingsProblem():
            return data_path
        case _:
            if not data_path.is_file():
                return SettingsProblem(status=404, message=f"""There is no {target.kind} file at {data_path}.""")
    try:
        validate_managed_file(kind=target.kind, data_path=data_path)
    except (OSError, ValueError) as error:
        return {"kind": target.kind, "ok": False, "problem": str(error)}
    return {"kind": target.kind, "ok": True, "problem": ""}


# What `devops config init` does. A missing file is made from the packaged example with its schema beside it. One that is there keeps its
# content: it gets the current schema beside it and the line that points to that schema, where either is missing.
def create_settings_file(target: FileTarget) -> SettingsFile | SettingsProblem:
    data_path = _located_path(target=target)
    match data_path:
        case SettingsProblem():
            return data_path
        case _:
            spec = get_managed_file_spec(target.kind)
    try:
        initialize_managed_file(spec=spec, data_path=data_path)
    except (OSError, ValueError) as error:
        return SettingsProblem(status=409, message=str(error))
    return describe_settings_file(kind=target.kind, scope=target.scope, folder=target.folder)


# The example StackOps ships for a file, as a new file of that kind starts out.
def read_settings_example(kind: ManagedFileKind) -> SettingsExample:
    spec = get_managed_file_spec(kind)
    return {
        "kind": kind,
        "file_name": spec.user_path.name,
        "schema_name": managed_schema_path(spec=spec, data_path=spec.user_path).name,
        "text": render_managed_file_content(spec=spec, data_path=spec.user_path, content=spec.example_source_path.read_text(encoding="utf-8")),
    }
