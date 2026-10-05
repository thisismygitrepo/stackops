from io import StringIO
from pathlib import Path
from unittest.mock import Mock

import pytest
from rich.console import Console

from stackops.scripts.python.helpers.helpers_cloud import backup_config
from stackops.scripts.python.helpers.helpers_cloud.backup_remote import backup_path_needs_default_cloud
from stackops.scripts.python.helpers.helpers_devops import devops_status_backup
from stackops.scripts.python.helpers.helpers_devops.devops_status_data import collect_status_section
from stackops.utils import source_of_truth


@pytest.fixture
def backup_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, Path]:
    data_path = tmp_path / "data.yaml"
    config_path = tmp_path / "config.json"
    config_path.write_text('{"version": "1.0.0"}', encoding="utf-8")
    monkeypatch.setattr(devops_status_backup, "USER_BACKUP_PATH", data_path)
    monkeypatch.setattr(backup_config, "USER_BACKUP_PATH", data_path)
    monkeypatch.setattr(source_of_truth, "DOTFILES_STACKOPS_CONFIG_PATH", config_path)
    monkeypatch.setattr(devops_status_backup, "system", Mock(return_value="Linux"))
    return data_path, config_path


@pytest.mark.parametrize("path_cloud", ["odp:archive", "odp:^", "^", "archive"])
def test_backup_status_uses_registered_user_entries(backup_paths: tuple[Path, Path], path_cloud: str) -> None:
    data_path, _config_path = backup_paths
    data_path.write_text(
        f"""registered:
  item:
    path_local: ~/example
    path_cloud: {path_cloud}
    share_url: null
    zip: false
    encryption: null
    rel2home: true
    os: [linux]
""",
        encoding="utf-8",
    )

    status = devops_status_backup.check_backup_config()

    assert status["source_path"] == data_path
    assert status["backup_items_count"] == 1
    assert status["backup_items"]["registered"]["item"]["path_cloud"] == path_cloud
    assert status["cloud_config"] is None
    assert status["cloud_selection_required"] is (":" not in path_cloud)
    snapshot = collect_status_section("backup")
    assert snapshot.level == ("ready" if ":" in path_cloud else "attention")
    assert snapshot.summary == ("1 backup item" if ":" in path_cloud else "1 backup item · cloud selection required")
    output = StringIO()
    Console(file=output, width=160, color_system=None).print(devops_status_backup.render_backup_status(status))
    rendered = output.getvalue()
    assert str(data_path) in rendered
    assert "registered.item" in rendered
    assert "Library" not in rendered
    assert ("Cloud selection" in rendered) is (":" not in path_cloud)


def test_backup_status_marks_missing_registrations_empty(backup_paths: tuple[Path, Path]) -> None:
    data_path, config_path = backup_paths
    config_path.unlink()

    status = devops_status_backup.check_backup_config()

    assert status["source_path"] == data_path
    assert status["backup_items_count"] == 0
    assert status["backup_items"] == {}
    assert status["cloud_selection_required"] is False
    snapshot = collect_status_section("backup")
    assert snapshot.level == "attention"
    assert snapshot.summary == "No registered backup items"


@pytest.mark.parametrize("contents", ["", "{}"])
def test_backup_status_accepts_empty_user_config(backup_paths: tuple[Path, Path], contents: str) -> None:
    data_path, _config_path = backup_paths
    data_path.write_text(contents, encoding="utf-8")

    status = devops_status_backup.check_backup_config()

    assert status["backup_items_count"] == 0
    assert status["backup_items"] == {}


@pytest.mark.parametrize("contents", ["[]", "registered: {invalid: {path: example}}"])
def test_backup_status_rejects_invalid_user_config(backup_paths: tuple[Path, Path], contents: str) -> None:
    data_path, _config_path = backup_paths
    data_path.write_text(contents, encoding="utf-8")

    with pytest.raises(ValueError):
        devops_status_backup.check_backup_config()
    snapshot = collect_status_section("backup")
    assert snapshot.level == "error"
    assert snapshot.summary == "Check failed"


def test_backup_status_rejects_non_file_user_config(backup_paths: tuple[Path, Path]) -> None:
    data_path, _config_path = backup_paths
    data_path.mkdir()

    with pytest.raises(ValueError, match="Could not load user backup configuration"):
        devops_status_backup.check_backup_config()


@pytest.mark.parametrize("default_remote", ["odp", "   "])
@pytest.mark.parametrize("operating_system", ["linux", "darwin"])
def test_backup_status_checks_default_only_for_current_os(
    backup_paths: tuple[Path, Path], default_remote: str, operating_system: str,
) -> None:
    data_path, config_path = backup_paths
    config_path.write_text(f"""{{"version": "1.0.0", "default_rclone_config": "{default_remote}"}}""", encoding="utf-8")
    data_path.write_text(
        f"""registered:
  other_os:
    path_local: ~/example
    path_cloud: ^
    zip: false
    encryption: null
    rel2home: true
    os: [{operating_system}]
""",
        encoding="utf-8",
    )

    status = devops_status_backup.check_backup_config()

    assert status["backup_items_count"] == 1
    assert status["cloud_selection_required"] is (not default_remote.strip() and operating_system == "linux")
    assert status["cloud_config"] == (default_remote.strip() or None)


@pytest.mark.parametrize(
    ("path_cloud", "requires_default"),
    [(None, True), ("^", True), ("archive", True), (":archive", True), ("odp:", True), ("C:/archive", True), ("odp:archive", False), ("odp:^", False)],
)
def test_backup_remote_requirement_matches_sync_contract(path_cloud: str | None, requires_default: bool) -> None:
    assert backup_path_needs_default_cloud(path_cloud) is requires_default
