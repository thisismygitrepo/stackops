from collections.abc import Iterator
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_browser_temporary_profiles as temporary_profiles
from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BrowserName


@pytest.fixture
def source_profile(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    expected_profile_path = tmp_path.joinpath("browsers-profiles", "chrome", "base")
    expected_profile_path.mkdir(parents=True)

    def require_not_in_use(*, browser: BrowserName, profile_path: Path) -> None:
        assert browser == "chrome"
        assert profile_path == expected_profile_path

    monkeypatch.setattr(temporary_profiles, "require_browser_profile_not_in_use", require_not_in_use)
    return expected_profile_path


def test_copy_browser_profile_to_temporary_uses_nested_alias_and_excludes_previous_copies(
    monkeypatch: pytest.MonkeyPatch, source_profile: Path
) -> None:
    source_profile.joinpath("Local State").write_bytes(b"state")
    previous_copy = source_profile.joinpath(".tmp", "previous-alias")
    previous_copy.mkdir(parents=True)
    previous_copy.joinpath("old.bin").write_bytes(b"old")

    def alias_name(*, noun: bool) -> str:
        assert noun
        return "bright-broker"

    monkeypatch.setattr(temporary_profiles, "randstr", alias_name)

    destination_path = temporary_profiles.copy_browser_profile_to_temporary(browser="chrome", source_path=source_profile)

    assert destination_path == source_profile.joinpath(".tmp", "bright-broker")
    assert destination_path.joinpath("Local State").read_bytes() == b"state"
    assert not destination_path.joinpath(".tmp").exists()
    assert previous_copy.joinpath("old.bin").read_bytes() == b"old"


def test_copy_browser_profile_to_temporary_retries_alias_collision_without_overwriting(monkeypatch: pytest.MonkeyPatch, source_profile: Path) -> None:
    collision_path = source_profile.joinpath(".tmp", "existing-alias")
    collision_path.mkdir(parents=True)
    sentinel_path = collision_path.joinpath("keep.bin")
    sentinel_path.write_bytes(b"keep")
    aliases: Iterator[str] = iter(("existing-alias", "new-alias"))

    def alias_name(*, noun: bool) -> str:
        assert noun
        return next(aliases)

    monkeypatch.setattr(temporary_profiles, "randstr", alias_name)

    destination_path = temporary_profiles.copy_browser_profile_to_temporary(browser="chrome", source_path=source_profile)

    assert destination_path == source_profile.joinpath(".tmp", "new-alias")
    assert sentinel_path.read_bytes() == b"keep"


def test_copy_browser_profile_to_temporary_rolls_back_partial_copy(monkeypatch: pytest.MonkeyPatch, source_profile: Path) -> None:
    def alias_name(*, noun: bool) -> str:
        assert noun
        return "failed-alias"

    def fail_copy(*, source_directory: Path, destination_directory: Path, excluded_root_directory_names: frozenset[str]) -> None:
        del source_directory, excluded_root_directory_names
        destination_directory.joinpath("partial.bin").write_bytes(b"partial")
        raise OSError("copy failed")

    monkeypatch.setattr(temporary_profiles, "randstr", alias_name)
    monkeypatch.setattr(temporary_profiles, "copy_directory_tree_excluding", fail_copy)

    with pytest.raises(RuntimeError, match="copy failed"):
        temporary_profiles.copy_browser_profile_to_temporary(browser="chrome", source_path=source_profile)

    assert not source_profile.joinpath(".tmp", "failed-alias").exists()


def test_copy_browser_profile_to_temporary_rolls_back_directory_creation_interruption(monkeypatch: pytest.MonkeyPatch, source_profile: Path) -> None:
    destination_path = source_profile.joinpath(".tmp", "interrupted-alias")
    original_mkdir = Path.mkdir

    def alias_name(*, noun: bool) -> str:
        assert noun
        return "interrupted-alias"

    def interrupt_after_creation(path: Path, mode: int = 0o777, parents: bool = False, exist_ok: bool = False) -> None:
        original_mkdir(path, mode=mode, parents=parents, exist_ok=exist_ok)
        if path == destination_path:
            raise KeyboardInterrupt

    monkeypatch.setattr(temporary_profiles, "randstr", alias_name)
    monkeypatch.setattr(Path, "mkdir", interrupt_after_creation)

    with pytest.raises(KeyboardInterrupt):
        temporary_profiles.copy_browser_profile_to_temporary(browser="chrome", source_path=source_profile)

    assert not destination_path.exists()


def test_copy_browser_profile_to_temporary_rejects_mounted_temporary_root(monkeypatch: pytest.MonkeyPatch, source_profile: Path) -> None:
    temporary_root = source_profile.joinpath(".tmp")
    temporary_root.mkdir()

    def selected_path_is_boundary(*, path: Path) -> bool:
        return path == temporary_root

    monkeypatch.setattr(temporary_profiles, "path_is_filesystem_boundary", selected_path_is_boundary)

    with pytest.raises(ValueError, match="filesystem boundary"):
        temporary_profiles.copy_browser_profile_to_temporary(browser="chrome", source_path=source_profile)

    assert tuple(temporary_root.iterdir()) == ()


def test_copy_browser_profile_to_temporary_rejects_symlinked_temporary_root(
    monkeypatch: pytest.MonkeyPatch, source_profile: Path, tmp_path: Path
) -> None:
    external_path = tmp_path.joinpath("external")
    external_path.mkdir()
    temporary_root = source_profile.joinpath(".tmp")
    try:
        temporary_root.symlink_to(external_path, target_is_directory=True)
    except OSError:
        temporary_root.mkdir()
        original_is_symlink = Path.is_symlink

        def selected_path_is_symlink(path: Path) -> bool:
            return path == temporary_root or original_is_symlink(path)

        monkeypatch.setattr(Path, "is_symlink", selected_path_is_symlink)

    with pytest.raises(ValueError, match="regular directory"):
        temporary_profiles.copy_browser_profile_to_temporary(browser="chrome", source_path=source_profile)

    assert tuple(external_path.iterdir()) == ()
