# pyright: reportPrivateUsage=false, reportArgumentType=false


from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

import pytest
from git.exc import GitCommandError
from git.remote import Remote
from git.repo import Repo
from rich.console import Console

from stackops.scripts.python.helpers.helpers_repos import cloud_repo_sync as sync_module


@dataclass(frozen=True)
class FakeRemoteReference:
    remote_head: str
    name: str


@dataclass
class FakeRemote:
    name: str
    refs: list[FakeRemoteReference]
    fetched_branches: list[str] = field(default_factory=list)

    def fetch(self, branch_name: str) -> None:
        self.fetched_branches.append(branch_name)


@dataclass
class FakeIndex:
    unmerged: dict[str, object]

    def unmerged_blobs(self) -> dict[str, object]:
        return self.unmerged


@dataclass
class FakeGit:
    merge_output: str
    merge_error: GitCommandError | None = None
    merged_refs: list[str] = field(default_factory=list)

    def merge(self, remote_reference_name: str, no_edit: bool) -> str:
        _ = no_edit
        self.merged_refs.append(remote_reference_name)
        if self.merge_error is not None:
            raise self.merge_error
        return self.merge_output


@dataclass
class FakeRepo:
    created_remote: FakeRemote
    index: FakeIndex
    git: FakeGit

    def create_remote(self, remote_name: str, remote_path: str) -> FakeRemote:
        assert remote_name == sync_module.REMOTE_NAME
        assert remote_path != ""
        return self.created_remote


class FakePathExtended:
    deleted_paths: list[Path] = []

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def zip(self, inplace: bool) -> str:
        assert not inplace
        archive_path = self.path.parent / f"{self.path.name}.zip"
        archive_path.write_text("archive", encoding="utf-8")
        return str(archive_path)

    def delete(self, sure: bool, verbose: bool) -> None:
        _ = sure, verbose
        FakePathExtended.deleted_paths.append(self.path)

    def unzip(self, inplace: bool, verbose: bool, overwrite: bool, content: bool, merge: bool) -> str:
        _ = inplace, verbose, overwrite, content, merge
        extracted_path = self.path.with_suffix("")
        extracted_path.mkdir(parents=True, exist_ok=True)
        return str(extracted_path)


def test_get_remote_reference_name_returns_matching_branch() -> None:
    remote = FakeRemote(
        name="originEnc",
        refs=[
            FakeRemoteReference(remote_head="dev", name="originEnc/dev"),
            FakeRemoteReference(remote_head="master", name="originEnc/master"),
        ],
    )

    assert sync_module._get_remote_reference_name(remote=cast(Remote, remote), branch_name="master") == "originEnc/master"


def test_get_remote_reference_name_raises_for_missing_branch() -> None:
    remote = FakeRemote(name="originEnc", refs=[FakeRemoteReference(remote_head="dev", name="originEnc/dev")])

    with pytest.raises(RuntimeError, match="Remote branch 'master' was not fetched"):
        sync_module._get_remote_reference_name(remote=cast(Remote, remote), branch_name="master")


def test_upload_repo_archive_uses_selected_encryption_and_cleans_up(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    remote_path = Path("backups/repo.zip.gpg")
    cleaned_paths: list[tuple[Path, ...]] = []
    uploaded: list[tuple[Path, str, Path]] = []

    monkeypatch.setattr(sync_module, "PathExtended", FakePathExtended)
    monkeypatch.setattr(sync_module, "encrypt_file_asymmetric", lambda file_path: file_path.with_suffix(".zip.gpg"))
    monkeypatch.setattr(sync_module, "encrypt_file_symmetric", lambda file_path, pwd: file_path.with_name(f"{file_path.stem}-{pwd}.gpg"))
    monkeypatch.setattr(
        sync_module.rclone_wrapper,
        "to_cloud",
        lambda local_path, cloud, remote_path, share, verbose, transfers: uploaded.append((Path(local_path), cloud, Path(remote_path))),
    )
    monkeypatch.setattr(sync_module, "_cleanup_temp_paths", lambda paths: cleaned_paths.append(paths))

    sync_module._upload_repo_archive(repo_root=repo_root, cloud="demo", remote_path=remote_path, pwd=None)
    sync_module._upload_repo_archive(repo_root=repo_root, cloud="demo", remote_path=remote_path, pwd="secret")

    assert uploaded[0][0].name == "repo.zip.gpg"
    assert uploaded[1][0].name == "repo-secret.gpg"
    assert cleaned_paths[0][0].name == "repo.zip"
    assert cleaned_paths[0][1].name == "repo.zip.gpg"


def test_download_repo_archive_restores_and_extracts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_remote_root = tmp_path / "remote-copy"
    remote_path = Path("backups/repo.zip.gpg")
    downloads: list[tuple[Path, str, Path]] = []
    FakePathExtended.deleted_paths = []

    monkeypatch.setattr(sync_module, "PathExtended", FakePathExtended)
    monkeypatch.setattr(sync_module, "delete_path", lambda target, *, verbose: FakePathExtended.deleted_paths.append(Path(target)))
    monkeypatch.setattr(
        sync_module.rclone_wrapper,
        "from_cloud",
        lambda local_path, cloud, remote_path, transfers, verbose: downloads.append((Path(local_path), cloud, Path(remote_path))),
    )
    monkeypatch.setattr(sync_module, "decrypt_file_asymmetric", lambda file_path: file_path.with_suffix(""))

    extracted = sync_module._download_repo_archive(
        repo_remote_root=repo_remote_root,
        cloud="demo",
        remote_path=remote_path,
        pwd=None,
    )

    assert downloads == [(Path(f"{repo_remote_root}.zip.gpg"), "demo", remote_path)]
    assert extracted == repo_remote_root
    assert Path(f"{repo_remote_root}.zip.gpg") in FakePathExtended.deleted_paths


def test_merge_remote_copy_returns_success_or_conflict(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sync_module, "_remove_remote_if_present", lambda repo, remote_name: None)

    success_remote = FakeRemote(name="originEnc", refs=[FakeRemoteReference(remote_head="master", name="originEnc/master")])
    success_repo = FakeRepo(
        created_remote=success_remote,
        index=FakeIndex(unmerged={}),
        git=FakeGit(merge_output="merged"),
    )

    success = sync_module._merge_remote_copy(
        repo=cast(Repo, success_repo),
        remote_path=tmp_path / "remote",
        console=Console(),
    )

    assert success.status == "success"
    assert success.details == "merged"
    assert success_remote.fetched_branches == [sync_module.REMOTE_BRANCH_NAME]

    conflict_remote = FakeRemote(name="originEnc", refs=[FakeRemoteReference(remote_head="master", name="originEnc/master")])
    conflict_repo = FakeRepo(
        created_remote=conflict_remote,
        index=FakeIndex(unmerged={"conflict.txt": object()}),
        git=FakeGit(
            merge_output="",
            merge_error=GitCommandError("merge", 1, stderr="conflict"),
        ),
    )

    conflict = sync_module._merge_remote_copy(
        repo=cast(Repo, conflict_repo),
        remote_path=tmp_path / "remote",
        console=Console(),
    )

    assert conflict.status == "merge_conflict"
    assert conflict.conflict_paths == ("conflict.txt",)
