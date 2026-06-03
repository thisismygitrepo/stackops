from pathlib import Path

import pytest
import yaml

from stackops.scripts.python.helpers.helpers_cloud import cloud_copy
from stackops.scripts.python.helpers.helpers_devops import backup_config, cli_backup_retrieve


def _run_cloud_copy(
    source: Path,
    target: str,
    *,
    share: bool = True,
    record: bool = False,
    record_group: str = "default",
    record_name: str | None = None,
    zip_: bool = False,
    encrypt: bool = False,
) -> None:
    cloud_copy.main(
        source=source.as_posix(),
        target=target,
        overwrite=False,
        share=share,
        record=record,
        record_group=record_group,
        record_name=record_name,
        record_os="linux,darwin,windows",
        rel2home=False,
        root="myhome",
        key=None,
        pwd=None,
        encrypt=encrypt,
        zip_=zip_,
        os_specific=False,
        config=None,
    )


def test_cloud_copy_share_does_not_write_share_url_sidecar(monkeypatch, tmp_path: Path) -> None:
    local_path = tmp_path / "report.txt"
    local_path.write_text("report\n", encoding="utf-8")

    def fake_to_cloud(**_kwargs: object) -> str:
        return "https://example.test/share/report"

    monkeypatch.setattr(cloud_copy.rclone_wrapper, "to_cloud", fake_to_cloud)

    _run_cloud_copy(local_path, "odp:backups/report.txt", share=True, record=False)

    assert not local_path.with_suffix(".share_url_odp").exists()


def test_cloud_copy_record_writes_share_url_to_data_yaml(monkeypatch, tmp_path: Path) -> None:
    backup_path = tmp_path / "dotfiles" / "stackops" / "mapper" / "data.yaml"
    local_path = tmp_path / "report.txt"
    local_path.write_text("report\n", encoding="utf-8")
    share_url = "https://example.test/share/report"

    def fake_to_cloud(**_kwargs: object) -> str:
        return share_url

    monkeypatch.setattr(cloud_copy.rclone_wrapper, "to_cloud", fake_to_cloud)
    monkeypatch.setattr(backup_config, "USER_BACKUP_PATH", backup_path)
    monkeypatch.setattr(cli_backup_retrieve, "USER_BACKUP_PATH", backup_path)

    _run_cloud_copy(
        local_path,
        "odp:backups/report.txt",
        share=True,
        record=True,
        record_group="shared",
        record_name="report",
    )

    document = yaml.safe_load(backup_path.read_text(encoding="utf-8"))
    assert document == {
        "shared": {
            "report": {
                "path_local": local_path.as_posix(),
                "path_cloud": "odp:backups/report.txt",
                "share_url": share_url,
                "encrypt": False,
                "zip": False,
                "rel2home": False,
                "os": ["linux", "darwin", "windows"],
            }
        }
    }
    assert not local_path.with_suffix(".share_url_odp").exists()


def test_cloud_copy_record_without_share_writes_data_yaml(monkeypatch, tmp_path: Path) -> None:
    backup_path = tmp_path / "dotfiles" / "stackops" / "mapper" / "data.yaml"
    local_path = tmp_path / "report.txt"
    local_path.write_text("report\n", encoding="utf-8")

    def fake_to_cloud(**_kwargs: object) -> None:
        return None

    monkeypatch.setattr(cloud_copy.rclone_wrapper, "to_cloud", fake_to_cloud)
    monkeypatch.setattr(backup_config, "USER_BACKUP_PATH", backup_path)
    monkeypatch.setattr(cli_backup_retrieve, "USER_BACKUP_PATH", backup_path)

    _run_cloud_copy(
        local_path,
        "odp:backups/report.txt",
        share=False,
        record=True,
        record_group="shared",
        record_name="report",
    )

    document = yaml.safe_load(backup_path.read_text(encoding="utf-8"))
    assert document == {
        "shared": {
            "report": {
                "path_local": local_path.as_posix(),
                "path_cloud": "odp:backups/report.txt",
                "share_url": None,
                "encrypt": False,
                "zip": False,
                "rel2home": False,
                "os": ["linux", "darwin", "windows"],
            }
        }
    }
    assert not local_path.with_suffix(".share_url_odp").exists()


def test_cloud_copy_record_requires_record_name(monkeypatch, tmp_path: Path) -> None:
    local_path = tmp_path / "report.txt"
    local_path.write_text("report\n", encoding="utf-8")

    def fake_to_cloud(**_kwargs: object) -> None:
        return None

    monkeypatch.setattr(cloud_copy.rclone_wrapper, "to_cloud", fake_to_cloud)

    with pytest.raises(SystemExit) as exc_info:
        _run_cloud_copy(
            local_path,
            "odp:backups/report.txt",
            share=False,
            record=True,
        )

    assert exc_info.value.code == 1


def test_record_path_cloud_strips_generated_artifact_suffixes() -> None:
    assert (
        cloud_copy._strip_artifact_suffixes(
            Path("backups/report.txt.zip.gpg"),
            zip_requested=True,
            encrypt_requested=True,
        )
        == "backups/report.txt"
    )
