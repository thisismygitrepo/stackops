from __future__ import annotations

from pathlib import Path

from stackops.profile.create_links_export import ON_CONFLICT_STRICT
from stackops.utils import links as links_module
from stackops.utils.path_extended import PathExtended


def test_files_are_identical_compares_file_contents(tmp_path: Path) -> None:
    file_one = PathExtended(tmp_path / "one.txt")
    file_two = PathExtended(tmp_path / "two.txt")
    file_one.write_text("same", encoding="utf-8")
    file_two.write_text("same", encoding="utf-8")

    assert links_module.files_are_identical(file_one, file_two) is True

    file_two.write_text("different", encoding="utf-8")

    assert links_module.files_are_identical(file_one, file_two) is False


def test_symlink_map_creates_target_and_link_when_paths_missing(tmp_path: Path) -> None:
    on_conflict: ON_CONFLICT_STRICT = "throw-error"
    default_path = tmp_path / "default" / "config.toml"
    managed_path = tmp_path / "managed" / "config.toml"

    result = links_module.symlink_map(
        config_file_default_path=default_path,
        config_file_self_managed_path=managed_path,
        on_conflict=on_conflict,
    )

    assert result["action"] == "newLinkAndSelfManagedPath"
    assert managed_path.is_file()
    assert default_path.is_symlink()
    assert default_path.resolve() == managed_path.resolve()


def test_copy_map_copies_existing_self_managed_file_to_default_path(
    tmp_path: Path,
) -> None:
    on_conflict: ON_CONFLICT_STRICT = "throw-error"
    default_path = PathExtended(tmp_path / "default" / "config.toml")
    managed_path = PathExtended(tmp_path / "managed" / "config.toml")
    managed_path.parent.mkdir(parents=True, exist_ok=True)
    managed_path.write_text("managed = true\n", encoding="utf-8")

    result = links_module.copy_map(
        config_file_default_path=default_path,
        config_file_self_managed_path=managed_path,
        on_conflict=on_conflict,
    )

    assert result["action"] == "new_link"
    assert default_path.read_text(encoding="utf-8") == "managed = true\n"
    assert not default_path.is_symlink()
