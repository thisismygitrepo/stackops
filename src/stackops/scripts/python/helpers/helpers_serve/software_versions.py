import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from time import time
from typing import Literal, TypeAlias
from urllib.parse import unquote

import requests

from stackops.scripts.python.helpers.helpers_serve.constants import (
    GITHUB_RELEASE_CACHE_SECONDS,
    GITHUB_RELEASE_TIMEOUT_SECONDS,
    VERSION_PROBE_TIMEOUT_SECONDS,
)
from stackops.utils.schemas.installer.installer_types import InstallerData

VERSION_STANDING: TypeAlias = Literal["outdated", "current", "ahead", "unknown"]
ANSI_PATTERN = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
DOTTED_NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)+")
NUMBER_PATTERN = re.compile(r"\d+")
PUBLISHED_AT_PATTERN = re.compile(r'<relative-time[^>]*datetime="([^"]+)"')
RELEASE_TAG_MARKER = "/releases/tag/"


@dataclass(frozen=True, slots=True)
class LatestRelease:
    tag: str
    published_at: str
    url: str
    fetched_at: float


@dataclass(frozen=True, slots=True)
class SoftwareVersion:
    name: str
    repository: str
    installed_version: str
    latest_version: str
    released_at: str
    release_url: str
    standing: VERSION_STANDING


@dataclass(frozen=True, slots=True)
class VersionProblem:
    message: str
    status: int


# The repository an app is downloaded from on this machine, or None when it is installed another way (a package manager, a script, a direct link).
def github_release_repository(installer: InstallerData) -> str | None:
    from stackops.utils.installer_utils.github_release_bulk import get_repo_name_from_url, is_github_repo
    from stackops.utils.installer_utils.install_request_logic import build_install_target, resolve_installer_pattern
    from stackops.utils.schemas.installer.installer_types import get_normalized_arch, get_os_name

    repo_url = installer["repoURL"]
    pattern = resolve_installer_pattern(installer_data=installer, operating_system=get_os_name(), architecture=get_normalized_arch())
    if pattern is None or not is_github_repo(repo_url) or build_install_target(repo_url=repo_url, installer_value=pattern).installer_kind != "github_release":
        return None
    owner_and_name = get_repo_name_from_url(repo_url)
    return None if owner_and_name is None else "/".join(owner_and_name)


# What the app itself reports, and failing that the release the installer recorded. A version is the first dotted number, or a lone word such as "r41".
def read_installed_version(exe_name: str) -> str:
    from stackops.utils.source_of_truth import INSTALL_VERSION_ROOT

    try:
        answer = subprocess.run(
            [exe_name, "--version"],
            capture_output=True,
            text=True,
            errors="replace",
            check=False,
            stdin=subprocess.DEVNULL,
            timeout=VERSION_PROBE_TIMEOUT_SECONDS,
        )
        reported = ANSI_PATTERN.sub("", answer.stdout).strip() if answer.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        reported = ""
    record_path = INSTALL_VERSION_ROOT.joinpath(exe_name)
    for text in (reported, record_path.read_text(encoding="utf-8").strip() if record_path.is_file() else ""):
        dotted = DOTTED_NUMBER_PATTERN.search(text)
        if dotted is not None:
            return dotted.group()
        if len(text.split()) == 1 and NUMBER_PATTERN.search(text) is not None:
            return text
    return ""


# GitHub's public "latest release" page: its address carries the tag and the page the publish time. No login, and no API quota to run out of.
def fetch_latest_release(repository: str) -> LatestRelease | VersionProblem:
    try:
        response = requests.get(f"""https://github.com/{repository}/releases/latest""", timeout=GITHUB_RELEASE_TIMEOUT_SECONDS)
    except requests.RequestException as error:
        return VersionProblem(message=f"""GitHub could not be reached for {repository}: {error}""", status=502)
    if response.status_code != 200:
        return VersionProblem(message=f"""GitHub answered {response.status_code} for {repository}.""", status=502)
    _, marker, tag = response.url.partition(RELEASE_TAG_MARKER)
    if marker == "":
        return LatestRelease(tag="", published_at="", url=f"""https://github.com/{repository}/releases""", fetched_at=time())
    published = PUBLISHED_AT_PATTERN.search(response.text)
    return LatestRelease(tag=unquote(tag), published_at="" if published is None else published.group(1), url=response.url, fetched_at=time())


def compare_versions(installed: str, tag: str) -> VERSION_STANDING:
    installed_dotted = DOTTED_NUMBER_PATTERN.search(installed)
    tag_dotted = DOTTED_NUMBER_PATTERN.search(tag)
    if installed_dotted is not None and tag_dotted is not None:
        mine, theirs = installed_dotted.group(), tag_dotted.group()
    elif installed != "" and NUMBER_PATTERN.sub("#", installed.casefold()) == NUMBER_PATTERN.sub("#", tag.casefold()):
        mine, theirs = installed, tag
    else:
        return "unknown"
    my_numbers = [int(number) for number in NUMBER_PATTERN.findall(mine)]
    their_numbers = [int(number) for number in NUMBER_PATTERN.findall(theirs)]
    width = max(len(my_numbers), len(their_numbers))
    my_numbers += [0] * (width - len(my_numbers))
    their_numbers += [0] * (width - len(their_numbers))
    if my_numbers == their_numbers:
        return "current"
    return "outdated" if my_numbers < their_numbers else "ahead"


def check_software_version(
    name: str, fresh: bool, release_cache: dict[str, LatestRelease], installers_by_name: dict[str, InstallerData]
) -> SoftwareVersion | VersionProblem:
    from stackops.utils.installer_utils.installer_catalog import InstallerDataFileError
    from stackops.utils.installer_utils.installer_class import Installer
    from stackops.utils.installer_utils.installer_runner import get_installers_from_source
    from stackops.utils.schemas.installer.installer_types import get_normalized_arch, get_os_name

    # The catalog route fills `installers_by_name`, and a page reads the catalog before it checks versions. Reading it here on every check made a sweep
    # several times slower. It is empty only when a page that outlived a server restart checks first.
    if len(installers_by_name) == 0:
        try:
            installers = get_installers_from_source(source="all", user_path=None, os=get_os_name(), arch=get_normalized_arch(), which_cats=None)
        except InstallerDataFileError as error:
            return VersionProblem(message=str(error), status=422)
        installers_by_name.update({candidate["appName"]: candidate for candidate in installers})
    installer = installers_by_name.get(name)
    if installer is None:
        return VersionProblem(message=f"""{name} is not in the app catalog.""", status=404)
    repository = github_release_repository(installer=installer)
    exe_name = Installer(installer).get_exe_name()
    # An app installed another way has no release to compare with, so only the version on this machine is read.
    if repository is None:
        return SoftwareVersion(
            name=name,
            repository="",
            installed_version=read_installed_version(exe_name=exe_name),
            latest_version="",
            released_at="",
            release_url="",
            standing="unknown",
        )
    release = release_cache.get(repository)
    with ThreadPoolExecutor(max_workers=1) as pool:
        installed = pool.submit(read_installed_version, exe_name=exe_name)
        if release is None or fresh or time() - release.fetched_at > GITHUB_RELEASE_CACHE_SECONDS:
            fetched = fetch_latest_release(repository=repository)
            match fetched:
                case VersionProblem():
                    return fetched
                case LatestRelease():
                    release = fetched
                    release_cache[repository] = fetched
        installed_version = installed.result()
    return SoftwareVersion(
        name=name,
        repository=repository,
        installed_version=installed_version,
        latest_version=release.tag,
        released_at=release.published_at,
        release_url=release.url,
        standing=compare_versions(installed=installed_version, tag=release.tag),
    )
