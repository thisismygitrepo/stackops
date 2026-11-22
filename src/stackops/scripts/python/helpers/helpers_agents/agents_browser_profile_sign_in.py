from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3
from typing import cast
from urllib.parse import urlsplit

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import (
    CHROMIUM_COOKIE_DATABASE_PATHS,
    CHROMIUM_EPOCH_OFFSET_SECONDS,
    KNOWN_SERVICE_SIGN_IN_COOKIE_NAMES,
    BrowserSignInState,
)


@dataclass(frozen=True, slots=True)
class ChromiumLiveCookie:
    host: str
    name: str
    is_httponly: bool
    last_access: datetime | None


@dataclass(frozen=True, slots=True)
class ChromiumSavedLogin:
    host: str
    username: str


@dataclass(frozen=True, slots=True)
class BrowserProfileSiteSignIn:
    site: str
    state: BrowserSignInState
    accounts: tuple[str, ...]
    saved_usernames: tuple[str, ...]
    hosts: tuple[str, ...]
    cookie_names: tuple[str, ...]
    last_active: datetime | None


def read_json_object(*, path: Path) -> dict[str, object]:
    try:
        raw: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise RuntimeError(f"""Could not read browser profile metadata at {path}: {error}""") from error
    if not isinstance(raw, dict):
        raise RuntimeError(f"""Expected a JSON object in browser profile metadata: {path}""")
    return cast(dict[str, object], raw)


def read_chromium_live_cookies(*, profile_folder_path: Path, now: datetime) -> tuple[ChromiumLiveCookie, ...]:
    database_path = next(
        (
            candidate
            for candidate in (profile_folder_path.joinpath(*relative_path) for relative_path in CHROMIUM_COOKIE_DATABASE_PATHS)
            if candidate.is_file()
        ),
        None,
    )
    if database_path is None:
        return ()
    now_chromium = int((now.timestamp() + CHROMIUM_EPOCH_OFFSET_SECONDS) * 1_000_000)
    rows = cast(
        tuple[tuple[str, str, int, int], ...],
        _query_profile_database(
            database_path=database_path,
            query="select host_key, name, is_httponly, last_access_utc from cookies where has_expires = 0 or expires_utc > ?",
            parameters=(now_chromium,),
        ),
    )
    return tuple(
        ChromiumLiveCookie(
            host=host.casefold(),
            name=name,
            is_httponly=is_httponly == 1,
            last_access=None if last_access == 0 else datetime.fromtimestamp(last_access / 1_000_000 - CHROMIUM_EPOCH_OFFSET_SECONDS, tz=UTC),
        )
        for host, name, is_httponly, last_access in rows
    )


def read_chromium_saved_logins(*, profile_folder_path: Path) -> tuple[ChromiumSavedLogin, ...]:
    database_path = profile_folder_path.joinpath("Login Data")
    if not database_path.is_file():
        return ()
    rows = cast(
        tuple[tuple[str, str], ...],
        _query_profile_database(
            database_path=database_path,
            query="select signon_realm, username_value from logins where blacklisted_by_user = 0 and username_value != '' order by date_last_used desc",
            parameters=(),
        ),
    )
    saved_logins: list[ChromiumSavedLogin] = []
    for signon_realm, username in rows:
        host = urlsplit(signon_realm).hostname
        if host is not None:
            saved_logins.append(ChromiumSavedLogin(host=host.casefold(), username=username))
    return tuple(saved_logins)


def read_chromium_google_accounts(*, preferences: dict[str, object]) -> tuple[str, ...]:
    raw_accounts = preferences.get("account_info")
    if not isinstance(raw_accounts, list):
        return ()
    emails: list[str] = []
    for raw_account in cast(list[object], raw_accounts):
        if isinstance(raw_account, dict):
            email = cast(dict[str, object], raw_account).get("email")
            if isinstance(email, str) and email != "":
                emails.append(email)
    return tuple(emails)


def list_signed_in_known_services(*, cookies: tuple[ChromiumLiveCookie, ...]) -> tuple[str, ...]:
    return tuple(
        service
        for service, cookie_names in KNOWN_SERVICE_SIGN_IN_COOKIE_NAMES.items()
        if any(service in cookie.host and cookie.name in cookie_names for cookie in cookies)
    )


def resolve_site_sign_in(
    *, site: str, cookies: tuple[ChromiumLiveCookie, ...], saved_logins: tuple[ChromiumSavedLogin, ...], google_accounts: tuple[str, ...]
) -> BrowserProfileSiteSignIn:
    term = site.casefold()
    site_cookies = tuple(cookie for cookie in cookies if term in cookie.host)
    known_cookie_names = next((names for service, names in KNOWN_SERVICE_SIGN_IN_COOKIE_NAMES.items() if service in term), None)
    state: BrowserSignInState
    if known_cookie_names is None:
        evidence = tuple(cookie for cookie in site_cookies if cookie.is_httponly)
        state = "likely" if len(evidence) > 0 else "none"
    else:
        evidence = tuple(cookie for cookie in site_cookies if cookie.name in known_cookie_names)
        state = "signed-in" if len(evidence) > 0 else "none"
    last_access_times = tuple(cookie.last_access for cookie in evidence if cookie.last_access is not None)
    return BrowserProfileSiteSignIn(
        site=site,
        state=state,
        accounts=google_accounts if "google" in term else (),
        saved_usernames=tuple(dict.fromkeys(login.username for login in saved_logins if term in login.host)),
        hosts=tuple(sorted({cookie.host for cookie in evidence})),
        cookie_names=tuple(sorted({cookie.name for cookie in evidence})),
        last_active=max(last_access_times) if len(last_access_times) > 0 else None,
    )


def _query_profile_database(*, database_path: Path, query: str, parameters: tuple[int, ...]) -> tuple[tuple[object, ...], ...]:
    try:
        connection = sqlite3.connect(f"""{database_path.as_uri()}?mode=ro&immutable=1""", uri=True)
        try:
            return tuple(cast(list[tuple[object, ...]], connection.execute(query, parameters).fetchall()))
        finally:
            connection.close()
    except sqlite3.Error as error:
        raise RuntimeError(f"""Could not read browser profile database {database_path}: {error}""") from error
