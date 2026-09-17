from pathlib import Path

from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_archive import get_repo_remote_archive_path
from stackops.scripts.python.helpers.helpers_repos.spec_store import repo_record_path
from stackops.utils.cloud.default_remote import read_default_rclone_remote
from stackops.utils.schemas.repos.repos_types import RepoRecordDict, RepoSync


def configure_repository_sync(
    records: list[RepoRecordDict], existing_records: list[RepoRecordDict], guard: bool | None, cloud: str | None, ignore_gitignore: bool | None
) -> None:
    existing_syncs: dict[Path, RepoSync] = {repo_record_path(record): record["sync"] for record in existing_records}
    resolved_cloud = cloud
    for record in records:
        path = repo_record_path(repo_record=record)
        previous: RepoSync = existing_syncs.get(path, {"mode": "git"})
        if guard is None:
            record["sync"] = previous
        elif guard:
            if resolved_cloud is None and previous["mode"] != "guard":
                resolved_cloud = read_default_rclone_remote()
            record["sync"] = {
                "mode": "guard",
                "cloud": cloud or (previous["cloud"] if previous["mode"] == "guard" else str(resolved_cloud)),
                "remotePath": previous["remotePath"] if previous["mode"] == "guard" else get_repo_remote_archive_path(repo_root=path).as_posix(),
                "ignoreGitignore": ignore_gitignore if ignore_gitignore is not None else previous["mode"] == "guard" and previous["ignoreGitignore"],
            }
        else:
            record["sync"] = {"mode": "git"}
        if record["sync"]["mode"] == "guard":
            record["remotes"] = []
