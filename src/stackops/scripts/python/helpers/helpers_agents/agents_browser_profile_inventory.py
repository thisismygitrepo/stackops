from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import (
    BROWSER_PROFILES_ROOT,
    CHROMIUM_NON_USER_PROFILE_FOLDERS,
    ChromiumBrowserName,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_native_profiles import list_native_browser_profiles
from stackops.scripts.python.helpers.helpers_agents.agents_browser_process_scan import OpenBrowserProcess, collect_open_browsers
from stackops.scripts.python.helpers.helpers_agents.agents_browser_profile_listing import natural_profile_name_key
from stackops.scripts.python.helpers.helpers_agents.agents_browser_profile_sign_in import (
    BrowserProfileSiteSignIn,
    LockedProfileDatabase,
    list_signed_in_known_services,
    read_chromium_google_accounts,
    read_chromium_live_cookies,
    read_chromium_saved_logins,
    read_json_object,
    resolve_site_sign_in,
)


@dataclass(frozen=True, slots=True)
class BrowserProfileInventoryRow:
    profile: str
    running: bool
    debugging_port: int | None
    browser_account: str | None
    signed_in_services: tuple[str, ...] | LockedProfileDatabase
    last_used: datetime | None
    sites: tuple[BrowserProfileSiteSignIn, ...]
    browser: ChromiumBrowserName
    profile_folder: str | None
    user_data_path: Path


def collect_browser_profile_inventory(
    *, browser: ChromiumBrowserName, native: bool, sites: tuple[str, ...], now: datetime
) -> tuple[BrowserProfileInventoryRow, ...]:
    targets: list[tuple[str, Path, str | None]] = []
    if native:
        targets.extend(
            (f"""{profile.name} ({profile.profile_path.name})""", profile.user_data_path, profile.profile_path.name)
            for profile in list_native_browser_profiles(browser=browser)
        )
    else:
        profiles_root = BROWSER_PROFILES_ROOT.expanduser().joinpath(browser)
        try:
            user_data_paths = (
                sorted((child for child in profiles_root.iterdir() if child.is_dir()), key=lambda child: natural_profile_name_key(name=child.name))
                if profiles_root.is_dir()
                else []
            )
            for user_data_path in user_data_paths:
                folders = sorted(
                    child.name
                    for child in user_data_path.iterdir()
                    if child.name not in CHROMIUM_NON_USER_PROFILE_FOLDERS and child.joinpath("Preferences").is_file()
                )
                if len(folders) == 0:
                    targets.append((user_data_path.name, user_data_path, None))
                targets.extend(
                    (user_data_path.name if folder == "Default" else f"""{user_data_path.name}/{folder}""", user_data_path, folder)
                    for folder in folders
                )
        except OSError as error:
            raise RuntimeError(f"""Could not inspect browser profiles under {profiles_root}: {error}""") from error
    open_browsers = tuple(open_browser for open_browser in collect_open_browsers() if open_browser.browser == browser)
    info_cache_by_user_data_path: dict[Path, dict[str, object]] = {}
    rows: list[BrowserProfileInventoryRow] = []
    for profile, user_data_path, profile_folder in targets:
        if user_data_path not in info_cache_by_user_data_path:
            info_cache_by_user_data_path[user_data_path] = _read_profile_info_cache(user_data_path=user_data_path)
        rows.append(
            _build_inventory_row(
                browser=browser,
                profile=profile,
                user_data_path=user_data_path,
                profile_folder=profile_folder,
                native=native,
                open_browsers=open_browsers,
                info_cache=info_cache_by_user_data_path[user_data_path],
                sites=sites,
                now=now,
            )
        )
    return tuple(rows)


def _build_inventory_row(
    *,
    browser: ChromiumBrowserName,
    profile: str,
    user_data_path: Path,
    profile_folder: str | None,
    native: bool,
    open_browsers: tuple[OpenBrowserProcess, ...],
    info_cache: dict[str, object],
    sites: tuple[str, ...],
    now: datetime,
) -> BrowserProfileInventoryRow:
    resolved_user_data_path = user_data_path.resolve()
    open_browser = next(
        (
            candidate
            for candidate in open_browsers
            if (native if candidate.profile_path is None else candidate.profile_path.expanduser().resolve() == resolved_user_data_path)
        ),
        None,
    )
    raw_details = None if profile_folder is None else info_cache.get(profile_folder)
    details = cast(dict[str, object], raw_details) if isinstance(raw_details, dict) else {}
    user_name = details.get("user_name")
    active_time = details.get("active_time")
    signed_in_services: tuple[str, ...] | LockedProfileDatabase = ()
    site_sign_ins: tuple[BrowserProfileSiteSignIn, ...] = ()
    if profile_folder is not None:
        profile_folder_path = user_data_path.joinpath(profile_folder)
        cookies = read_chromium_live_cookies(profile_folder_path=profile_folder_path, now=now)
        signed_in_services = cookies if isinstance(cookies, LockedProfileDatabase) else list_signed_in_known_services(cookies=cookies)
        if len(sites) > 0:
            preferences_path = profile_folder_path.joinpath("Preferences")
            google_accounts = read_chromium_google_accounts(preferences=read_json_object(path=preferences_path)) if preferences_path.is_file() else ()
            saved_logins = read_chromium_saved_logins(profile_folder_path=profile_folder_path)
            site_sign_ins = tuple(
                resolve_site_sign_in(site=site, cookies=cookies, saved_logins=saved_logins, google_accounts=google_accounts) for site in sites
            )
    return BrowserProfileInventoryRow(
        profile=profile,
        running=open_browser is not None,
        debugging_port=None if open_browser is None else open_browser.debugging_port,
        browser_account=user_name if isinstance(user_name, str) and user_name != "" else None,
        signed_in_services=signed_in_services,
        last_used=datetime.fromtimestamp(active_time, tz=UTC) if isinstance(active_time, (int, float)) and active_time > 0 else None,
        sites=site_sign_ins,
        browser=browser,
        profile_folder=profile_folder,
        user_data_path=user_data_path,
    )


def _read_profile_info_cache(*, user_data_path: Path) -> dict[str, object]:
    local_state_path = user_data_path.joinpath("Local State")
    if not local_state_path.is_file():
        return {}
    raw_profile = read_json_object(path=local_state_path).get("profile")
    raw_cache = cast(dict[str, object], raw_profile).get("info_cache") if isinstance(raw_profile, dict) else None
    return cast(dict[str, object], raw_cache) if isinstance(raw_cache, dict) else {}
