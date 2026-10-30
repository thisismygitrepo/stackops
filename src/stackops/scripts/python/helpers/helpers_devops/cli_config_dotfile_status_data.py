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
class LoadedMappers:
    user_exists: bool
    user: MapperDocument
    library: MapperDocument
    catalog: MapperDocument


@dataclass(frozen=True, slots=True)
class MapperCounts:
    groups: int
    entries: int
    entries_per_os: dict[OsName, int]


@dataclass(frozen=True, slots=True)
class MappersStatus:
    user_counts: MapperCounts | None
    library_counts: MapperCounts
    user_group_counts: dict[str, MapperCounts]
    replaced_library_entries: list[tuple[str, str]]


@dataclass(frozen=True, slots=True)
class SyncStatus:
    user: list[ConfigFileStatus]
    library: list[ConfigFileStatus]


@dataclass(frozen=True, slots=True)
class Footprint:
    files: int
    size_bytes: int


@dataclass(frozen=True, slots=True)
class ManagedCopy:
    path: Path
    entries: list[tuple[str, str]]
    footprint: Footprint


@dataclass(frozen=True, slots=True)
class StorageStatus:
    dotfiles_root_footprint: Footprint | None
    managed_copies: list[ManagedCopy]
    managed_footprint: Footprint
    outside_dotfiles_root: list[tuple[str, str, Path]]
    unreferenced_stored_paths: list[Path]


def load_mappers() -> LoadedMappers:
    user_exists = USER_MAPPER_PATH.exists()
    return LoadedMappers(
        user_exists=user_exists,
        user=load_dotfiles_mapper(USER_MAPPER_PATH) if user_exists else {},
        library=load_dotfiles_mapper(LIBRARY_MAPPER_PATH),
        catalog=load_dotfiles_mapper(USER_EXAMPLE_MAPPER_PATH),
    )


def _select_groups(mapper: MapperDocument, groups: frozenset[str] | None) -> MapperDocument:
    return mapper if groups is None else {group: section for group, section in mapper.items() if group in groups}


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


def _measure_footprint(root: Path) -> Footprint:
    if root.is_dir() and not root.is_symlink():
        files = 0
        size_bytes = 0
        for directory, _directory_names, file_names in root.walk():
            files += len(file_names)
            size_bytes += sum(directory.joinpath(file_name).lstat().st_size for file_name in file_names)
        return Footprint(files=files, size_bytes=size_bytes)
    if root.exists() or root.is_symlink():
        return Footprint(files=1, size_bytes=root.lstat().st_size)
    return Footprint(files=0, size_bytes=0)


def collect_mappers_status(mappers: LoadedMappers, groups: frozenset[str] | None) -> MappersStatus:
    user_mapper = _select_groups(mappers.user, groups)
    library_mapper = _select_groups(mappers.library, groups)
    return MappersStatus(
        user_counts=_count_entries(user_mapper) if mappers.user_exists else None,
        library_counts=_count_entries(library_mapper),
        user_group_counts={group: _count_entries({group: section}) for group, section in user_mapper.items()},
        replaced_library_entries=[(group, name) for group, section in library_mapper.items() for name in section if name in user_mapper.get(group, {})],
    )


def collect_sync_status(mappers: LoadedMappers, groups: frozenset[str] | None, current_os: OsName) -> SyncStatus:
    effective_library = compose_mapper_documents(library_mapper=mappers.library, user_mapper=mappers.user, source="library")
    return SyncStatus(
        user=_check_sync(_select_groups(mappers.user, groups), current_os), library=_check_sync(_select_groups(effective_library, groups), current_os)
    )


def collect_radar_status(mappers: LoadedMappers, groups: frozenset[str] | None, current_os: OsName) -> list[CollectEntryPlan]:
    plans = plan_collect(personal_catalog=mappers.catalog, library_mapper=mappers.library, user_mapper=mappers.user, current_os=current_os)
    return [plan for plan in plans if groups is None or plan.group in groups]


def collect_storage_status(mappers: LoadedMappers, groups: frozenset[str] | None) -> StorageStatus:
    all_managed_paths = {resolve_source_of_truth_path(entry["self_managed"]) for section in mappers.user.values() for entry in section.values()}
    entries_by_path: dict[Path, list[tuple[str, str]]] = {}
    for group, section in _select_groups(mappers.user, groups).items():
        for name, entry in section.items():
            entries_by_path.setdefault(resolve_source_of_truth_path(entry["self_managed"]), []).append((group, name))
    managed_copies = sorted(
        (ManagedCopy(path=path, entries=entries, footprint=_measure_footprint(path)) for path, entries in entries_by_path.items()),
        key=lambda copy: copy.footprint.size_bytes,
        reverse=True,
    )
    outermost_copies = [copy for copy in managed_copies if not any(copy.path != other and copy.path.is_relative_to(other) for other in entries_by_path)]
    dotfiles_root_resolved = DOTFILES_ROOT.resolve()
    stored_paths = sorted(DOTFILES_MAPPER_FILES_ROOT.iterdir()) if DOTFILES_MAPPER_FILES_ROOT.is_dir() else []
    return StorageStatus(
        dotfiles_root_footprint=_measure_footprint(dotfiles_root_resolved) if dotfiles_root_resolved.is_dir() else None,
        managed_copies=managed_copies,
        managed_footprint=Footprint(
            files=sum(copy.footprint.files for copy in outermost_copies), size_bytes=sum(copy.footprint.size_bytes for copy in outermost_copies)
        ),
        outside_dotfiles_root=[
            (group, name, path) for path, entries in entries_by_path.items() if not path.resolve().is_relative_to(dotfiles_root_resolved) for group, name in entries
        ],
        unreferenced_stored_paths=[
            stored_path
            for stored_path in stored_paths
            if not any(stored_path == path or path.is_relative_to(stored_path) or stored_path.is_relative_to(path) for path in all_managed_paths)
        ],
    )
