from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from git.exc import InvalidGitRepositoryError, NoSuchPathError
from git.repo import Repo


type RepositoryState = Literal["Missing", "Not a Git repo", "Clean", "Changed", "Bare"]
type ChangeKind = Literal["m", "n", "d", "r", "u"]


@dataclass(frozen=True)
class LocalRepositoryStatus:
    path: Path
    state: RepositoryState
    changes: str
    branch: str | None
    committed_at: datetime | None


def inspect_local_repository(destination: Path) -> LocalRepositoryStatus:
    path = destination.expanduser().absolute()
    try:
        with Repo(path, search_parent_directories=False) as repository:
            counts: dict[ChangeKind, int] = {"m": 0, "n": 0, "d": 0, "r": 0, "u": 0}
            status_output = "" if repository.bare else repository.git.status(
                porcelain="v1", z=True, untracked_files="all", ignore_submodules="none"
            )
            entries = iter(status_output.split("\0"))
            for entry in entries:
                if not entry:
                    continue
                change = entry[:2]
                if "R" in change or "C" in change:
                    next(entries)
                if "U" in change or change in {"AA", "DD"}:
                    counts["u"] += 1
                elif "D" in change:
                    counts["d"] += 1
                elif change == "??" or "A" in change or "C" in change:
                    counts["n"] += 1
                elif "R" in change:
                    counts["r"] += 1
                else:
                    counts["m"] += 1
            changes = "/".join(f"""{count}{kind}""" for kind, count in counts.items() if count)
            state: RepositoryState = "Bare" if repository.bare else ("Changed" if changes else "Clean")
            branch = None if repository.head.is_detached else repository.active_branch.name
            committed_at = repository.head.commit.committed_datetime.astimezone() if repository.head.is_valid() else None
            return LocalRepositoryStatus(path=path, state=state, changes=changes, branch=branch, committed_at=committed_at)
    except NoSuchPathError:
        return LocalRepositoryStatus(path=path, state="Missing", changes="", branch=None, committed_at=None)
    except InvalidGitRepositoryError:
        return LocalRepositoryStatus(path=path, state="Not a Git repo", changes="", branch=None, committed_at=None)
