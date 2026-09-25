from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from git.objects.commit import Commit
    from git.repo import Repo
    from rich.console import Console


def print_repository_comparison(
    repo: "Repo", local_commit: "Commit | None", remote_commit: "Commit | None", console: "Console", title: str
) -> None:
    from rich import box
    from rich.table import Table
    from rich.text import Text

    if local_commit is not None and remote_commit is not None:
        counts = repo.git.rev_list("--left-right", "--count", f"""{local_commit.hexsha}...{remote_commit.hexsha}""")
        local_ahead, remote_ahead = (int(count) for count in counts.split())
    else:
        local_ahead = int(repo.git.rev_list("--count", local_commit.hexsha)) if local_commit is not None else 0
        remote_ahead = int(repo.git.rev_list("--count", remote_commit.hexsha)) if remote_commit is not None else 0

    table = Table(
        title=Text(title),
        box=box.ROUNDED,
        header_style="bold cyan",
        show_lines=True,
        caption=Text(
            "Ahead/behind: commits relative to the other copy. Files/lines: latest commit compared with its first parent "
            "(empty tree for the first commit). Remote archive: cloud copy."
        ),
    )
    table.add_column("Copy", no_wrap=True)
    table.add_column("Last commit", no_wrap=True)
    table.add_column("Committed", max_width=22)
    table.add_column("Message", overflow="fold", ratio=2)
    table.add_column("Files / lines", justify="right")
    table.add_column("Ahead", justify="right")
    table.add_column("Behind", justify="right")
    for label, commit, ahead, behind in (
        ("Local", local_commit, local_ahead, remote_ahead),
        ("Remote archive", remote_commit, remote_ahead, local_ahead),
    ):
        if commit is None:
            table.add_row(label, "—", "—", Text("No commits"), "—", str(ahead), str(behind))
            continue
        stats = commit.stats.total
        file_label = "file" if stats["files"] == 1 else "files"
        table.add_row(
            label,
            commit.hexsha[:8],
            commit.committed_datetime.strftime("%Y-%m-%d %H:%M %z"),
            Text(str(commit.summary)),
            f"""{stats["files"]} {file_label}
+{stats["insertions"]} / -{stats["deletions"]}""",
            str(ahead),
            str(behind),
        )
    console.print(table)


def print_integration_result(repo: "Repo", previous_commit: str | None, remote_commit: str, console: "Console") -> None:
    from rich.panel import Panel
    from rich.text import Text

    final_commit = repo.head.commit
    if previous_commit is None:
        outcome = "Initialized local repository from the remote archive."
        changed_files = repo.git.ls_tree("-r", "--name-only", "-z", final_commit.hexsha).count("\0")
    else:
        changed_files = len(repo.commit(previous_commit).diff(final_commit))
        if final_commit.hexsha == previous_commit:
            outcome = (
                "Already synchronized; no merge needed."
                if final_commit.hexsha == remote_commit
                else "Local history already contains the remote archive; no merge needed."
            )
        elif final_commit.hexsha == remote_commit:
            outcome = "Fast-forwarded local repository to the remote archive."
        else:
            outcome = "Merged local and remote histories."
    console.print(
        Panel(
            Text(f"""{outcome}
Resulting commit: {final_commit.hexsha[:8]}
Files changed locally: {changed_files}"""),
            title="Integration result",
            border_style="green",
        )
    )


def print_matching_repositories(repo_root: Path, console: "Console", title: str) -> None:
    from git.repo import Repo

    with Repo(repo_root) as repo:
        commit = repo.head.commit if repo.head.is_valid() else None
        print_repository_comparison(repo=repo, local_commit=commit, remote_commit=commit, console=console, title=title)
