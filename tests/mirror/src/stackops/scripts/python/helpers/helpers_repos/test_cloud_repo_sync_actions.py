from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_actions import publish_local_repository, validate_integration_transport
from stackops.utils.cloud.rclone import RcloneConfigError
from stackops.utils.path_core import PathLike


def test_remote_recovery_copy_is_removed_only_after_successful_upload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    local_root = tmp_path.joinpath("local", "repository")
    remote_root = tmp_path.joinpath("remote", "repository")
    events: list[str] = []

    def upload_repo_archive(repo_root: Path, cloud: str, remote_path: Path, pwd: str | None) -> None:
        assert repo_root == local_root
        assert cloud == "fake-cloud"
        assert remote_path == Path("archive.zip.gpg")
        assert pwd is None
        events.append("upload")

    def delete_path(target: PathLike, *, verbose: bool) -> None:
        assert Path(target) == remote_root.parent
        assert verbose
        events.append("delete")

    monkeypatch.setattr("stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_archive.upload_repo_archive", upload_repo_archive)
    monkeypatch.setattr("stackops.utils.path_core.delete_path", delete_path)

    publish_local_repository(
        repo_local_root=local_root, repo_remote_root=remote_root, cloud="fake-cloud", remote_path=Path("archive.zip.gpg"), pwd=None
    )

    assert events == ["upload", "delete"]


def test_failed_upload_preserves_remote_recovery_copy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    remote_root = tmp_path.joinpath("remote", "repository")
    delete_calls: list[Path] = []

    def upload_repo_archive(repo_root: Path, cloud: str, remote_path: Path, pwd: str | None) -> None:
        _ = repo_root, cloud, remote_path, pwd
        raise RuntimeError("synthetic upload failure")

    def delete_path(target: PathLike, *, verbose: bool) -> None:
        _ = verbose
        delete_calls.append(Path(target))

    monkeypatch.setattr("stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_archive.upload_repo_archive", upload_repo_archive)
    monkeypatch.setattr("stackops.utils.path_core.delete_path", delete_path)

    with pytest.raises(RuntimeError, match="synthetic upload failure"):
        publish_local_repository(
            repo_local_root=tmp_path.joinpath("local", "repository"),
            repo_remote_root=remote_root,
            cloud="fake-cloud",
            remote_path=Path("archive.zip.gpg"),
            pwd=None,
        )

    assert delete_calls == []


def test_integration_transport_validation_uses_candidate_config_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from stackops.utils import source_of_truth
    from stackops.utils.cloud import rclone

    local_root = tmp_path.joinpath("dotfiles")
    integration_root = tmp_path.joinpath("integration")
    relative_config_path = Path("creds/rclone/rclone.conf")
    candidate_config_path = integration_root.joinpath(relative_config_path)
    candidate_config_path.parent.mkdir(parents=True)
    candidate_config_path.write_text("synthetic config placeholder\n", encoding="utf-8")
    inspected_paths: list[Path] = []

    def list_remote_names_from_config(config_path: Path) -> tuple[str, ...]:
        inspected_paths.append(config_path)
        return ("different-cloud",)

    monkeypatch.setattr(source_of_truth, "DOTFILES_ROOT", local_root)
    monkeypatch.setattr(source_of_truth, "DOTFILES_RCLONE_CONF_PATH", local_root.joinpath(relative_config_path))
    monkeypatch.setattr(rclone, "list_remote_names_from_config", list_remote_names_from_config)

    with pytest.raises(RcloneConfigError, match="required-cloud"):
        validate_integration_transport(repo_local_root=local_root, integration_root=integration_root, cloud="required-cloud")

    assert inspected_paths == [candidate_config_path]
