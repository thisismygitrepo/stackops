from typing import Final

PACKAGE_NAME: Final[str] = "stackops"
# The package index says which release is the newest and when each one came out. No login, no quota.
PACKAGE_INDEX_URL: Final[str] = "https://pypi.org/pypi/stackops/json"
PACKAGE_INDEX_PAGE: Final[str] = "https://pypi.org/project/stackops"
# GitHub's public pages for a branch: its newest commits as a feed, and the version its pyproject.toml declares. Both answer without a login and
# neither counts against the API's sixty requests an hour.
GITHUB_FEED_URL: Final[str] = "https://github.com/{repository}/commits/{branch}.atom"
GITHUB_PROJECT_URL: Final[str] = "https://raw.githubusercontent.com/{repository}/refs/heads/{branch}/pyproject.toml"
GITHUB_HISTORY_PAGE: Final[str] = "https://github.com/{repository}/commits/{branch}"
ATOM_NAMESPACE: Final[str] = "{http://www.w3.org/2005/Atom}"

# A lookup that takes longer than this is treated as "no network right now", which the page shows as a calm state.
LATEST_TIMEOUT_SECONDS: Final[float] = 8.0
# How long an answer from the network is kept, so coming back to the page, or the refresh after a run, does not ask again.
LATEST_CACHE_SECONDS: Final[float] = 600.0
GIT_TIMEOUT_SECONDS: Final[float] = 10.0
UV_TIMEOUT_SECONDS: Final[float] = 5.0

# How far back the checkout's own history is read to tell which of the newest commits online it already has.
LOCAL_HISTORY_DEPTH: Final[int] = 400
# How many changed files the page names before it says "and N more".
CHANGED_NAMES_SHOWN: Final[int] = 8
# How many releases newer than the installed one the page lists, newest first.
RELEASES_SHOWN: Final[int] = 12
