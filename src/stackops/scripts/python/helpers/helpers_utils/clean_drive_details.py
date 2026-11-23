import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import TypedDict, cast

from stackops.scripts.python.helpers.helpers_utils.clean_drive_constants import DETAIL_ITEM_LIMIT
from stackops.scripts.python.helpers.helpers_utils.clean_drive_models import DetailItem, DockerKind, TargetDetails
from stackops.scripts.python.helpers.helpers_utils.clean_drive_usage import parse_size


BREW_REMOVAL_PATTERN = re.compile(r"^Would remove: (?P<path>.+) \((?:(?P<files>[\d,]+ files), )?(?P<size>[^,()]+)\)$", re.MULTILINE)
BLEACHBIT_ITEM_PATTERN = re.compile(r"^(?:Delete|Truncate) (?P<size>\S+) (?P<path>.+)$", re.MULTILINE)
BLEACHBIT_UNKNOWN_SIZE = "?B"
DOCKER_UNKNOWN_SIZE = "N/A"
DOCKER_ACTIVE_STATES = ("running", "paused", "restarting")
DOCKER_UNTAGGED = "<none>"
DOCKER_ID_PREFIX = "sha256:"
DOCKER_SHORT_ID_LENGTH = 12
DOCKER_NO_CREATION_DATE = ("0001-01-01", "1970-01-01")


class DockerImageRow(TypedDict):
    ID: str
    Repository: str
    Tag: str
    Containers: str
    CreatedAt: str
    CreatedSince: str
    Size: str
    SharedSize: str
    UniqueSize: str


class DockerContainerRow(TypedDict):
    Names: str
    Image: str
    State: str
    Status: str
    Size: str


class DockerVolumeRow(TypedDict):
    Name: str
    Links: str
    Size: str


class DockerBuildCacheRow(TypedDict):
    ID: str
    CacheType: str
    Description: str
    InUse: str
    Shared: str
    LastUsedSince: str
    Size: str


class DockerVerboseUsage(TypedDict):
    Images: list[DockerImageRow]
    Containers: list[DockerContainerRow]
    Volumes: list[DockerVolumeRow]
    BuildCache: list[DockerBuildCacheRow]


class DetailItemRecord(TypedDict):
    name: str
    note: str
    bytes: int | None


class DetailsRecord(TypedDict):
    title: str
    count: int
    items: list[DetailItemRecord]


def biggest_details(*, title: str, items: Iterable[DetailItem]) -> TargetDetails | None:
    ranked = sorted(items, key=lambda item: -(item.bytes or 0))
    if not ranked:
        return None
    return TargetDetails(title=title, count=len(ranked), items=tuple(ranked[:DETAIL_ITEM_LIMIT]))


def docker_removable(*, kind: DockerKind, output: str) -> tuple[str, list[DetailItem]]:
    usage = cast(DockerVerboseUsage, json.loads(output))
    rows: list[tuple[str, str, str]]
    match kind:
        case "Containers":
            title = "Stopped containers"
            rows = [
                (
                    row["Names"],
                    f"""{row["Status"]} · image {row["Image"].removeprefix(DOCKER_ID_PREFIX)[:DOCKER_SHORT_ID_LENGTH] if row["Image"].startswith(DOCKER_ID_PREFIX) else row["Image"]}""",
                    row["Size"].split(" (")[0],
                )
                for row in usage["Containers"] if row["State"] not in DOCKER_ACTIVE_STATES
            ]
        case "Images":
            title = "Images no container uses"
            rows = [
                (
                    row["ID"].removeprefix(DOCKER_ID_PREFIX)[:DOCKER_SHORT_ID_LENGTH] if row["Repository"] == DOCKER_UNTAGGED else f"""{row["Repository"]}:{row["Tag"]}""",
                    " · ".join(part for part in (
                        "untagged" if row["Repository"] == DOCKER_UNTAGGED else "",
                        "" if row["CreatedAt"].startswith(DOCKER_NO_CREATION_DATE) else f"""created {row["CreatedSince"]}""",
                        "" if row["SharedSize"] in ("0B", DOCKER_UNKNOWN_SIZE) else f"""{row["Size"]} with the layers other images also use""",
                    ) if part),
                    row["UniqueSize"],
                )
                for row in usage["Images"] if row["Containers"] == "0"
            ]
        case "Local Volumes":
            title = "Volumes no container uses"
            rows = [(row["Name"], "", row["Size"]) for row in usage["Volumes"] if row["Links"] == "0"]
        case "Build Cache":
            title = "Build layers nothing uses"
            rows = [
                (row["Description"] or row["ID"], f"""{row["CacheType"]} · last used {row["LastUsedSince"].lower()}""", row["Size"])
                for row in usage["BuildCache"] if row["InUse"] == "false" and row["Shared"] == "false"
            ]
    return title, [DetailItem(name=name, note=note, bytes=None if size == DOCKER_UNKNOWN_SIZE else parse_size(size)) for name, note, size in rows]


def brew_details(output: str) -> TargetDetails | None:
    return biggest_details(title="What Homebrew removes", items=(
        DetailItem(name=match["path"], note=match["files"] or "", bytes=parse_size(match["size"]))
        for match in BREW_REMOVAL_PATTERN.finditer(output)
    ))


def bleachbit_details(output: str) -> TargetDetails | None:
    folders: dict[str, tuple[int, int]] = {}
    for match in BLEACHBIT_ITEM_PATTERN.finditer(output):
        folder = str(Path(match["path"]).parent)
        size, files = folders.get(folder, (0, 0))
        folders[folder] = (size + (0 if match["size"] == BLEACHBIT_UNKNOWN_SIZE else parse_size(match["size"])), files + 1)
    return biggest_details(title="Folders with the most to delete", items=(
        DetailItem(name=folder, note=f"""{files:,} {"file" if files == 1 else "files"}""", bytes=size) for folder, (size, files) in folders.items()
    ))


def details_record(details: TargetDetails | None) -> DetailsRecord | None:
    if details is None:
        return None
    return {
        "title": details.title, "count": details.count,
        "items": [{"name": item.name, "note": item.note, "bytes": item.bytes} for item in details.items],
    }
