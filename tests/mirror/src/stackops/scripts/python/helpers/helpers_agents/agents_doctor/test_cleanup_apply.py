import os
import errno
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_apply import apply_cleanup_plan
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_models import CleanupChange, CleanupPlan
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_paths import capture_cleanup_snapshot


def test_stale_snapshot_blocks_every_change_before_mutation(tmp_path: Path) -> None:
    paths = (tmp_path / "first.json", tmp_path / "second.json")
    for path in paths:
        path.write_text("original", encoding="utf-8")
    plan = CleanupPlan(
        entries=(),
        changes=tuple(CleanupChange(capture_cleanup_snapshot(path=path, home_directory=tmp_path), None) for path in paths),
        blockers=(),
    )
    paths[1].write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="changed since inspection"):
        apply_cleanup_plan(plan=plan, backup_root=tmp_path / "quarantine", home_directory=tmp_path)
    assert paths[0].read_text(encoding="utf-8") == "original"
    assert not (tmp_path / "quarantine").exists()


def test_failed_write_rolls_back_previous_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = (tmp_path / "first.json", tmp_path / "second.json")
    for path in paths:
        path.write_text("original", encoding="utf-8")
    plan = CleanupPlan(
        entries=(),
        changes=tuple(CleanupChange(capture_cleanup_snapshot(path=path, home_directory=tmp_path), b"new") for path in paths),
        blockers=(),
    )
    original_replace = os.replace

    def fail_second_move(source: Path, destination: Path) -> None:
        if source == paths[1]:
            raise PermissionError("Simulated write failure")
        original_replace(source, destination)

    monkeypatch.setattr(os, "replace", fail_second_move)
    with pytest.raises(ValueError, match="rolled back"):
        apply_cleanup_plan(plan=plan, backup_root=tmp_path / "quarantine", home_directory=tmp_path)
    assert all(path.read_text(encoding="utf-8") == "original" for path in paths)


def test_symlink_and_protected_paths_are_rejected_before_reading(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "linked"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="Symlink"):
        capture_cleanup_snapshot(path=link / "settings.json", home_directory=tmp_path)
    with pytest.raises(ValueError, match="Protected"):
        capture_cleanup_snapshot(path=tmp_path / "dotfiles" / "settings.json", home_directory=tmp_path)


def test_directory_quarantine_preserves_nested_symlink_without_following_it(tmp_path: Path) -> None:
    directory = tmp_path / "plugin"
    directory.mkdir()
    (directory / "nested").symlink_to(tmp_path / "dotfiles", target_is_directory=True)
    snapshot = capture_cleanup_snapshot(path=directory, home_directory=tmp_path)
    assert snapshot.files == ()
    assert snapshot.links == ((Path("nested"), str(tmp_path / "dotfiles")),)
    result = apply_cleanup_plan(
        plan=CleanupPlan(entries=(), changes=(CleanupChange(snapshot, None),), blockers=()),
        backup_root=tmp_path / "quarantine", home_directory=tmp_path,
    )
    assert not directory.exists()
    assert result.backup_directory is not None
    assert (result.backup_directory / "0000-plugin" / "nested").is_symlink()


def test_leaf_symlink_can_be_quarantined_without_reading_or_removing_target(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.write_text("untouched", encoding="utf-8")
    link = tmp_path / "linked-skill"
    link.symlink_to(target)
    snapshot = capture_cleanup_snapshot(path=link, home_directory=tmp_path)
    result = apply_cleanup_plan(
        plan=CleanupPlan(entries=(), changes=(CleanupChange(snapshot, None),), blockers=()),
        backup_root=tmp_path / "quarantine", home_directory=tmp_path,
    )
    assert not link.is_symlink()
    assert target.read_text(encoding="utf-8") == "untouched"
    assert result.backup_directory is not None
    assert (result.backup_directory / "0000-linked-skill").is_symlink()


def test_backups_cannot_be_inside_the_target_directory(tmp_path: Path) -> None:
    directory = tmp_path / "plugin"
    directory.mkdir()
    plan = CleanupPlan(entries=(), changes=(CleanupChange(capture_cleanup_snapshot(path=directory, home_directory=tmp_path), None),), blockers=())
    with pytest.raises(ValueError, match="inside a cleanup target"):
        apply_cleanup_plan(plan=plan, backup_root=directory / "quarantine", home_directory=tmp_path)
    assert directory.exists()


def test_backups_do_not_require_cross_filesystem_renames(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    directory = tmp_path / "plugin"
    directory.mkdir()
    path = directory / "hook.json"
    path.write_text("original", encoding="utf-8")
    plan = CleanupPlan(entries=(), changes=(CleanupChange(capture_cleanup_snapshot(path=directory, home_directory=tmp_path), None),), blockers=())
    original_replace = os.replace
    backup_root = tmp_path / "backups"

    def same_directory_replace(source: Path, destination: Path) -> None:
        if source.is_relative_to(backup_root) != destination.is_relative_to(backup_root):
            raise OSError(errno.EXDEV, "Cross-device rename")
        original_replace(source, destination)

    monkeypatch.setattr(os, "replace", same_directory_replace)
    result = apply_cleanup_plan(plan=plan, backup_root=backup_root, home_directory=tmp_path)
    assert not directory.exists()
    assert result.backup_directory is not None
    assert (result.backup_directory / "0000-plugin" / "hook.json").read_text(encoding="utf-8") == "original"
