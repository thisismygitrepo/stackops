from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_browser_profile_filesystem as profile_filesystem


def test_linux_mountinfo_rejects_same_filesystem_bind_mount(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    profile_path = tmp_path.joinpath("profile")
    bind_mount_path = profile_path.joinpath("Cache", "mounted data")
    bind_mount_path.mkdir(parents=True)
    encoded_mount_path = str(bind_mount_path).replace(" ", r"\040")
    mount_info = f"42 1 0:1 / {encoded_mount_path} rw - none none rw\n"
    original_read_text = Path.read_text

    def read_mount_info(path: Path, encoding: str | None = None, errors: str | None = None) -> str:
        if path == Path("/proc/self/mountinfo"):
            assert encoding == "utf-8"
            return mount_info
        return original_read_text(path, encoding=encoding, errors=errors)

    monkeypatch.setattr(profile_filesystem.platform, "system", lambda: "Linux")
    monkeypatch.setattr(Path, "read_text", read_mount_info)
    monkeypatch.setattr(Path, "is_mount", lambda _path: False)

    assert profile_filesystem.path_is_filesystem_boundary(path=bind_mount_path) is True
    with pytest.raises(RuntimeError, match="refuses filesystem boundary"):
        profile_filesystem.require_tree_without_filesystem_boundaries(
            directory=profile_path, include_root=False, excluded_root_directory_names=frozenset()
        )


def test_linux_mountinfo_rejects_same_filesystem_file_bind_mount(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    profile_path = tmp_path.joinpath("profile")
    bind_mount_path = profile_path.joinpath("Cache", "mounted file")
    bind_mount_path.parent.mkdir(parents=True)
    bind_mount_path.write_bytes(b"external")
    encoded_mount_path = str(bind_mount_path).replace(" ", r"\040")
    mount_info = f"42 1 0:1 / {encoded_mount_path} rw - none none rw\n"
    original_read_text = Path.read_text

    def read_mount_info(path: Path, encoding: str | None = None, errors: str | None = None) -> str:
        if path == Path("/proc/self/mountinfo"):
            assert encoding == "utf-8"
            return mount_info
        return original_read_text(path, encoding=encoding, errors=errors)

    monkeypatch.setattr(profile_filesystem.platform, "system", lambda: "Linux")
    monkeypatch.setattr(Path, "read_text", read_mount_info)
    monkeypatch.setattr(Path, "is_mount", lambda _path: False)

    with pytest.raises(RuntimeError, match="refuses filesystem boundary"):
        profile_filesystem.require_tree_without_filesystem_boundaries(
            directory=profile_path, include_root=False, excluded_root_directory_names=frozenset()
        )
