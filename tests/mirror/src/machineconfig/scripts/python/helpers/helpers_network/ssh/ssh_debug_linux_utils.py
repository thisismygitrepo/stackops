from __future__ import annotations

import subprocess

import pytest

from machineconfig.scripts.python.helpers.helpers_network.ssh import ssh_debug_linux_utils as target


def test_run_cmd_returns_false_when_binary_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(_cmd: list[str], *, capture_output: bool, text: bool, check: bool) -> subprocess.CompletedProcess[str]:
        _ = (capture_output, text, check)
        raise FileNotFoundError

    monkeypatch.setattr(target.subprocess, "run", fake_run)

    assert target.run_cmd(["missing-command"]) == (False, "")


def test_check_sshd_installed_falls_back_to_which(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakePath:
        def __init__(self, value: str) -> None:
            self.value = value

        def exists(self) -> bool:
            return False

    monkeypatch.setattr(target, "Path", FakePath)
    monkeypatch.setattr(target, "run_cmd", lambda _cmd: (True, "/usr/local/bin/sshd"))

    assert target.check_sshd_installed() == (True, "/usr/local/bin/sshd")


def test_detect_package_manager_prefers_apt(monkeypatch: pytest.MonkeyPatch) -> None:
    existing_paths = {"/usr/bin/apt", "/usr/bin/dnf"}

    class FakePath:
        def __init__(self, value: str) -> None:
            self.value = value

        def exists(self) -> bool:
            return self.value in existing_paths

    monkeypatch.setattr(target, "Path", FakePath)

    assert target.detect_package_manager() == ("apt", "sudo apt update && sudo apt install -y openssh-server")


def test_detect_package_manager_returns_unknown_when_none_found(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakePath:
        def __init__(self, value: str) -> None:
            self.value = value

        def exists(self) -> bool:
            return False

    monkeypatch.setattr(target, "Path", FakePath)

    assert target.detect_package_manager() == ("unknown", "# Install openssh-server using your package manager")
