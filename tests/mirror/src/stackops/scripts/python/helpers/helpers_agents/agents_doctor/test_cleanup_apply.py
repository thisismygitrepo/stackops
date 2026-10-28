import os
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_apply import apply_cleanup_plan
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_models import CleanupEdit, CleanupPlan, CleanupRemoval
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_paths import read_editable_file


def _edit_plan(*, paths: tuple[Path, ...], home_directory: Path) -> CleanupPlan:
    changes: list[CleanupEdit] = []
    for path in paths:
        original, mode = read_editable_file(path=path, home_directory=home_directory)
        changes.append(CleanupEdit(path=path, original=original, mode=mode, replacement=b"new"))
    return CleanupPlan(entries=(), changes=tuple(changes), blockers=())


def test_stale_edit_blocks_every_change_before_mutation(tmp_path: Path) -> None:
    paths = (tmp_path / "first.json", tmp_path / "second.json")
    for path in paths:
        path.write_text("original", encoding="utf-8")
    plan = _edit_plan(paths=paths, home_directory=tmp_path)
    paths[1].write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="changed since inspection"):
        apply_cleanup_plan(plan=plan, home_directory=tmp_path)
    assert paths[0].read_text(encoding="utf-8") == "original"


def test_failed_write_rolls_back_previous_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = (tmp_path / "first.json", tmp_path / "second.json")
    for path in paths:
        path.write_text("original", encoding="utf-8")
    plan = _edit_plan(paths=paths, home_directory=tmp_path)
    original_replace = os.replace

    def fail_second_move(source: Path, destination: Path) -> None:
        if source == paths[1]:
            raise PermissionError("Simulated write failure")
        original_replace(source, destination)

    monkeypatch.setattr(os, "replace", fail_second_move)
    with pytest.raises(ValueError, match="rolled back"):
        apply_cleanup_plan(plan=plan, home_directory=tmp_path)
    assert all(path.read_text(encoding="utf-8") == "original" for path in paths)


def test_symlink_protected_and_hard_linked_paths_are_rejected_before_editing(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "linked"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="Symlink"):
        read_editable_file(path=link / "settings.json", home_directory=tmp_path)
    with pytest.raises(ValueError, match="Protected"):
        read_editable_file(path=tmp_path / "dotfiles" / "settings.json", home_directory=tmp_path)
    original = tmp_path / "settings.json"
    original.write_text("{}", encoding="utf-8")
    os.link(original, tmp_path / "settings-alias.json")
    with pytest.raises(ValueError, match="Hard-linked"):
        read_editable_file(path=original, home_directory=tmp_path)


def test_directory_removal_deletes_hard_linked_files_and_never_follows_symlinks(tmp_path: Path) -> None:
    protected = tmp_path / "dotfiles"
    protected.mkdir()
    (protected / "keep.txt").write_text("keep", encoding="utf-8")
    shared = tmp_path / "cache.bin"
    shared.write_text("shared", encoding="utf-8")
    directory = tmp_path / "repo" / ".ai"
    (directory / "tmp_scripts" / "venv").mkdir(parents=True)
    os.link(shared, directory / "tmp_scripts" / "venv" / "linked.bin")
    (directory / "nested").symlink_to(protected, target_is_directory=True)
    result = apply_cleanup_plan(
        plan=CleanupPlan(entries=(), changes=(CleanupRemoval(directory),), blockers=()), home_directory=tmp_path,
    )
    assert result.changed_paths == (directory,)
    assert not directory.exists()
    assert not tuple(directory.parent.glob(".stackops-depoison-*"))
    assert shared.read_text(encoding="utf-8") == "shared"
    assert (protected / "keep.txt").read_text(encoding="utf-8") == "keep"


def test_leaf_symlink_removal_does_not_touch_its_target(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.write_text("untouched", encoding="utf-8")
    link = tmp_path / "linked-skill"
    link.symlink_to(target)
    apply_cleanup_plan(plan=CleanupPlan(entries=(), changes=(CleanupRemoval(link),), blockers=()), home_directory=tmp_path)
    assert not link.is_symlink()
    assert target.read_text(encoding="utf-8") == "untouched"
