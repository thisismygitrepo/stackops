import re
import tomllib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from itertools import takewhile
from time import time
from typing import Literal, TypedDict, cast
from xml.etree import ElementTree

import requests

from stackops.scripts.python.helpers.helpers_webui.machine_update_constants import (
    ATOM_NAMESPACE,
    GITHUB_FEED_URL,
    GITHUB_HISTORY_PAGE,
    GITHUB_PROJECT_URL,
    LATEST_CACHE_SECONDS,
    LATEST_TIMEOUT_SECONDS,
    PACKAGE_INDEX_PAGE,
    PACKAGE_INDEX_URL,
    RELEASES_SHOWN,
)
from stackops.scripts.python.helpers.helpers_webui.software_versions import NUMBER_PATTERN, VERSION_STANDING, compare_versions

COMMIT_ID_PATTERN = re.compile(r"[0-9a-f]{40}")

# Why a lookup has no answer: the network did not answer in time, or the site answered with a refusal (a private repository, too many requests).
type LookupTrouble = Literal["", "offline", "refused"]


class ReleaseNote(TypedDict):
    version: str
    released_at: str


class CommitNote(TypedDict):
    sha: str
    title: str
    committed_at: str
    author: str
    url: str


# What the package index last said: its newest release and every release with the time it came out.
@dataclass(frozen=True, slots=True)
class IndexAnswer:
    fetched_at: float
    version: str
    releases: tuple[ReleaseNote, ...]


# What GitHub last said about one branch: its newest commits, newest first, and the version its pyproject.toml declares (empty if unreadable).
@dataclass(frozen=True, slots=True)
class BranchAnswer:
    fetched_at: float
    version: str
    commits: tuple[CommitNote, ...]


@dataclass(frozen=True, slots=True)
class LookupProblem:
    trouble: LookupTrouble


# The newest version there is, next to what is here. `releases` are the ones newer than the installed version and `commits` the ones the checkout
# does not have yet, both newest first; `more` says the list of commits was cut short. Without an answer `trouble` says why and the rest is empty.
class LatestView(TypedDict):
    source: Literal["index", "github", "none"]
    trouble: LookupTrouble
    version: str
    released_at: str
    page: str
    standing: VERSION_STANDING
    releases: list[ReleaseNote]
    commits: list[CommitNote]
    more: bool
    checked_at: float


def fetch(address: str) -> requests.Response | LookupProblem:
    try:
        response = requests.get(address, timeout=LATEST_TIMEOUT_SECONDS)
    except requests.RequestException:
        return LookupProblem(trouble="offline")
    return response if response.status_code == 200 else LookupProblem(trouble="refused")


def fetch_index() -> IndexAnswer | LookupProblem:
    response = fetch(PACKAGE_INDEX_URL)
    match response:
        case LookupProblem():
            return response
        case _:
            document = cast(dict[str, dict[str, object]], response.json())
    files_by_version = cast(dict[str, list[dict[str, object]]], document["releases"])
    releases: list[ReleaseNote] = [
        {"version": version, "released_at": str(files[0]["upload_time_iso_8601"])} for version, files in files_by_version.items() if len(files) > 0 and files[0].get("yanked") is not True
    ]
    releases.sort(key=lambda release: [int(number) for number in NUMBER_PATTERN.findall(release["version"])], reverse=True)
    return IndexAnswer(fetched_at=time(), version=str(document["info"]["version"]), releases=tuple(releases))


def fetch_branch(repository: str, branch: str) -> BranchAnswer | LookupProblem:
    with ThreadPoolExecutor(max_workers=2) as pool:
        feed_call = pool.submit(fetch, GITHUB_FEED_URL.format(repository=repository, branch=branch))
        project_call = pool.submit(fetch, GITHUB_PROJECT_URL.format(repository=repository, branch=branch))
        feed, project = feed_call.result(), project_call.result()
    match feed:
        case LookupProblem():
            return feed
        case _:
            entries = ElementTree.fromstring(feed.content).iter(f"""{ATOM_NAMESPACE}entry""")
    commits: list[CommitNote] = []
    for entry in entries:
        sha = entry.findtext(f"""{ATOM_NAMESPACE}id""", "").rpartition("/")[2]
        # A commit's address is built here from its id, so nothing the feed says is used as a link.
        if COMMIT_ID_PATTERN.fullmatch(sha) is None:
            continue
        commits.append(
            {
                "sha": sha,
                "title": " ".join(entry.findtext(f"""{ATOM_NAMESPACE}title""", "").split()),
                "committed_at": entry.findtext(f"""{ATOM_NAMESPACE}updated""", ""),
                "author": entry.findtext(f"""{ATOM_NAMESPACE}author/{ATOM_NAMESPACE}name""", ""),
                "url": f"""https://github.com/{repository}/commit/{sha}""",
            }
        )
    version = ""
    match project:
        case LookupProblem():
            pass
        case _:
            declared = cast(dict[str, dict[str, object]], tomllib.loads(project.text)).get("project", {}).get("version")
            version = declared if isinstance(declared, str) else ""
    return BranchAnswer(fetched_at=time(), version=version, commits=tuple(commits))


def no_answer(source: Literal["index", "github", "none"], trouble: LookupTrouble, page: str) -> LatestView:
    return {"source": source, "trouble": trouble, "version": "", "released_at": "", "page": page, "standing": "unknown", "releases": [], "commits": [], "more": False, "checked_at": time()}


# The newest release on the package index against the installed version. An answer younger than the cache time is reused unless `fresh`.
def latest_release(installed_version: str, fresh: bool, answers: dict[str, IndexAnswer | BranchAnswer]) -> LatestView:
    known = answers.get("index")
    if not isinstance(known, IndexAnswer) or fresh or time() - known.fetched_at > LATEST_CACHE_SECONDS:
        fetched = fetch_index()
        match fetched:
            case LookupProblem():
                return no_answer(source="index", trouble=fetched.trouble, page=PACKAGE_INDEX_PAGE)
            case IndexAnswer():
                known = fetched
                answers["index"] = fetched
    newer = [release for release in known.releases if compare_versions(installed=installed_version, tag=release["version"]) == "outdated"]
    return {
        "source": "index",
        "trouble": "",
        "version": known.version,
        "released_at": next((release["released_at"] for release in known.releases if release["version"] == known.version), ""),
        "page": f"""{PACKAGE_INDEX_PAGE}/{known.version}/""",
        "standing": compare_versions(installed=installed_version, tag=known.version),
        "releases": newer[:RELEASES_SHOWN],
        "commits": [],
        "more": len(newer) > RELEASES_SHOWN,
        "checked_at": known.fetched_at,
    }


# The newest commits of the branch the checkout follows, against the commits the checkout already has. Nothing is fetched into the checkout:
# GitHub's public pages are read, and `history` is the checkout's own record.
def latest_commits(repository: str, branch: str, history: frozenset[str], fresh: bool, answers: dict[str, IndexAnswer | BranchAnswer]) -> LatestView:
    page = GITHUB_HISTORY_PAGE.format(repository=repository, branch=branch)
    key = f"""{repository}@{branch}"""
    known = answers.get(key)
    if not isinstance(known, BranchAnswer) or fresh or time() - known.fetched_at > LATEST_CACHE_SECONDS:
        fetched = fetch_branch(repository=repository, branch=branch)
        match fetched:
            case LookupProblem():
                return no_answer(source="github", trouble=fetched.trouble, page=page)
            case BranchAnswer():
                known = fetched
                answers[key] = fetched
    unseen = list(takewhile(lambda commit: commit["sha"] not in history, known.commits))
    return {
        "source": "github",
        "trouble": "",
        "version": known.version,
        "released_at": known.commits[0]["committed_at"] if len(known.commits) > 0 else "",
        "page": page,
        "standing": "outdated" if len(unseen) > 0 else "current",
        "releases": [],
        "commits": unseen,
        "more": len(unseen) > 0 and len(unseen) == len(known.commits),
        "checked_at": known.fetched_at,
    }
