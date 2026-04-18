from __future__ import annotations

import subprocess

import pytest

from stackops.scripts.python.helpers.helpers_network.ssh import ssh_debug_windows_utils as target


def test_run_powershell_returns_status_and_stripped_output(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(_cmd: list[str], *, capture_output: bool, text: bool, check: bool) -> subprocess.CompletedProcess[str]:
        _ = (capture_output, text, check)
        return subprocess.CompletedProcess(args=["powershell"], returncode=0, stdout=" ready \n", stderr="")

    monkeypatch.setattr(target.subprocess, "run", fake_run)

    assert target.run_powershell("Write-Output ready") == (True, "ready")


def test_check_sshd_binary_exists_falls_back_to_get_command(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakePath:
        def __init__(self, value: str) -> None:
            self.value = value

        def exists(self) -> bool:
            return False

        def __str__(self) -> str:
            return self.value

    monkeypatch.setattr(target, "Path", FakePath)
    monkeypatch.setattr(target, "run_powershell", lambda _cmd: (True, "C:/Custom/OpenSSH/sshd.exe"))

    assert target.check_sshd_binary_exists() == (True, "C:/Custom/OpenSSH/sshd.exe")


def test_detect_openssh_reports_capability_install(monkeypatch: pytest.MonkeyPatch) -> None:
    existing_paths = {"C:/Windows/System32/OpenSSH/sshd.exe", "C:/ProgramData/ssh"}

    class FakePath:
        def __init__(self, value: str) -> None:
            self.value = value

        def exists(self) -> bool:
            return self.value in existing_paths

        def __eq__(self, other: object) -> bool:
            return isinstance(other, FakePath) and self.value == other.value

        def __str__(self) -> str:
            return self.value

    monkeypatch.setattr(target, "Path", FakePath)

    install_type, sshd_path, config_dir = target.detect_openssh()

    assert install_type == "capability"
    assert sshd_path == FakePath("C:/Windows/System32/OpenSSH/sshd.exe")
    assert config_dir == FakePath("C:/ProgramData/ssh")


def test_detect_openssh_reports_missing_install(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakePath:
        def __init__(self, value: str) -> None:
            self.value = value

        def exists(self) -> bool:
            return False

    monkeypatch.setattr(target, "Path", FakePath)

    assert target.detect_openssh() == ("not_found", None, None)
