from configparser import ConfigParser, Error as ConfigParserError
from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
from typing import cast

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import ProfileBrowserName
from stackops.scripts.python.helpers.helpers_agents.agents_browser_profile_listing import natural_profile_name_key


@dataclass(frozen=True, slots=True)
class NativeBrowserProfile:
    name: str
    profile_path: Path
    user_data_path: Path


def resolve_native_browser_data_path(*, browser: ProfileBrowserName) -> Path:
    home_path = Path.home()
    relative_paths: dict[ProfileBrowserName, tuple[str, ...]]
    match sys.platform:
        case "darwin":
            data_root = home_path.joinpath("Library", "Application Support")
            relative_paths = {
                "chrome": ("Google", "Chrome"),
                "brave": ("BraveSoftware", "Brave-Browser"),
                "edge": ("Microsoft Edge",),
                "firefox": ("Firefox",),
            }
        case "win32":
            if browser == "firefox":
                return Path(os.environ["APPDATA"]).joinpath("Mozilla", "Firefox")
            data_root = Path(os.environ["LOCALAPPDATA"])
            relative_paths = {
                "chrome": ("Google", "Chrome", "User Data"),
                "brave": ("BraveSoftware", "Brave-Browser", "User Data"),
                "edge": ("Microsoft", "Edge", "User Data"),
                "firefox": ("Mozilla", "Firefox"),
            }
        case "linux":
            if browser == "firefox":
                return home_path.joinpath(".mozilla", "firefox")
            data_root = Path(os.environ.get("XDG_CONFIG_HOME", str(home_path.joinpath(".config"))))
            if browser == "chrome" and os.environ.get("CHROME_CONFIG_HOME"):
                data_root = Path(os.environ["CHROME_CONFIG_HOME"])
            relative_paths = {
                "chrome": ("google-chrome",),
                "brave": ("BraveSoftware", "Brave-Browser"),
                "edge": ("microsoft-edge",),
                "firefox": (".mozilla", "firefox"),
            }
        case _:
            raise ValueError(f"""Native browser profile discovery is not supported on {sys.platform}.""")
    return data_root.joinpath(*relative_paths[browser])


def list_native_browser_profiles(*, browser: ProfileBrowserName) -> tuple[NativeBrowserProfile, ...]:
    user_data_path = resolve_native_browser_data_path(browser=browser)
    if not user_data_path.is_dir():
        raise ValueError(f"""The native {browser} data directory does not exist: {user_data_path}""")
    profiles = (
        _list_firefox_profiles(user_data_path=user_data_path)
        if browser == "firefox"
        else _list_chromium_profiles(user_data_path=user_data_path)
    )
    if not profiles:
        raise ValueError(f"""No native {browser} profiles found in: {user_data_path}""")
    return tuple(sorted(profiles, key=lambda profile: natural_profile_name_key(name=profile.profile_path.name)))


def _list_chromium_profiles(*, user_data_path: Path) -> tuple[NativeBrowserProfile, ...]:
    metadata_path = user_data_path.joinpath("Local State")
    try:
        raw_metadata: object = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise RuntimeError(f"""Could not read native browser profile metadata at {metadata_path}: {error}""") from error
    if not isinstance(raw_metadata, dict):
        raise ValueError(f"""Expected an object in native browser metadata: {metadata_path}""")
    raw_profile = cast(dict[str, object], raw_metadata).get("profile")
    if not isinstance(raw_profile, dict):
        raise ValueError(f"""Missing profile metadata in: {metadata_path}""")
    raw_cache = cast(dict[str, object], raw_profile).get("info_cache")
    if not isinstance(raw_cache, dict):
        raise ValueError(f"""Missing profile.info_cache in: {metadata_path}""")
    profiles: list[NativeBrowserProfile] = []
    for folder_name, raw_details in cast(dict[str, object], raw_cache).items():
        if not folder_name or Path(folder_name).name != folder_name or folder_name in {".", ".."}:
            raise ValueError(f"""Invalid native browser profile folder in {metadata_path}: {folder_name}""")
        if not isinstance(raw_details, dict):
            raise ValueError(f"""Invalid native browser profile metadata for {folder_name}: {metadata_path}""")
        name = cast(dict[str, object], raw_details).get("name")
        if not isinstance(name, str) or not name:
            raise ValueError(f"""Missing native browser profile name for {folder_name}: {metadata_path}""")
        profile_path = user_data_path.joinpath(folder_name)
        if profile_path.is_dir():
            profiles.append(NativeBrowserProfile(name=name, profile_path=profile_path, user_data_path=user_data_path))
    return tuple(profiles)


def _list_firefox_profiles(*, user_data_path: Path) -> tuple[NativeBrowserProfile, ...]:
    metadata_path = user_data_path.joinpath("profiles.ini")
    configuration = ConfigParser(interpolation=None)
    profiles: list[NativeBrowserProfile] = []
    try:
        with metadata_path.open(encoding="utf-8") as metadata_file:
            configuration.read_file(metadata_file)
        for section in configuration.sections():
            if not section.startswith("Profile"):
                continue
            name = configuration.get(section, "Name")
            path_value = configuration.get(section, "Path")
            is_relative = configuration.getboolean(section, "IsRelative")
            profile_path = user_data_path.joinpath(path_value) if is_relative else Path(path_value)
            if not name or not path_value or not profile_path.is_absolute():
                raise ValueError(f"""Invalid native Firefox profile in section {section}: {metadata_path}""")
            if profile_path.is_dir():
                profiles.append(NativeBrowserProfile(name=name, profile_path=profile_path, user_data_path=user_data_path))
    except (OSError, ConfigParserError, ValueError) as error:
        raise RuntimeError(f"""Could not read native Firefox profile metadata at {metadata_path}: {error}""") from error
    return tuple(profiles)
