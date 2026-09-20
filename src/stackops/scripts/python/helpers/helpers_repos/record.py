from pathlib import Path

import stackops.utils.path_core as path_core
from stackops.utils.schemas.repos.repos_types import GitVersionInfo, RepoRecordDict, RepoRemote

from stackops.utils.schemas.repos.repos_types import RepoRecordFile
from stackops.scripts.python.helpers.helpers_repos.spec_store import (
    load_or_create_repos_spec,
    merge_repo_records,
    repo_record_path,
    resolve_repos_spec_path,
    save_repos_spec,
    RepoRecordMergeEntry,
    RepoRecordMergeReport,
)

from rich import print as pprint
from rich.progress import Progress, TaskID, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, MofNCompleteColumn


_MERGE_FIELD_LABELS = {
    "name": "name",
    "parentDir": "parent path",
    "currentBranch": "branch",
    "remotes": "remotes",
    "version": "commit/branch pin",
    "isDirty": "dirty status",
    "sync": "sync destination",
}


def build_tree_structure(repos: list[RepoRecordDict], repos_root: Path) -> str:
    """Build a tree structure representation of all repositories."""
    if not repos:
        return "No repositories found."

    # Group repos by their parent directories relative to repos_root
    tree_dict: dict[str, list[RepoRecordDict]] = {}
    repos_root_abs = repos_root.expanduser().absolute()

    for repo in repos:
        parent_path = Path(repo["parentDir"]).expanduser().absolute()
        try:
            relative_path = parent_path.relative_to(repos_root_abs)
            relative_str = str(relative_path) if str(relative_path) != "." else ""
        except ValueError:
            # If the path is not relative to repos_root, use the full path
            relative_str = str(parent_path)

        if relative_str not in tree_dict:
            tree_dict[relative_str] = []
        tree_dict[relative_str].append(repo)

    # Sort directories for consistent output
    sorted_dirs = sorted(tree_dict.keys())

    tree_lines: list[str] = []
    tree_lines.append(f"📂 {repos_root.name}/ ({repos_root_abs})")

    for i, dir_path in enumerate(sorted_dirs):
        is_last_dir = i == len(sorted_dirs) - 1
        dir_prefix = "└── " if is_last_dir else "├── "

        if dir_path:
            tree_lines.append(f"│   {dir_prefix}📁 {dir_path}/")
            repo_prefix_base = "│   │   " if not is_last_dir else "    "
        else:
            repo_prefix_base = "│   "

        repos_in_dir = tree_dict[dir_path]
        # Sort repos by name
        repos_in_dir.sort(key=lambda x: x["name"])

        for j, repo in enumerate(repos_in_dir):
            is_last_repo = j == len(repos_in_dir) - 1
            repo_prefix = f"{repo_prefix_base}└── " if is_last_repo else f"{repo_prefix_base}├── "

            # Create status indicators
            status_indicators = []
            if repo["isDirty"]:
                status_indicators.append("🔶 DIRTY")
            if repo["sync"]["mode"] == "guard":
                status_indicators.append(f"""🔐 GUARD ({repo['sync']['cloud']})""")
            elif not repo["remotes"]:
                status_indicators.append("⚠️ NO_REMOTE")
            if repo["currentBranch"] == "DETACHED":
                status_indicators.append("🔀 DETACHED")

            status_str = f"[{' | '.join(status_indicators)}]" if status_indicators else "[✅ CLEAN]"
            branch_info = f" ({repo['currentBranch']})" if repo["currentBranch"] != "DETACHED" else ""

            # Build the base string without status
            base_str = f"{repo_prefix}📦 {repo['name']}{branch_info}"

            # Calculate padding to align status at 75 characters
            target_width = 45
            current_length = len(base_str)
            padding = max(1, target_width - current_length)  # At least 1 space

            tree_lines.append(f"{base_str}{' ' * padding}{status_str}")

    return "\n".join(tree_lines)


def _format_merge_entry(entry: RepoRecordMergeEntry) -> str:
    return f"{entry['name']} ({entry['path']}) [branch: {entry['branch']}]"


def _format_changed_fields(entry: RepoRecordMergeEntry) -> str:
    return ", ".join(_MERGE_FIELD_LABELS.get(field, field) for field in entry["changedFields"])


def _print_merge_entries(label: str, marker: str, entries: list[RepoRecordMergeEntry], include_changed_fields: bool = False) -> None:
    print(f"   {label}: {len(entries)}")
    for entry in entries:
        changed_suffix = ""
        if include_changed_fields and entry["changedFields"]:
            changed_suffix = f" | changed: {_format_changed_fields(entry)}"
        print(f"      {marker} {_format_merge_entry(entry)}{changed_suffix}")


def _print_unchanged_summary(entries: list[RepoRecordMergeEntry], limit: int = 12) -> None:
    if not entries:
        print("   Unchanged: 0")
        return
    names = ", ".join(entry["name"] for entry in entries[:limit])
    if len(entries) > limit:
        print(f"   Unchanged: {len(entries)} (showing first {limit}: {names})")
    else:
        print(f"   Unchanged: {len(entries)} ({names})")


def _print_merge_report(report: RepoRecordMergeReport) -> None:
    print("\n🧾 Global spec update:")
    _print_merge_entries("Added", "+", report["added"])
    _print_merge_entries("Updated", "~", report["updated"], include_changed_fields=True)
    _print_merge_entries("Removed from spec", "-", report["removed"])
    _print_unchanged_summary(report["unchanged"])


def record_a_repo(path: Path, search_parent_directories: bool, preferred_remote: str | None) -> RepoRecordDict:
    from git.repo import Repo

    repo = Repo(path, search_parent_directories=search_parent_directories)  # get list of remotes using git python
    repo_root = Path(repo.working_dir).absolute()
    # remotes: = {remote.name: remote.url for remote in repo.remotes}
    remotes: list[RepoRemote] = [{"name": remote.name, "url": remote.url} for remote in repo.remotes]
    if preferred_remote is not None:
        if preferred_remote in [remote["name"] for remote in remotes]:
            remotes = [remote for remote in remotes if remote["name"] == preferred_remote]
        else:
            print(f"⚠️ `{preferred_remote=}` not found in {remotes}.")
            preferred_remote = None
    try:
        commit = repo.head.commit.hexsha
    except ValueError:  # look at https://github.com/gitpython-developers/GitPython/issues/1016
        print(f"⚠️ Failed to get latest commit of {repo}")
        commit = "UNKNOWN"
    try:
        current_branch = repo.head.reference.name  # same as repo.active_branch.name
    except TypeError:
        print(f"⁉️ Failed to get current branch of {repo}. It is probably in a detached state.")
        # current_branch = None
        current_branch = "DETACHED"

    # Check if repo is dirty (has uncommitted changes)
    is_dirty = repo.is_dirty(untracked_files=True)

    version_info: GitVersionInfo = {"branch": current_branch, "commit": commit}

    res: RepoRecordDict = {
        "name": repo_root.name,
        "parentDir": path_core.collapseuser(repo_root.parent, strict=False).as_posix(),
        "currentBranch": current_branch,
        "remotes": remotes,
        "version": version_info,
        "isDirty": is_dirty,
        "sync": {"mode": "git"},
    }
    return res


def count_git_repositories(repos_root: str, r: bool) -> int:
    """Count total git repositories for accurate progress tracking."""
    path_obj = Path(repos_root).expanduser().absolute()
    if path_obj.is_file():
        return 0
    if path_obj.joinpath(".git").exists():
        return 1

    search_res = sorted(
        (candidate for candidate in path_obj.glob("*") if candidate.is_dir() and not candidate.name.startswith(".")), key=lambda path: path.as_posix()
    )
    count = 0

    for a_search_res in search_res:
        if a_search_res.joinpath(".git").exists():
            count += 1
        elif r:
            count += count_git_repositories(str(a_search_res), r=r)

    return count


def count_total_directories(repos_root: str, r: bool) -> int:
    """Count total directories to scan for accurate progress tracking."""
    path_obj = Path(repos_root).expanduser().absolute()
    if path_obj.is_file():
        return 0
    if path_obj.joinpath(".git").exists():
        return 0

    search_res = sorted(
        (candidate for candidate in path_obj.glob("*") if candidate.is_dir() and not candidate.name.startswith(".")), key=lambda path: path.as_posix()
    )
    count = len(search_res)

    if r:
        for a_search_res in search_res:
            if not a_search_res.joinpath(".git").exists():
                count += count_total_directories(str(a_search_res), r=r)

    return count


def record_repos_recursively(
    repos_root: str, r: bool, progress: Progress | None, scan_task_id: TaskID | None, process_task_id: TaskID | None,
    registered_paths: set[Path],
) -> list[RepoRecordDict]:
    path_obj = Path(repos_root).expanduser().absolute()
    if path_obj.is_file():
        return []
    if path_obj.joinpath(".git").exists():
        already_registered = path_obj.resolve() in registered_paths
        if progress is not None and process_task_id is not None:
            label = "Checking registered" if already_registered else "Registering new"
            progress.update(process_task_id, description=f"""{label}: {path_obj.name}""")

        repo_record = record_a_repo(path_obj, search_parent_directories=False, preferred_remote=None)

        if progress is not None and process_task_id is not None:
            label = "Checked registered" if already_registered else "Recorded new"
            progress.update(process_task_id, advance=1, description=f"""{label}: {repo_record['name']}""")
        return [repo_record]

    search_res = sorted(
        (candidate for candidate in path_obj.glob("*") if candidate.is_dir() and not candidate.name.startswith(".")), key=lambda path: path.as_posix()
    )
    res: list[RepoRecordDict] = []

    for a_search_res in search_res:
        if progress is not None and scan_task_id is not None:
            progress.update(scan_task_id, description=f"Scanning: {a_search_res.name}")

        if a_search_res.joinpath(".git").exists():
            try:
                already_registered = a_search_res.resolve() in registered_paths
                if progress is not None and process_task_id is not None:
                    label = "Checking registered" if already_registered else "Registering new"
                    progress.update(process_task_id, description=f"""{label}: {a_search_res.name}""")

                repo_record = record_a_repo(a_search_res, search_parent_directories=False, preferred_remote=None)
                res.append(repo_record)

                if progress is not None and process_task_id is not None:
                    label = "Checked registered" if already_registered else "Recorded new"
                    progress.update(process_task_id, advance=1, description=f"""{label}: {repo_record['name']}""")
            except Exception as e:
                print(f"⚠️ Failed to record {a_search_res}: {e}")
        else:
            if r:
                res += record_repos_recursively(
                    str(a_search_res), r=r, progress=progress, scan_task_id=scan_task_id,
                    process_task_id=process_task_id, registered_paths=registered_paths,
                )

        if progress is not None and scan_task_id is not None:
            progress.update(scan_task_id, advance=1)

    return res


def _resolve_directory(directory: str | None) -> Path:
    import typer

    if directory is None:
        directory = Path.cwd().as_posix()
        typer.echo(f"📁 Using directory: {directory}")
    return Path(directory).expanduser().absolute().resolve()


def main_record(
    repos_root_str: str | None, specs_path: str | Path | None, guard: bool | None, cloud: str | None, ignore_gitignore: bool | None
) -> Path:
    from stackops.scripts.python.helpers.helpers_repos.registration_sync import configure_repository_sync

    repos_root = _resolve_directory(directory=repos_root_str)
    spec_path_resolved = resolve_repos_spec_path(specs_path=specs_path)
    existing_spec = load_or_create_repos_spec(path=spec_path_resolved)
    registered_paths = {repo_record_path(repo) for repo in existing_spec["repos"]}

    if repos_root in registered_paths and repos_root.joinpath(".git").exists():
        print(f"""ℹ️ Already registered: {repos_root.name} ({repos_root}). Checking for changes...""")
        repo_records = [record_a_repo(repos_root, search_parent_directories=False, preferred_remote=None)]
    else:
        print("\n📝 Registering repositories...")
        registered_count = sum(path.is_relative_to(repos_root) for path in registered_paths)
        if registered_count:
            print(f"""ℹ️ Already registered under this directory: {registered_count}. Checking for changes...""")
        print("🔍 Analyzing directory structure...")
        total_dirs = count_total_directories(str(repos_root), r=True)
        total_repos = count_git_repositories(str(repos_root), r=True)
        print(f"""📊 Found {total_dirs} directories to scan and {total_repos} Git repositories to check""")

        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(), MofNCompleteColumn(), TimeElapsedColumn()
        ) as progress:
            scan_task = progress.add_task("Scanning directories...", total=total_dirs)
            process_task = progress.add_task("Checking repositories...", total=total_repos)

            repo_records = record_repos_recursively(
                repos_root=str(repos_root), r=True, progress=progress, scan_task_id=scan_task,
                process_task_id=process_task, registered_paths=registered_paths,
            )

    configure_repository_sync(
        records=repo_records, existing_records=existing_spec["repos"], guard=guard, cloud=cloud, ignore_gitignore=ignore_gitignore
    )
    merged_repos, merge_summary = merge_repo_records(existing_repos=existing_spec["repos"], scanned_repos=repo_records, scanned_root=repos_root)
    if not (merge_summary["added"] or merge_summary["updated"] or merge_summary["removed"]) and spec_path_resolved.exists():
        print(f"""✅ No changes to registered repositories ({len(merge_summary['unchanged'])} unchanged). Specification left unchanged: {spec_path_resolved}""")
        return spec_path_resolved

    # Summary with warnings
    total_repos = len(repo_records)
    repos_with_no_remotes = [repo for repo in repo_records if repo["sync"]["mode"] == "git" and len(repo["remotes"]) == 0]
    guard_repos = [repo for repo in repo_records if repo["sync"]["mode"] == "guard"]
    repos_with_remotes = [repo for repo in repo_records if len(repo["remotes"]) > 0]
    dirty_repos = [repo for repo in repo_records if repo["isDirty"]]
    clean_repos = [repo for repo in repo_records if not repo["isDirty"]]

    print("\n📊 Repository Summary:")
    print(f"   Total repositories found: {total_repos}")
    print(f"   Repositories with remotes: {len(repos_with_remotes)}")
    print(f"""   Guard repositories: {len(guard_repos)}""")
    print(f"   Repositories without remotes: {len(repos_with_no_remotes)}")
    print(f"   Clean repositories: {len(clean_repos)}")
    print(f"   Dirty repositories: {len(dirty_repos)}")

    if repos_with_no_remotes:
        print(f"\n⚠️  WARNING: {len(repos_with_no_remotes)} repositories have no remotes configured:")
        for repo in repos_with_no_remotes:
            repo_path = Path(repo["parentDir"]).joinpath(repo["name"])
            print(f"   • {repo['name']} ({repo_path})")
        print("   These repositories may be local-only or have configuration issues.")
    else:
        print("\n✅ All repositories have sync destinations.")

    if dirty_repos:
        print(f"\n⚠️  WARNING: {len(dirty_repos)} repositories have uncommitted changes:")
        for repo in dirty_repos:
            repo_path = Path(repo["parentDir"]).joinpath(repo["name"])
            print(f"   • {repo['name']} ({repo_path}) [branch: {repo['currentBranch']}]")
        print("   These repositories have uncommitted changes that may need attention.")
    else:
        print("\n✅ All repositories are clean (no uncommitted changes).")

    # Display repository tree structure
    print("\n🌳 Repository Tree Structure:")
    tree_structure = build_tree_structure(repos=repo_records, repos_root=repos_root)
    print(tree_structure)

    res: RepoRecordFile = {"version": existing_spec["version"], "repos": merged_repos}
    save_repos_spec(spec=res, path=spec_path_resolved)
    pprint(f"📁 Result saved at {spec_path_resolved}")
    _print_merge_report(merge_summary)

    print(">>>>>>>>> Finished Recording")
    return spec_path_resolved
