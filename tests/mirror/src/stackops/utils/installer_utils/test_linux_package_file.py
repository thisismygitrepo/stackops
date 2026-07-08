from pathlib import Path
import subprocess

import pytest

from stackops.utils.installer_utils import linux_package_file
from stackops.utils.installer_utils.linux_package_manager import LinuxDistribution, LinuxPackageManager


@pytest.mark.parametrize(
    ("package_manager", "package_name", "expected_command"),
    [
        ("apt", "tool.deb", ("sudo", "apt-get", "install", "-y", "/tmp/tool.deb")),
        ("dnf", "tool.rpm", ("sudo", "dnf", "install", "-y", "/tmp/tool.rpm")),
        ("pacman", "tool.pkg.tar.zst", ("sudo", "pacman", "-U", "--needed", "--noconfirm", "/tmp/tool.pkg.tar.zst")),
    ],
)
def test_builds_native_package_file_command(package_manager: LinuxPackageManager, package_name: str, expected_command: tuple[str, ...]) -> None:
    command = linux_package_file.build_linux_package_file_install_command(
        package_manager=package_manager, package_path=Path("/tmp").joinpath(package_name), privilege_prefix=("sudo",)
    )

    assert command == expected_command


@pytest.mark.parametrize(
    ("package_manager", "package_name"),
    [
        ("apt", "tool.rpm"),
        ("apt", "tool.pkg.tar.zst"),
        ("dnf", "tool.deb"),
        ("dnf", "tool.pkg.tar.zst"),
        ("pacman", "tool.deb"),
        ("pacman", "tool.rpm"),
    ],
)
def test_rejects_package_from_another_ecosystem(package_manager: LinuxPackageManager, package_name: str) -> None:
    with pytest.raises(linux_package_file.IncompatibleLinuxPackageError):
        linux_package_file.build_linux_package_file_install_command(
            package_manager=package_manager, package_path=Path(package_name), privilege_prefix=()
        )


@pytest.mark.parametrize(("package_name", "expected_is_package"), [("tool.pkg.tar.zst", True), ("tool.PKG.TAR.ZST", True), ("tool.tar.zst", False)])
def test_recognizes_only_complete_linux_package_suffixes(package_name: str, expected_is_package: bool) -> None:
    assert linux_package_file.is_linux_package_file(Path(package_name)) is expected_is_package


def test_installs_matching_pacman_package_and_removes_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    package_path = tmp_path.joinpath("tool.pkg.tar.zst")
    package_path.touch()
    commands: list[tuple[str, ...]] = []
    monkeypatch.setattr(linux_package_file, "detect_current_linux_distribution", lambda: LinuxDistribution(distribution_id="arch"))
    monkeypatch.setattr(linux_package_file.os, "geteuid", lambda: 0)

    def run_command(command: tuple[str, ...], *, capture_output: bool, text: bool, check: bool) -> subprocess.CompletedProcess[str]:
        _ = capture_output, text, check
        commands.append(command)
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(linux_package_file.subprocess, "run", run_command)

    linux_package_file.install_linux_package_file(package_path)

    assert commands == [("pacman", "-U", "--needed", "--noconfirm", str(package_path))]
    assert not package_path.exists()


def test_failed_install_preserves_package_for_diagnosis(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    package_path = tmp_path.joinpath("tool.deb")
    package_path.touch()
    monkeypatch.setattr(linux_package_file, "detect_current_linux_distribution", lambda: LinuxDistribution(distribution_id="debian"))
    monkeypatch.setattr(linux_package_file.os, "geteuid", lambda: 0)
    monkeypatch.setattr(
        linux_package_file.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(args=("apt-get",), returncode=1, stdout="", stderr="broken package"),
    )

    with pytest.raises(RuntimeError, match="broken package"):
        linux_package_file.install_linux_package_file(package_path)

    assert package_path.exists()
