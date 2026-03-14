from pathlib import Path
from unittest.mock import patch

from machineconfig.utils.installer_utils import installer_locator_utils


def test_check_tool_exists_windows_uses_path_lookup() -> None:
    with (
        patch.object(installer_locator_utils.platform, "system", return_value="Windows"),
        patch.object(installer_locator_utils.Path, "home", return_value=Path("/tmp/fake-home")),
        patch.object(installer_locator_utils, "WINDOWS_INSTALL_PATH", "/tmp/fake-windows-apps"),
        patch.object(installer_locator_utils.shutil, "which", side_effect=lambda name: "C:/Program Files/Git/cmd/git.exe" if name == "git" else None),
    ):
        assert installer_locator_utils.check_tool_exists("git") is True


def test_check_tool_exists_windows_returns_false_when_missing_everywhere() -> None:
    with (
        patch.object(installer_locator_utils.platform, "system", return_value="Windows"),
        patch.object(installer_locator_utils.Path, "home", return_value=Path("/tmp/fake-home")),
        patch.object(installer_locator_utils, "WINDOWS_INSTALL_PATH", "/tmp/fake-windows-apps"),
        patch.object(installer_locator_utils.shutil, "which", return_value=None),
    ):
        assert installer_locator_utils.check_tool_exists("git") is False
