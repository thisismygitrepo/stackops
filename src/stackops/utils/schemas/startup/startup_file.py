from pathlib import Path
from typing import cast

import yaml

from stackops.profile.dotfiles_constants import ALL_OS_VALUES
from stackops.utils.schemas.startup.startup_constants import STARTUP_ENTRY_KEYS, STARTUP_FILE_VERSION, STARTUP_KINDS, STARTUP_SCHEMA_URL, STARTUP_WHENS
from stackops.utils.schemas.startup.startup_types import StartupFile
from stackops.utils.schemas.yaml_document import yaml_document_text
from stackops.utils.schemas.yaml_schema import JsonValue


def read_startup_file(path: Path) -> StartupFile:
    try:
        document = cast(JsonValue, yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.CSafeLoader))
    except yaml.YAMLError as error:
        raise ValueError(f"""Invalid YAML in startup file '{path}': {error}""") from error
    if not isinstance(document, dict):
        raise ValueError(f"""Invalid startup file '{path}': expected a mapping at the top level.""")
    if document.get("version") != STARTUP_FILE_VERSION:
        raise ValueError(f"""Invalid startup file '{path}': 'version' must be the quoted string "{STARTUP_FILE_VERSION}", got {document.get("version")!r}.""")
    entries = document.get("entries")
    if not isinstance(entries, list):
        raise ValueError(f"""Invalid startup file '{path}': 'entries' must be a list.""")
    named: set[tuple[JsonValue, JsonValue, JsonValue]] = set()
    for index, entry in enumerate(entries):
        location = f"""'{path}' at entries[{index}]"""
        if not isinstance(entry, dict):
            raise ValueError(f"""Invalid entry in {location}: expected a mapping.""")
        if frozenset(entry) != STARTUP_ENTRY_KEYS:
            raise ValueError(f"""Invalid entry in {location}: it must have exactly the keys {", ".join(sorted(STARTUP_ENTRY_KEYS))}, and has {", ".join(sorted(str(key) for key in entry))}.""")
        if entry["kind"] not in STARTUP_KINDS:
            raise ValueError(f"""Invalid entry in {location}: 'kind' must be one of {", ".join(STARTUP_KINDS)}, got {entry["kind"]!r}.""")
        if not isinstance(entry["name"], str) or entry["name"] == "":
            raise ValueError(f"""Invalid entry in {location}: 'name' must be a non-empty string, got {entry["name"]!r}.""")
        systems = entry["os"]
        if not isinstance(systems, list) or len(systems) == 0 or any(system not in ALL_OS_VALUES for system in systems):
            raise ValueError(f"""Invalid entry in {location}: 'os' must be a non-empty list from {", ".join(ALL_OS_VALUES)}, got {systems!r}.""")
        if entry["when"] not in STARTUP_WHENS:
            raise ValueError(f"""Invalid entry in {location}: 'when' must be one of {", ".join(STARTUP_WHENS)}, got {entry["when"]!r}.""")
        for system in systems:
            if (entry["kind"], entry["name"], system) in named:
                raise ValueError(f"""Invalid entry in {location}: {entry["name"]} is already listed for {system}.""")
            named.add((entry["kind"], entry["name"], system))
    return cast(StartupFile, document)


def write_startup_file(path: Path, startup_file: StartupFile) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""# yaml-language-server: $schema={STARTUP_SCHEMA_URL}

{yaml_document_text(document=startup_file)}""",
        encoding="utf-8",
    )
