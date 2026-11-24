import os
import platform
from pathlib import Path
from typing import Literal, TypedDict

from stackops.profile.migration_until_2028_01_bash_zsh_hook import STALE_HOOKS
from stackops.profile.shell_profile_source import build_shell_profile_source
from stackops.scripts.python.helpers.helpers_webui.settings_constants import ASSET_NAMES_SENT, ASSET_NOISE_NAMES, ASSET_TEMPLATE_TOKEN, ASSET_TEMPLATED_FILE
from stackops.utils.source_of_truth import CONFIG_ROOT, LIBRARY_ROOT

type AssetSetId = Literal["scripts", "settings"]


# One folder of what StackOps ships, held against the copy on this machine. `extra` counts files that are only on this machine. The names are
# paths inside the set, at most ASSET_NAMES_SENT of each kind.
class AssetGroup(TypedDict):
    name: str
    offered: int
    same: int
    changed: int
    missing: int
    extra: int
    changed_names: list[str]
    missing_names: list[str]
    extra_names: list[str]


# `replaces` says a copy removes the folder on this machine first, so what is only there goes. The scripts folder is copied file by file, and
# also holds the person's own scripts, so nothing in it counts as extra.
class AssetSet(TypedDict):
    id: AssetSetId
    target: str
    on_machine: bool
    replaces: bool
    groups: list[AssetGroup]


# `old_profile_lines` are the shell profiles that still load StackOps the old way: copying the settings rewrites that line and keeps a backup.
class AssetsState(TypedDict):
    supported: bool
    sets: list[AssetSet]
    old_profile_lines: list[str]


def _files_under(root: Path) -> dict[str, Path]:
    found: dict[str, Path] = {}
    for folder, folder_names, file_names in os.walk(root):
        folder_names[:] = [name for name in folder_names if name not in ASSET_NOISE_NAMES]
        for name in file_names:
            if name not in ASSET_NOISE_NAMES:
                path = Path(folder, name)
                found[path.relative_to(root).as_posix()] = path
    return found


def _matches(source: Path, target: Path, templated: bool) -> bool:
    if templated:
        return target.read_text(encoding="utf-8", errors="replace") == source.read_text(encoding="utf-8").replace(ASSET_TEMPLATE_TOKEN, CONFIG_ROOT.as_posix())
    return source.stat().st_size == target.stat().st_size and source.read_bytes() == target.read_bytes()


def _compare(offered: dict[str, Path], target: Path, group_of: dict[str, str], extras: list[str], templated_name: str) -> list[AssetGroup]:
    groups: dict[str, AssetGroup] = {}
    for relative in [*offered, *extras]:
        groups.setdefault(group_of[relative], {
            "name": group_of[relative], "offered": 0, "same": 0, "changed": 0, "missing": 0, "extra": 0, "changed_names": [], "missing_names": [], "extra_names": [],
        })
    for relative, source in offered.items():
        group = groups[group_of[relative]]
        group["offered"] += 1
        copy = target / relative
        if not copy.is_file():
            group["missing"] += 1
            group["missing_names"].append(relative)
        elif _matches(source=source, target=copy, templated=relative == templated_name):
            group["same"] += 1
        else:
            group["changed"] += 1
            group["changed_names"].append(relative)
    for relative in extras:
        groups[group_of[relative]]["extra"] += 1
        groups[group_of[relative]]["extra_names"].append(relative)
    for group in groups.values():
        for key in ("changed_names", "missing_names", "extra_names"):
            group[key] = sorted(group[key])[:ASSET_NAMES_SENT]
    return sorted(groups.values(), key=lambda group: group["name"].casefold())


# What `devops config copy-assets scripts` copies: this system's scripts and the Nushell wrapper, into one folder.
def _scripts_set(system: str) -> AssetSet:
    target = CONFIG_ROOT / "scripts"
    offered = {**_files_under(LIBRARY_ROOT / "scripts" / system), "nu/wrap_stackops.nu": LIBRARY_ROOT / "scripts" / "nu" / "wrap_stackops.nu"}
    groups = _compare(offered=offered, target=target, group_of=dict.fromkeys(offered, "scripts"), extras=[], templated_name="")
    return {"id": "scripts", "target": str(target), "on_machine": target.is_dir(), "replaces": False, "groups": groups}


# What `devops config copy-assets settings` copies: the whole settings folder, in place of the one on this machine. A file at its top level
# has no folder of its own and is listed under an empty name.
def _settings_set() -> AssetSet:
    target = CONFIG_ROOT / "settings"
    offered = _files_under(LIBRARY_ROOT / "settings")
    extras = [relative for relative in _files_under(target) if relative not in offered] if target.is_dir() else []
    group_of = {relative: relative.partition("/")[0] if "/" in relative else "" for relative in [*offered, *extras]}
    groups = _compare(offered=offered, target=target, group_of=group_of, extras=extras, templated_name=ASSET_TEMPLATED_FILE)
    return {"id": "settings", "target": str(target), "on_machine": target.is_dir(), "replaces": True, "groups": groups}


def _old_profile_lines(system_name: str) -> list[str]:
    if system_name == "Windows":
        return []
    profiles: list[str] = []
    for shell in ("/bin/bash", "/bin/zsh"):
        profile = build_shell_profile_source(system_name=system_name, shell_variable=shell, config_root=CONFIG_ROOT).profile_path
        if profile.is_file() and any(line.strip() in STALE_HOOKS for line in profile.read_text(encoding="utf-8", errors="replace").splitlines()):
            profiles.append(str(profile))
    return profiles


# Reads every packaged file and its copy here, which is a few hundred small files: tens of milliseconds.
def read_assets_state() -> AssetsState:
    system_name = platform.system()
    if system_name not in {"Linux", "Darwin", "Windows"}:
        return {"supported": False, "sets": [], "old_profile_lines": []}
    return {
        "supported": True,
        "sets": [_scripts_set(system="windows" if system_name == "Windows" else "linux"), _settings_set()],
        "old_profile_lines": _old_profile_lines(system_name=system_name),
    }
