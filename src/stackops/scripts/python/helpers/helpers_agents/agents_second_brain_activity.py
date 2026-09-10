from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
import subprocess


@dataclass(frozen=True)
class GitActivity:
    commits: int
    files_changed: int
    files_added: int
    lines_added: int
    lines_deleted: int


@dataclass(frozen=True)
class WorkingTreeActivity:
    new_files: int
    changed_files: int
    deleted_files: int


@dataclass(frozen=True)
class SecondBrainGitActivity:
    today: GitActivity
    this_week: GitActivity
    working_tree: WorkingTreeActivity


def _run_git(*, second_brain_root: Path, arguments: list[str]) -> bytes:
    result = subprocess.run(
        ["git", "--no-optional-locks", *arguments],
        cwd=second_brain_root,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.decode(errors="replace").strip()
        raise RuntimeError(f"""Cannot read Second Brain Git activity in {second_brain_root}: {message}""")
    return result.stdout


def _read_committed_activity(*, second_brain_root: Path, start: date, end: date, has_commits: bool) -> GitActivity:
    commits = 0
    changed_files: set[bytes] = set()
    added_files: set[bytes] = set()
    lines_added = 0
    lines_deleted = 0
    if has_commits:
        since = datetime.combine(start, time.min).astimezone().isoformat()
        until = datetime.combine(end, time.max).astimezone().isoformat(timespec="seconds")
        output = _run_git(
            second_brain_root=second_brain_root,
            arguments=[
                "log",
                f"""--since-as-filter={since}""",
                f"""--until={until}""",
                "--format=format:commit%x00",
                "--raw",
                "--numstat",
                "--no-renames",
                "--no-ext-diff",
                "--no-textconv",
                "--diff-merges=off",
                "-z",
                "HEAD",
                "--",
            ],
        )
        records = iter(output.split(b"\0"))
        for record in records:
            record = record.lstrip(b"\n")
            if not record:
                continue
            if record == b"commit":
                commits += 1
            elif record.startswith(b":"):
                path = next(records)
                changed_files.add(path)
                if record.rsplit(b" ", 1)[1] == b"A":
                    added_files.add(path)
            else:
                added, deleted, _path = record.split(b"\t", 2)
                if added != b"-":
                    lines_added += int(added)
                    lines_deleted += int(deleted)
    return GitActivity(
        commits=commits,
        files_changed=len(changed_files),
        files_added=len(added_files),
        lines_added=lines_added,
        lines_deleted=lines_deleted,
    )


def read_second_brain_git_activity(*, second_brain_root: Path, today: date) -> SecondBrainGitActivity:
    output = _run_git(
        second_brain_root=second_brain_root,
        arguments=["status", "--porcelain=v2", "--branch", "--untracked-files=all", "--no-renames", "-z"],
    )
    has_commits = True
    new_files = 0
    changed_files = 0
    deleted_files = 0
    for record in output.split(b"\0"):
        if record == b"# branch.oid (initial)":
            has_commits = False
        elif record.startswith(b"? "):
            new_files += 1
        elif record.startswith((b"1 ", b"u ")):
            change = record[2:4]
            if b"D" in change:
                deleted_files += 1
            elif b"A" in change:
                new_files += 1
            else:
                changed_files += 1
    return SecondBrainGitActivity(
        today=_read_committed_activity(second_brain_root=second_brain_root, start=today, end=today, has_commits=has_commits),
        this_week=_read_committed_activity(
            second_brain_root=second_brain_root,
            start=today - timedelta(days=today.weekday()),
            end=today,
            has_commits=has_commits,
        ),
        working_tree=WorkingTreeActivity(new_files=new_files, changed_files=changed_files, deleted_files=deleted_files),
    )
