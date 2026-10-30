import filecmp
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from stackops.profile.dotfiles_constants import COLLECTED_SETTINGS_TOKEN_PREFIX, PACKAGED_SETTINGS_TOKEN_PREFIX, OsName
from stackops.profile.dotfiles_mapper import MapperDocument, RawMapperEntry
from stackops.utils.source_of_truth import resolve_source_of_truth_path

type CollectVerdict = Literal[
    "collect",
    "linked",
    "stored",
    "recorded",
    "other_os",
    "absent",
    "packaged",
    "unreadable",
    "own_link",
    "not_a_directory",
    "managed_path_exists",
    "original_mapped",
    "managed_path_mapped",
    "user_group",
]
type PathState = Literal["missing", "unreadable", "symlink", "directory", "file"]

ACTIONABLE_VERDICTS: frozenset[CollectVerdict] = frozenset({"collect", "linked", "stored"})
CONTENTS_BLOCKING_VERDICTS: tuple[CollectVerdict, ...] = ("unreadable", "own_link", "managed_path_exists")


@dataclass(frozen=True, slots=True)
class CollectEntryPlan:
    group: str
    name: str
    entry: RawMapperEntry
    original_path: Path
    managed_path: Path
    packaged_path: Path | None
    verdict: CollectVerdict


def _probe_path(path: Path) -> PathState:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError, NotADirectoryError:
        return "missing"
    except PermissionError:
        return "unreadable"
    if stat.S_ISLNK(mode):
        return "symlink"
    return "directory" if stat.S_ISDIR(mode) else "file"


def _matches_packaged(path: Path, packaged_path: Path) -> bool:
    if path.is_dir() and packaged_path.is_dir():
        names = sorted(child.name for child in path.iterdir())
        return names == sorted(child.name for child in packaged_path.iterdir()) and all(
            _matches_packaged(path.joinpath(name), packaged_path.joinpath(name)) for name in names
        )
    return path.is_file() and packaged_path.is_file() and filecmp.cmp(path, packaged_path, shallow=False)


def _classify_pair(original_path: Path, managed_path: Path, packaged_path: Path | None) -> CollectVerdict:
    managed_exists = _probe_path(managed_path) != "missing"
    match _probe_path(original_path):
        case "missing":
            return "stored" if managed_exists else "absent"
        case "unreadable":
            return "unreadable"
        case "symlink":
            original_target = original_path.resolve()
            if managed_exists and original_target == managed_path.resolve():
                return "linked"
            return "packaged" if packaged_path is not None and original_target == packaged_path.resolve() else "own_link"
        case "directory" | "file":
            if managed_exists:
                return "managed_path_exists"
            return "packaged" if packaged_path is not None and _matches_packaged(original_path, packaged_path) else "collect"


def _classify_contents(original_path: Path, managed_path: Path, packaged_path: Path | None) -> CollectVerdict:
    match _probe_path(original_path):
        case "file":
            return "not_a_directory"
        case "missing" | "unreadable" | "symlink":
            return _classify_pair(original_path, managed_path, packaged_path)
        case "directory":
            try:
                children = sorted(original_path.iterdir())
            except PermissionError:
                return "unreadable"
            child_verdicts = {
                _classify_pair(child, managed_path.joinpath(child.name), None if packaged_path is None else packaged_path.joinpath(child.name))
                for child in children
            }
            if len(child_verdicts) == 0:
                return "stored" if _probe_path(managed_path) != "missing" else "absent"
            for blocking_verdict in CONTENTS_BLOCKING_VERDICTS:
                if blocking_verdict in child_verdicts:
                    return blocking_verdict
            if child_verdicts == {"packaged"}:
                return "packaged"
            if child_verdicts == {"linked"}:
                return "linked"
            return "collect"


def _build_catalog(personal_catalog: MapperDocument, library_mapper: MapperDocument) -> tuple[MapperDocument, dict[tuple[str, str], Path]]:
    catalog: MapperDocument = {group: dict(section) for group, section in personal_catalog.items()}
    packaged_paths: dict[tuple[str, str], Path] = {}
    for group, section in library_mapper.items():
        for name, entry in section.items():
            packaged_value = entry["self_managed"]
            if not packaged_value.startswith(PACKAGED_SETTINGS_TOKEN_PREFIX):
                raise ValueError(f"""Library mapper entry {group}.{name} must keep its managed copy under {PACKAGED_SETTINGS_TOKEN_PREFIX}: {packaged_value}""")
            collected_entry: RawMapperEntry = {**entry, "self_managed": COLLECTED_SETTINGS_TOKEN_PREFIX + packaged_value.removeprefix(PACKAGED_SETTINGS_TOKEN_PREFIX)}
            catalog.setdefault(group, {})[name] = collected_entry
            packaged_paths[(group, name)] = resolve_source_of_truth_path(packaged_value)
    return catalog, packaged_paths


def plan_collect(
    *, personal_catalog: MapperDocument, library_mapper: MapperDocument, user_mapper: MapperDocument, current_os: OsName
) -> list[CollectEntryPlan]:
    catalog, packaged_paths = _build_catalog(personal_catalog, library_mapper)
    previously_collected_groups = {
        group
        for group, section in user_mapper.items()
        if group in catalog and all(catalog[group].get(name) == entry for name, entry in section.items())
    }
    claimed_entries = [entry for group, section in user_mapper.items() if group not in previously_collected_groups for entry in section.values()]
    claimed_originals = [Path(entry["original"]).expanduser().absolute() for entry in claimed_entries]
    claimed_managed_paths = [resolve_source_of_truth_path(entry["self_managed"]) for entry in claimed_entries]
    plans: list[CollectEntryPlan] = []
    for group, section in catalog.items():
        for name, entry in section.items():
            original_path = Path(entry["original"]).expanduser().absolute()
            managed_path = resolve_source_of_truth_path(entry["self_managed"])
            packaged_path = packaged_paths.get((group, name))
            verdict: CollectVerdict
            if group in user_mapper and group not in previously_collected_groups:
                verdict = "user_group"
            elif name in user_mapper.get(group, {}):
                verdict = "recorded"
            elif any(original_path == claimed or original_path.is_relative_to(claimed) or claimed.is_relative_to(original_path) for claimed in claimed_originals):
                verdict = "original_mapped"
            elif any(managed_path == claimed or managed_path.is_relative_to(claimed) or claimed.is_relative_to(managed_path) for claimed in claimed_managed_paths):
                verdict = "managed_path_mapped"
            elif current_os not in entry["os"]:
                verdict = "other_os"
            elif entry.get("contents", False):
                verdict = _classify_contents(original_path, managed_path, packaged_path)
            else:
                verdict = _classify_pair(original_path, managed_path, packaged_path)
            plans.append(
                CollectEntryPlan(
                    group=group, name=name, entry=entry, original_path=original_path, managed_path=managed_path, packaged_path=packaged_path, verdict=verdict
                )
            )
    return plans


def select_entries_to_record(*, plans: list[CollectEntryPlan], succeeded: set[tuple[str, str]]) -> MapperDocument:
    succeeded_groups = {group for group, _name in succeeded}
    anchored_managed_paths = {
        (plan.group, plan.managed_path)
        for plan in plans
        if plan.group in succeeded_groups and ((plan.group, plan.name) in succeeded or plan.verdict == "recorded")
    }
    additions: MapperDocument = {}
    for plan in plans:
        is_succeeded = (plan.group, plan.name) in succeeded
        is_other_os_sibling = plan.verdict == "other_os" and (plan.group, plan.managed_path) in anchored_managed_paths
        if is_succeeded or is_other_os_sibling:
            additions.setdefault(plan.group, {})[plan.name] = plan.entry
    return additions
