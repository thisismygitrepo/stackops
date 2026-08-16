from contextlib import nullcontext
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_browser_profiles as profiles
from stackops.scripts.python.helpers.helpers_agents import agents_browser_resolution
from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BrowserName


@pytest.fixture
def profiles_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    root = tmp_path.joinpath("browsers-profiles")
    root.mkdir()

    def no_browser_processes(*, browser: BrowserName) -> tuple[int, ...]:
        del browser
        return ()

    monkeypatch.setattr(agents_browser_resolution, "BROWSER_PROFILES_ROOT", root)
    monkeypatch.setattr(profiles, "find_browser_process_ids", no_browser_processes)
    monkeypatch.setattr(profiles, "browser_launch_lock", nullcontext)
    return root


def _create_profile(*, profiles_root: Path, browser: BrowserName, name: str = "base") -> Path:
    profile_path = profiles_root.joinpath(browser, name)
    profile_path.mkdir(parents=True)
    return profile_path


def _write_sized_file(path: Path, size: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    return path


@pytest.mark.parametrize("browser", ["chrome", "brave", "edge"])
def test_declutter_chromium_removes_only_cache_data_and_reports_recovered_bytes(browser: BrowserName, profiles_root: Path) -> None:
    profile_path = _create_profile(profiles_root=profiles_root, browser=browser)
    removed_files = {
        _write_sized_file(profile_path.joinpath("OptGuideOnDeviceModel", "model.bin"), 101),
        _write_sized_file(profile_path.joinpath("ShaderCache", "cache.bin"), 11),
        _write_sized_file(profile_path.joinpath("Default", "Cache", "http.bin"), 23),
        _write_sized_file(profile_path.joinpath("Profile 1", "Code Cache", "code.bin"), 37),
    }
    persistent_files = {
        _write_sized_file(profile_path.joinpath("Local State"), 5),
        _write_sized_file(profile_path.joinpath("Default", "Cookies"), 7),
        _write_sized_file(profile_path.joinpath("Default", "History"), 13),
        _write_sized_file(profile_path.joinpath("Default", "Preferences"), 17),
        _write_sized_file(profile_path.joinpath("Default", "Service Worker", "CacheStorage", "data.bin"), 19),
    }

    result = profiles.declutter_browser_profile(browser=browser, profile_name="base")

    removed_bytes = 101 + 11 + 23 + 37
    persistent_bytes = 5 + 7 + 13 + 17 + 19
    assert result.profile_path == profile_path
    assert result.size_before_bytes == removed_bytes + persistent_bytes
    assert result.size_after_bytes == persistent_bytes
    assert result.recovered_bytes == removed_bytes
    assert {path.relative_to(profile_path).as_posix() for path in result.removed_paths} == {
        "OptGuideOnDeviceModel",
        "ShaderCache",
        "Default/Cache",
        "Profile 1/Code Cache",
    }
    assert all(not path.exists() for path in removed_files)
    assert all(path.is_file() for path in persistent_files)


def test_declutter_firefox_uses_its_cache_allowlist(profiles_root: Path) -> None:
    profile_path = _create_profile(profiles_root=profiles_root, browser="firefox")
    removed_files = {
        _write_sized_file(profile_path.joinpath("cache2", "entries", "cache.bin"), 13),
        _write_sized_file(profile_path.joinpath("shader-cache", "shader.bin"), 17),
        _write_sized_file(profile_path.joinpath("startupCache", "startup.bin"), 19),
    }
    persistent_files = {
        _write_sized_file(profile_path.joinpath("cookies.sqlite"), 23),
        _write_sized_file(profile_path.joinpath("storage", "default", "site", "idb", "data.bin"), 29),
    }

    result = profiles.declutter_browser_profile(browser="firefox", profile_name="base")

    assert {path.relative_to(profile_path).as_posix() for path in result.removed_paths} == {"cache2", "shader-cache", "startupCache"}
    assert result.recovered_bytes == 13 + 17 + 19
    assert all(not path.exists() for path in removed_files)
    assert all(path.is_file() for path in persistent_files)


def test_declutter_refuses_to_change_a_profile_while_browser_is_running(monkeypatch: pytest.MonkeyPatch, profiles_root: Path) -> None:
    profile_path = _create_profile(profiles_root=profiles_root, browser="chrome")
    cache_file = _write_sized_file(profile_path.joinpath("Cache", "data.bin"), 8)

    def running_browser_processes(*, browser: BrowserName) -> tuple[int, ...]:
        assert browser == "chrome"
        return (101, 202)

    monkeypatch.setattr(profiles, "find_browser_process_ids", running_browser_processes)

    with pytest.raises(RuntimeError, match=r"101, 202"):
        profiles.declutter_browser_profile(browser="chrome", profile_name="base")

    assert cache_file.is_file()


def test_declutter_refuses_nested_mount_before_removing_anything(monkeypatch: pytest.MonkeyPatch, profiles_root: Path) -> None:
    profile_path = _create_profile(profiles_root=profiles_root, browser="chrome")
    model_file = _write_sized_file(profile_path.joinpath("OptGuideOnDeviceModel", "model.bin"), 8)
    mounted_directory = profile_path.joinpath("Default", "Cache", "external")
    cache_file = _write_sized_file(mounted_directory.joinpath("cache.bin"), 13)
    original_is_mount = Path.is_mount

    def selected_directory_is_mount(path: Path) -> bool:
        return path == mounted_directory or original_is_mount(path)

    monkeypatch.setattr(Path, "is_mount", selected_directory_is_mount)

    with pytest.raises(RuntimeError, match="refuses filesystem boundary"):
        profiles.declutter_browser_profile(browser="chrome", profile_name="base")

    assert model_file.is_file()
    assert cache_file.is_file()


def test_replicate_creates_p1_through_pn_from_the_base_profile(profiles_root: Path) -> None:
    source_path = _create_profile(profiles_root=profiles_root, browser="chrome")
    _write_sized_file(source_path.joinpath("Local State"), 8)
    _write_sized_file(source_path.joinpath("Default", "Cookies"), 13)

    result = profiles.replicate_browser_profile(browser="chrome", profile_name="base", count=3)

    expected_destinations = tuple(profiles_root.joinpath("chrome", f"p{index}") for index in range(1, 4))
    assert result.source_path == source_path
    assert result.destination_paths == expected_destinations
    assert result.source_size_bytes == 21
    for destination_path in expected_destinations:
        assert destination_path.joinpath("Local State").read_bytes() == b"x" * 8
        assert destination_path.joinpath("Default", "Cookies").read_bytes() == b"x" * 13


def test_replicate_preflights_all_destination_collisions(profiles_root: Path) -> None:
    source_path = _create_profile(profiles_root=profiles_root, browser="chrome")
    _write_sized_file(source_path.joinpath("Local State"), 8)
    collision_path = _create_profile(profiles_root=profiles_root, browser="chrome", name="p2")
    sentinel_path = _write_sized_file(collision_path.joinpath("keep.bin"), 5)

    with pytest.raises(ValueError, match=r"p2"):
        profiles.replicate_browser_profile(browser="chrome", profile_name="base", count=3)

    assert not profiles_root.joinpath("chrome", "p1").exists()
    assert sentinel_path.is_file()
    assert not profiles_root.joinpath("chrome", "p3").exists()


def test_replicate_does_not_remove_destination_created_after_preflight(monkeypatch: pytest.MonkeyPatch, profiles_root: Path) -> None:
    source_path = _create_profile(profiles_root=profiles_root, browser="chrome")
    _write_sized_file(source_path.joinpath("Local State"), 8)
    collision_path = profiles_root.joinpath("chrome", "p2")
    sentinel_path = collision_path.joinpath("keep.bin")
    original_mkdir = Path.mkdir

    def create_p2_before_reservation(path: Path, mode: int = 0o777, parents: bool = False, exist_ok: bool = False) -> None:
        if path == collision_path and not path.exists():
            original_mkdir(path, mode=mode, parents=parents, exist_ok=exist_ok)
            sentinel_path.write_bytes(b"keep")
        original_mkdir(path, mode=mode, parents=parents, exist_ok=exist_ok)

    monkeypatch.setattr(Path, "mkdir", create_p2_before_reservation)

    with pytest.raises(RuntimeError, match="Could not replicate browser profile"):
        profiles.replicate_browser_profile(browser="chrome", profile_name="base", count=3)

    assert not profiles_root.joinpath("chrome", "p1").exists()
    assert sentinel_path.read_bytes() == b"keep"
    assert not profiles_root.joinpath("chrome", "p3").exists()


def test_replicate_rolls_back_all_reserved_destinations_after_partial_copy_failure(monkeypatch: pytest.MonkeyPatch, profiles_root: Path) -> None:
    source_path = _create_profile(profiles_root=profiles_root, browser="chrome")
    _write_sized_file(source_path.joinpath("Local State"), 8)
    original_copytree = profiles.shutil.copytree

    def fail_on_p2(source: Path, destination: Path, *, symlinks: bool, dirs_exist_ok: bool) -> Path:
        if destination.name == "p2":
            destination.joinpath("partial.bin").write_bytes(b"partial")
            raise OSError("copy failed")
        return original_copytree(source, destination, symlinks=symlinks, dirs_exist_ok=dirs_exist_ok)

    monkeypatch.setattr(profiles.shutil, "copytree", fail_on_p2)

    with pytest.raises(RuntimeError, match="copy failed"):
        profiles.replicate_browser_profile(browser="chrome", profile_name="base", count=3)

    assert all(not profiles_root.joinpath("chrome", f"p{index}").exists() for index in range(1, 4))


def test_replicate_rolls_back_all_reserved_destinations_after_interruption(monkeypatch: pytest.MonkeyPatch, profiles_root: Path) -> None:
    source_path = _create_profile(profiles_root=profiles_root, browser="chrome")
    _write_sized_file(source_path.joinpath("Local State"), 8)

    def interrupt_copy(source: Path, destination: Path, *, symlinks: bool, dirs_exist_ok: bool) -> Path:
        del source, symlinks, dirs_exist_ok
        destination.joinpath("partial.bin").write_bytes(b"partial")
        raise KeyboardInterrupt

    monkeypatch.setattr(profiles.shutil, "copytree", interrupt_copy)

    with pytest.raises(KeyboardInterrupt):
        profiles.replicate_browser_profile(browser="chrome", profile_name="base", count=2)

    assert all(not profiles_root.joinpath("chrome", f"p{index}").exists() for index in range(1, 3))


def test_replicate_tracks_destination_before_interrupted_directory_creation(monkeypatch: pytest.MonkeyPatch, profiles_root: Path) -> None:
    source_path = _create_profile(profiles_root=profiles_root, browser="chrome")
    _write_sized_file(source_path.joinpath("Local State"), 8)
    destination_path = profiles_root.joinpath("chrome", "p1")
    original_mkdir = Path.mkdir

    def interrupt_after_creation(path: Path, mode: int = 0o777, parents: bool = False, exist_ok: bool = False) -> None:
        original_mkdir(path, mode=mode, parents=parents, exist_ok=exist_ok)
        if path == destination_path:
            raise KeyboardInterrupt

    monkeypatch.setattr(Path, "mkdir", interrupt_after_creation)

    with pytest.raises(KeyboardInterrupt):
        profiles.replicate_browser_profile(browser="chrome", profile_name="base", count=1)

    assert not destination_path.exists()


def test_replicate_refuses_nested_filesystem_boundary(monkeypatch: pytest.MonkeyPatch, profiles_root: Path) -> None:
    source_path = _create_profile(profiles_root=profiles_root, browser="chrome")
    boundary_path = source_path.joinpath("Default", "external")
    _write_sized_file(boundary_path.joinpath("outside.bin"), 8)
    original_is_junction = Path.is_junction

    def selected_directory_is_junction(path: Path) -> bool:
        return path == boundary_path or original_is_junction(path)

    monkeypatch.setattr(Path, "is_junction", selected_directory_is_junction)

    with pytest.raises(RuntimeError, match="refuses filesystem boundary"):
        profiles.replicate_browser_profile(browser="chrome", profile_name="base", count=1)

    assert not profiles_root.joinpath("chrome", "p1").exists()


@pytest.mark.parametrize("count", [0, -1])
def test_replicate_rejects_invalid_count(count: int, profiles_root: Path) -> None:
    del profiles_root
    with pytest.raises(ValueError, match="COUNT must be at least 1"):
        profiles.replicate_browser_profile(browser="chrome", profile_name="base", count=count)


def test_replicate_rejects_missing_source(profiles_root: Path) -> None:
    with pytest.raises(ValueError, match="does not exist or is not a directory"):
        profiles.replicate_browser_profile(browser="chrome", profile_name="missing", count=1)


def test_replicate_rejects_safari_profiles(profiles_root: Path) -> None:
    del profiles_root
    with pytest.raises(ValueError, match="Safari does not support StackOps browser profiles"):
        profiles.replicate_browser_profile(browser="safari", profile_name="base", count=1)


def test_replicate_rejects_symlink_source(profiles_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    actual_profile = tmp_path.joinpath("actual-profile")
    actual_profile.mkdir()
    source_path = profiles_root.joinpath("chrome", "base")
    source_path.parent.mkdir(parents=True)
    try:
        source_path.symlink_to(actual_profile, target_is_directory=True)
    except OSError:
        source_path.mkdir()
        original_is_symlink = Path.is_symlink

        def selected_source_is_symlink(path: Path) -> bool:
            return path == source_path or original_is_symlink(path)

        monkeypatch.setattr(Path, "is_symlink", selected_source_is_symlink)

    with pytest.raises(ValueError, match="must not be a symbolic link"):
        profiles.replicate_browser_profile(browser="chrome", profile_name="base", count=1)
