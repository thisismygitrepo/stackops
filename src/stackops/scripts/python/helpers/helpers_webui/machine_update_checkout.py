import re
import sys
from pathlib import Path
from typing import Literal, TypedDict
from urllib.parse import urlsplit, urlunsplit

from stackops.scripts.python.helpers.helpers_webui.machine_update_constants import CHANGED_NAMES_SHOWN, GIT_TIMEOUT_SECONDS, LOCAL_HISTORY_DEPTH

GITHUB_ADDRESS_PATTERN = re.compile(r"github\.com[:/]([^/\s]+)/([^/\s]+?)(?:\.git)?/?$")
# GitPython cannot stop a git command that hangs on Windows, so there it runs without a limit.
GIT_TIME_LIMIT: float | None = None if sys.platform == "win32" else GIT_TIMEOUT_SECONDS
# Git writes these into its folder while a rebase or a merge waits to be finished.
type UnfinishedWork = Literal["", "rebase", "merge"]
UNFINISHED_MARKS: dict[str, UnfinishedWork] = {"rebase-merge": "rebase", "rebase-apply": "rebase", "MERGE_HEAD": "merge"}

type CheckoutProblem = Literal["", "not_repository", "unreadable"]


class CommitView(TypedDict):
    sha: str
    title: str
    committed_at: float


# The source checkout the update installs from, as git sees it now. `branch` is empty when no branch is checked out and `upstream` when the branch
# follows none. `ahead` and `behind` count against the upstream as of the last fetch. `changed` counts tracked files with changes and `untracked`
# the new ones git does not ignore; `names` holds the first few of either. `origin` is that remote's address with any sign-in details taken out,
# and `online` is its "owner/name" on GitHub when the branch follows a branch there.
class CheckoutView(TypedDict):
    path: str
    problem: CheckoutProblem
    branch: str
    upstream: str
    ahead: int
    behind: int
    head: CommitView | None
    changed: int
    untracked: int
    names: list[str]
    origin: str
    online: str
    online_branch: str
    fetched_at: float | None
    version: str
    unfinished: UnfinishedWork


def without_sign_in(address: str) -> str:
    parts = urlsplit(address)
    if parts.username is None and parts.password is None:
        return address
    host = parts.hostname or ""
    return urlunsplit((parts.scheme, host if parts.port is None else f"""{host}:{parts.port}""", parts.path, parts.query, parts.fragment))


def blank_checkout(root: Path, problem: CheckoutProblem) -> CheckoutView:
    return {
        "path": str(root), "problem": problem, "branch": "", "upstream": "", "ahead": 0, "behind": 0, "head": None, "changed": 0, "untracked": 0, "names": [],
        "origin": "", "online": "", "online_branch": "", "fetched_at": None, "version": "", "unfinished": "",
    }


# The path of one entry in git's machine-readable status: the last field, and for a rename the new name, which comes before a tab.
def entry_path(line: str) -> str:
    fields_before_path = {"1": 8, "2": 9, "u": 10, "?": 1}[line[0]]
    return line.split(" ", fields_before_path)[fields_before_path].split("\t")[0]


# Every lookup here only reads. Git is told not to refresh its index on the way, which `git status` otherwise does and which takes a lock that
# another git command could trip over. Nothing is fetched, so `ahead`, `behind` and the upstream are what the last fetch left.
def read_checkout(root: Path) -> CheckoutView:
    import git

    from stackops.scripts.python.helpers.helpers_devops.stackops_release import read_stackops_project

    try:
        repo = git.Repo(root)
    except (git.InvalidGitRepositoryError, git.NoSuchPathError):
        return blank_checkout(root=root, problem="not_repository")
    with repo:
        repo.git.update_environment(GIT_OPTIONAL_LOCKS="0")
        try:
            lines = str(repo.git.status("--porcelain=v2", "--branch", "--untracked-files=all", kill_after_timeout=GIT_TIME_LIMIT)).splitlines()
        except git.GitCommandError:
            return blank_checkout(root=root, problem="unreadable")
        notes = {parts[1]: parts[2] for parts in (line.split(" ", 2) for line in lines if line.startswith("# ")) if len(parts) == 3}
        entries = [line for line in lines if line[:1] in ("1", "2", "u", "?")]
        branch = notes.get("branch.head", "")
        upstream = notes.get("branch.upstream", "")
        ahead, behind = (abs(int(count)) for count in notes.get("branch.ab", "+0 -0").split())
        origin = next((remote.url for remote in repo.remotes if remote.name == "origin"), "")
        hosted = GITHUB_ADDRESS_PATTERN.search(origin)
        follows_origin = upstream.startswith("origin/")
        fetch_note = Path(repo.git_dir).joinpath("FETCH_HEAD")
        try:
            version = str(read_stackops_project(repo_root=root).get("version", ""))
        except (OSError, ValueError):
            version = ""
        head: CommitView | None = None
        if repo.head.is_valid():
            head = {"sha": repo.head.commit.hexsha, "title": str(repo.head.commit.summary), "committed_at": float(repo.head.commit.committed_date)}
        unfinished: UnfinishedWork = ""
        for mark, kind in UNFINISHED_MARKS.items():
            if Path(repo.git_dir).joinpath(mark).exists():
                unfinished = kind
                break
        return {
            "path": str(root),
            "problem": "",
            "branch": "" if branch == "(detached)" else branch,
            "upstream": upstream,
            "ahead": ahead,
            "behind": behind,
            "head": head,
            "changed": sum(1 for line in entries if line[0] != "?"),
            "untracked": sum(1 for line in entries if line[0] == "?"),
            "names": [entry_path(line) for line in entries[:CHANGED_NAMES_SHOWN]],
            "origin": without_sign_in(origin),
            "online": f"""{hosted.group(1)}/{hosted.group(2)}""" if hosted is not None and follows_origin else "",
            "online_branch": upstream.removeprefix("origin/") if follows_origin else "",
            "fetched_at": fetch_note.stat().st_mtime if fetch_note.is_file() else None,
            "version": version,
            "unfinished": unfinished,
        }


# The commits the checkout already has, newest first, as far back as the page needs to tell which of the newest ones online are new to it.
def read_local_history(root: Path) -> frozenset[str]:
    import git

    try:
        with git.Repo(root) as repo:
            return frozenset(str(repo.git.rev_list(f"""--max-count={LOCAL_HISTORY_DEPTH}""", "HEAD", kill_after_timeout=GIT_TIME_LIMIT)).split())
    except (git.InvalidGitRepositoryError, git.NoSuchPathError, git.GitCommandError):
        return frozenset()
