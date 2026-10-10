import sys

from rich.console import Console
from rich.prompt import IntPrompt
from rich.table import Table
from rich.text import Text

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import ProfileBrowserName
from stackops.scripts.python.helpers.helpers_agents.agents_browser_native_profiles import NativeBrowserProfile, list_native_browser_profiles


def select_native_browser_profile(*, browser: ProfileBrowserName, profile_name: str | None) -> NativeBrowserProfile:
    profiles = list_native_browser_profiles(browser=browser)
    if profile_name is not None:
        folder_matches = tuple(profile for profile in profiles if profile.profile_path.name == profile_name)
        matches = folder_matches or tuple(profile for profile in profiles if profile.name == profile_name)
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            folders = ", ".join(profile.profile_path.name for profile in matches)
            raise ValueError(f"""Native profile name {profile_name!r} is ambiguous. Use a folder name with --profile: {folders}""")
        available_profiles = ", ".join(f"""{profile.name} ({profile.profile_path.name})""" for profile in profiles)
        raise ValueError(f"""Native {browser} profile {profile_name!r} was not found. Available profiles: {available_profiles}""")

    table = Table(title=f"""Native {browser} profiles""", header_style="bold cyan")
    table.add_column("#", justify="right")
    table.add_column("Profile name")
    table.add_column("Folder")
    table.add_column("Path", overflow="fold")
    for index, profile in enumerate(profiles, start=1):
        table.add_row(str(index), Text(profile.name), Text(profile.profile_path.name), Text(str(profile.profile_path)))
    Console().print(table)
    if not sys.stdin.isatty():
        raise ValueError("Use --native --profile <folder-or-name> when input is not interactive.")
    selected_index = IntPrompt.ask("Profile number", choices=[str(index) for index in range(1, len(profiles) + 1)])
    return profiles[selected_index - 1]
