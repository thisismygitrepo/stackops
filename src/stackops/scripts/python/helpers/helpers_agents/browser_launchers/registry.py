from typing import assert_never

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BrowserName
from stackops.scripts.python.helpers.helpers_agents.browser_launchers.brave import LAUNCHER as BRAVE_LAUNCHER
from stackops.scripts.python.helpers.helpers_agents.browser_launchers.chrome import LAUNCHER as CHROME_LAUNCHER
from stackops.scripts.python.helpers.helpers_agents.browser_launchers.edge import LAUNCHER as EDGE_LAUNCHER
from stackops.scripts.python.helpers.helpers_agents.browser_launchers.firefox import LAUNCHER as FIREFOX_LAUNCHER
from stackops.scripts.python.helpers.helpers_agents.browser_launchers.models import BrowserLauncher
from stackops.scripts.python.helpers.helpers_agents.browser_launchers.safari import LAUNCHER as SAFARI_LAUNCHER


def get_browser_launcher(*, browser: BrowserName) -> BrowserLauncher:
    match browser:
        case "chrome":
            return CHROME_LAUNCHER
        case "brave":
            return BRAVE_LAUNCHER
        case "edge":
            return EDGE_LAUNCHER
        case "firefox":
            return FIREFOX_LAUNCHER
        case "safari":
            return SAFARI_LAUNCHER
        case _:
            assert_never(browser)
