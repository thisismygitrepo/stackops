import hashlib
from pathlib import Path
import re

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BROWSER_PROFILES_ROOT, BrowserName


def browser_profile_label(*, browser: BrowserName, profile_path: Path | None, port: int) -> str:
    if profile_path is None:
        return "no-profile"
    named_profile_root = BROWSER_PROFILES_ROOT.expanduser().joinpath(browser)
    if profile_path.is_relative_to(named_profile_root):
        return f"profile-{profile_path.relative_to(named_profile_root)}"
    return f"temp-port-{port}"


def browser_launch_id(*, browser: BrowserName, profile_path: Path | None, port: int) -> str:
    profile = browser_profile_label(browser=browser, profile_path=profile_path, port=port)
    browser_slug = re.sub("[^a-z0-9]+", "-", browser.strip().lower()).strip("-")
    profile_slug = re.sub("[^a-z0-9]+", "-", profile.strip().lower()).strip("-")
    if browser_slug == "" or profile_slug == "":
        raise ValueError("browser launch identity segments must not be empty")
    if profile_path is None:
        return f"{browser_slug}-{profile_slug}-p{port}"
    profile_digest = hashlib.sha256(str(profile_path).encode("utf-8")).hexdigest()[:16]
    return f"{browser_slug}-{profile_slug}-{profile_digest}-p{port}"
