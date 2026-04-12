from __future__ import annotations

import subprocess

from machineconfig.scripts.python.helpers.helpers_network.ssh import ssh_debug_darwin_utils as target


def test_run_cmd_returns_false_when_binary_missing(monkeypatch: object) -> None:
    def fake_run(_cmd: list[str], *, capture_output: bool, text: bool, check: bool) -> subprocess.CompletedProcess[str]:
        _ = (capture_output, text, check)
        raise FileNotFoundError

    monkeypatch.setattr(target.subprocess, "run", fake_run)

    assert target.run_cmd(["missing-command"]) == (False, "")


def test_check_sshd_installed_prefers_known_path(monkeypatch: object) -> None:
    existing_paths = {"/opt/homebrew/sbin/sshd"}

    class FakePath:
        def __init__(self, value: str) -> None:
            self.value = value

        def exists(self) -> bool:
            return self.value in existing_paths

    monkeypatch.setattr(target, "Path", FakePath)

    assert target.check_sshd_installed() == (True, "/opt/homebrew/sbin/sshd")


def test_check_sshd_installed_falls_back_to_which(monkeypatch: object) -> None:
    class FakePath:
        def __init__(self, value: str) -> None:
            self.value = value

        def exists(self) -> bool:
            return False

    monkeypatch.setattr(target, "Path", FakePath)
    monkeypatch.setattr(target, "run_cmd", lambda _cmd: (True, "/custom/bin/sshd"))

    assert target.check_sshd_installed() == (True, "/custom/bin/sshd")
