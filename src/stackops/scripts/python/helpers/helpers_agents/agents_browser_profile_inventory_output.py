from datetime import datetime

from rich import box
from rich.table import Table
from rich.text import Text

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import ChromiumBrowserName
from stackops.scripts.python.helpers.helpers_agents.agents_browser_profile_inventory import BrowserProfileInventoryRow
from stackops.scripts.python.helpers.helpers_agents.agents_browser_profile_sign_in import BrowserProfileSiteSignIn, LockedProfileDatabase


def build_browser_profile_inventory_table(
    *, browser: ChromiumBrowserName, native: bool, sites: tuple[str, ...], rows: tuple[BrowserProfileInventoryRow, ...], now: datetime
) -> Table:
    running_count = sum(1 for row in rows if row.running)
    caption = (
        "Pass sites for accounts and session details, e.g. `stackops agents browser profiles google slack`."
        if len(sites) == 0
        else "signed in: an unexpired sign-in cookie of a known service · likely: unexpired HttpOnly cookies on a matching host. "
        "The site may still have ended the session. Account names come from the browser's Google sign-in and from saved logins."
    )
    locked_databases = tuple(
        dict.fromkeys(
            locked.path
            for row in rows
            for locked in (row.signed_in_services, *(sign_in.saved_usernames for sign_in in row.sites))
            if isinstance(locked, LockedProfileDatabase)
        )
    )
    if len(locked_databases) > 0:
        caption = f"""{caption}
locked: the browser holds the profile database open (Chrome does on Windows while running); close it and run again. Locked: {_shorten(values=tuple(str(path) for path in locked_databases))}"""
    table = Table(
        title=f"""{"Native" if native else "StackOps"} {browser} profiles: {len(rows)} found, {running_count} running""",
        caption=caption,
        box=box.ROUNDED,
        header_style="bold cyan",
        show_lines=len(sites) > 0,
    )
    table.add_column("Profile", style="bold white", overflow="fold")
    table.add_column("State")
    table.add_column("Browser account", overflow="fold")
    table.add_column("Signed in to")
    table.add_column("Last used")
    for site in sites:
        table.add_column(site, overflow="fold")
    for row in rows:
        state = Text("closed", style="dim")
        if row.running:
            running_label = "browser running" if native else "running"
            state = Text(running_label if row.debugging_port is None else f"""{running_label} · :{row.debugging_port}""", style="bold green")
        table.add_row(
            Text(row.profile),
            state,
            Text("-", style="dim") if row.browser_account is None else Text(row.browser_account),
            _signed_in_services_cell(signed_in_services=row.signed_in_services),
            Text("-", style="dim") if row.last_used is None else Text(_format_age(moment=row.last_used, now=now)),
            *(_site_cell(sign_in=sign_in, now=now) for sign_in in row.sites),
        )
    return table


def _site_cell(*, sign_in: BrowserProfileSiteSignIn, now: datetime) -> Text:
    match sign_in.state:
        case "signed-in":
            cell = Text("signed in", style="bold green")
        case "likely":
            cell = Text("likely", style="bold yellow")
        case "none":
            cell = Text("no", style="dim")
        case "unknown":
            cell = Text("unknown · cookies locked", style="bold yellow")
    if sign_in.last_active is not None:
        cell.append(f""" · {_format_age(moment=sign_in.last_active, now=now)}""", style="dim")
    for account in sign_in.accounts:
        cell.append(f"""\n{account}""", style="white")
    match sign_in.saved_usernames:
        case LockedProfileDatabase():
            cell.append("""\nsaved: unknown · logins locked""", style="yellow")
        case ():
            pass
        case saved_usernames:
            cell.append(f"""\nsaved: {_shorten(values=saved_usernames)}""", style="white")
    if len(sign_in.hosts) > 0:
        cell.append(f"""\nhosts: {_shorten(values=sign_in.hosts)}""", style="dim")
        cell.append(f"""\ncookies: {_shorten(values=sign_in.cookie_names)}""", style="dim")
    return cell


def _signed_in_services_cell(*, signed_in_services: tuple[str, ...] | LockedProfileDatabase) -> Text:
    match signed_in_services:
        case LockedProfileDatabase():
            return Text("unknown · cookies locked", style="bold yellow")
        case ():
            return Text("-", style="dim")
        case services:
            return Text(" · ".join(services), style="green")


def _shorten(*, values: tuple[str, ...]) -> str:
    shown = ", ".join(values[:3])
    return shown if len(values) <= 3 else f"""{shown} +{len(values) - 3}"""


def _format_age(*, moment: datetime, now: datetime) -> str:
    seconds = int((now - moment).total_seconds())
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"""{seconds // 60}m ago"""
    if seconds < 86400:
        return f"""{seconds // 3600}h ago"""
    return f"""{seconds // 86400}d ago"""
