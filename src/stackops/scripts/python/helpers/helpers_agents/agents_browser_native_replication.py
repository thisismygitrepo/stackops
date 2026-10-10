import json
from typing import cast

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import ProfileBrowserName, TEMPORARY_BROWSER_PROFILE_DIRECTORY_NAME
from stackops.scripts.python.helpers.helpers_agents.agents_browser_detached_processes import find_browser_process_ids
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_lock import browser_launch_lock
from stackops.scripts.python.helpers.helpers_agents.agents_browser_native_profiles import NativeBrowserProfile
from stackops.scripts.python.helpers.helpers_agents.agents_browser_profiles import BrowserProfileReplicationResult, copy_browser_profile_to_replicas


def replicate_native_browser_profile(
    *, browser: ProfileBrowserName, profile: NativeBrowserProfile, target_names: tuple[str, ...], overwrite: bool
) -> BrowserProfileReplicationResult:
    with browser_launch_lock():
        if not profile.profile_path.is_dir():
            raise ValueError(f"""Native browser profile does not exist: {profile.profile_path}""")
        if profile.profile_path.is_symlink() or profile.profile_path.is_junction():
            raise ValueError(f"""Native browser profile must not be a symbolic link or junction: {profile.profile_path}""")
        process_ids = find_browser_process_ids(browser=browser)
        if process_ids:
            process_list = ", ".join(str(process_id) for process_id in process_ids)
            raise RuntimeError(f"""Quit {browser} before copying a native profile. Running process ID(s): {process_list}""")
        local_state = None if browser == "firefox" else _prepare_chromium_local_state(profile=profile)
        return copy_browser_profile_to_replicas(
            browser=browser,
            source_path=profile.profile_path,
            target_names=target_names,
            overwrite=overwrite,
            chromium_local_state=local_state,
            excluded_root_directory_names=frozenset({
                TEMPORARY_BROWSER_PROFILE_DIRECTORY_NAME,
                "SingletonCookie",
                "SingletonLock",
                "SingletonSocket",
                "DevToolsActivePort",
                "lock",
                "parent.lock",
                ".parentlock",
            }),
        )


def _prepare_chromium_local_state(*, profile: NativeBrowserProfile) -> bytes:
    metadata_path = profile.user_data_path.joinpath("Local State")
    try:
        raw_metadata: object = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise RuntimeError(f"""Could not read native browser metadata at {metadata_path}: {error}""") from error
    if not isinstance(raw_metadata, dict):
        raise ValueError(f"""Expected an object in native browser metadata: {metadata_path}""")
    metadata = cast(dict[str, object], raw_metadata)
    raw_profile_metadata = metadata.get("profile")
    if not isinstance(raw_profile_metadata, dict):
        raise ValueError(f"""Missing profile metadata in: {metadata_path}""")
    profile_metadata = cast(dict[str, object], raw_profile_metadata)
    raw_info_cache = profile_metadata.get("info_cache")
    if not isinstance(raw_info_cache, dict):
        raise ValueError(f"""Missing profile.info_cache in: {metadata_path}""")
    info_cache = cast(dict[str, object], raw_info_cache)
    folder_name = profile.profile_path.name
    if folder_name not in info_cache:
        raise ValueError(f"""Native profile {folder_name!r} is no longer registered in: {metadata_path}""")
    profile_metadata.update({
        "info_cache": {folder_name: info_cache[folder_name]},
        "last_used": folder_name,
        "last_active_profiles": [folder_name],
        "profiles_order": [folder_name],
        "show_picker_on_startup": False,
    })
    raw_profiles_metadata = metadata.get("profiles")
    if isinstance(raw_profiles_metadata, dict):
        cast(dict[str, object], raw_profiles_metadata).pop("profile_basenames_deleted", None)
    return json.dumps(metadata).encode("utf-8")
