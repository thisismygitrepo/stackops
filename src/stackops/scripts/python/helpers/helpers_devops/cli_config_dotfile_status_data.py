from dataclasses import dataclass
from pathlib import Path

from stackops.profile.create_links import to_config_mapper
from stackops.profile.dotfiles_collect_plan import CollectEntryPlan, plan_collect
from stackops.profile.dotfiles_constants import ALL_OS_VALUES, OsName
from stackops.profile.dotfiles_mapper import (
    LIBRARY_MAPPER_PATH,
    USER_EXAMPLE_MAPPER_PATH,
    USER_MAPPER_PATH,
    MapperDocument,
    compose_mapper_documents,
    load_dotfiles_mapper,
)
from stackops.scripts.python.helpers.helpers_devops.devops_status_config import ConfigFileStatus, check_config_file
from stackops.utils.source_of_truth import DOTFILES_MAPPER_FILES_ROOT, DOTFILES_ROOT, resolve_source_of_truth_path


@dataclass(frozen=True, slots=True)
class MapperCounts:
    groups: int
    entries: int
    entries_per_os: dict[OsName, int]


@dataclass(frozen=True, slots=True)
class Footprint:
    files: int
    size_bytes: int


@dataclass(frozen=True, slots=True)
class DotfilesStatus:
    current_os: OsName
    user_counts: MapperCounts | None
    library_counts: MapperCounts
    replaced_library_entries: int
    user_sync: list[ConfigFileStatus]
    library_sync: list[ConfigFileStatus]
    radar: list[CollectEntryPlan]
    dotfiles_root_footprint: Footprint | None
    managed_path_count: int
    managed_footprint: Footprint
    outside_dotfiles_root: list[tuple[str, str, Path]]
    unreferenced_stored_paths: list[Path]


def _count_entries(mapper: MapperDocument) -> MapperCounts:
    entries = [entry for section in mapper.values() for entry in section.values()]
    return MapperCounts(
        groups=len(mapper),
        entries=len(entries),
        entries_per_os={os_name: sum(os_name in entry["os"] for entry in entries) for os_name in ALL_OS_VALUES},
    )


def _check_sync(mapper: MapperDocument, current_os: OsName) -> list[ConfigFileStatus]:
    return [
        check_config_file(group, to_config_mapper(file_name=name, entry=entry))
        for group, section in mapper.items()
        for name, entry in section.items()
        if current_os in entry["os"]
    ]


def _measure_footprint(roots: list[Path]) -> Footprint:
    distinct_roots = set(roots)
    outermost_roots = [root for root in distinct_roots if not any(root != other and root.is_relative_to(other) for other in distinct_roots)]
    files = 0
    size_bytes = 0
    for root in outermost_roots:
        if root.is_dir() and not root.is_symlink():
            for directory, _directory_names, file_names in root.walk():
                files += len(file_names)
                size_bytes += sum(directory.joinpath(file_name).lstat().st_size for file_name in file_names)
        elif root.exists() or root.is_symlink():
            files += 1
            size_bytes += root.lstat().st_size
    return Footprint(files=files, size_bytes=size_bytes)


def collect_dotfiles_status(current_os: OsName) -> DotfilesStatus:
    user_mapper = load_dotfiles_mapper(USER_MAPPER_PATH) if USER_MAPPER_PATH.exists() else None
    known_user_mapper: MapperDocument = {} if user_mapper is None else user_mapper
    library_mapper = load_dotfiles_mapper(LIBRARY_MAPPER_PATH)
    library_counts = _count_entries(library_mapper)
    effective_library = compose_mapper_documents(library_mapper=library_mapper, user_mapper=known_user_mapper, source="library")
    user_managed = [
        (group, name, resolve_source_of_truth_path(entry["self_managed"]))
        for group, section in known_user_mapper.items()
        for name, entry in section.items()
    ]
    managed_paths = [managed_path for _group, _name, managed_path in user_managed]
    dotfiles_root_resolved = DOTFILES_ROOT.resolve()
    stored_paths = sorted(DOTFILES_MAPPER_FILES_ROOT.iterdir()) if DOTFILES_MAPPER_FILES_ROOT.is_dir() else []
    return DotfilesStatus(
        current_os=current_os,
        user_counts=None if user_mapper is None else _count_entries(user_mapper),
        library_counts=library_counts,
        replaced_library_entries=library_counts.entries - _count_entries(effective_library).entries,
        user_sync=_check_sync(known_user_mapper, current_os),
        library_sync=_check_sync(effective_library, current_os),
        radar=plan_collect(
            personal_catalog=load_dotfiles_mapper(USER_EXAMPLE_MAPPER_PATH),
            library_mapper=library_mapper,
            user_mapper=known_user_mapper,
            current_os=current_os,
        ),
        dotfiles_root_footprint=_measure_footprint([dotfiles_root_resolved]) if dotfiles_root_resolved.is_dir() else None,
        managed_path_count=len(set(managed_paths)),
        managed_footprint=_measure_footprint(managed_paths),
        outside_dotfiles_root=[
            (group, name, managed_path)
            for group, name, managed_path in user_managed
            if not managed_path.resolve().is_relative_to(dotfiles_root_resolved)
        ],
        unreferenced_stored_paths=[
            stored_path
            for stored_path in stored_paths
            if not any(stored_path == managed_path or managed_path.is_relative_to(stored_path) or stored_path.is_relative_to(managed_path) for managed_path in managed_paths)
        ],
    )
