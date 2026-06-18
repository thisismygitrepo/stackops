import errno
from pathlib import Path

import pytest

from stackops.utils.installer_utils import installer_locator_utils


def test_find_move_delete_linux_does_not_fail_install_when_cleanup_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    install_dir = tmp_path / "bin"
    extracted_dir = tmp_path / "yazi-x86_64-unknown-linux-musl"
    nested_dir = extracted_dir / "yazi-x86_64-unknown-linux-musl"
    nested_dir.mkdir(parents=True)
    executable = nested_dir / "yazi"
    executable.write_text("#!/bin/sh\n", encoding="utf-8")
    executable.chmod(0o755)
    (nested_dir / "README.md").write_text("temporary archive content\n", encoding="utf-8")

    def fail_cleanup(_path: Path, *, verbose: bool) -> None:
        _ = verbose
        raise OSError(errno.ENOTEMPTY, "Directory not empty", str(nested_dir))

    monkeypatch.setattr(installer_locator_utils, "LINUX_INSTALL_PATH", str(install_dir))
    monkeypatch.setattr(installer_locator_utils, "delete_path", fail_cleanup)

    installed_path = installer_locator_utils.find_move_delete_linux(
        downloaded=extracted_dir,
        tool_name="yazi",
        delete=True,
        rename_to="yazi",
    )

    assert installed_path == install_dir / "yazi"
    assert installed_path.is_file()
