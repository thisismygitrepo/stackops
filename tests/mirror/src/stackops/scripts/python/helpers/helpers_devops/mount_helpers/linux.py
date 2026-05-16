import subprocess

import pytest

from stackops.scripts.python.helpers.helpers_devops.mount_helpers import linux


def test_mount_udisksctl_linux_returns_when_mapper_is_already_mounted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(linux, "_find_crypt_device", lambda _part_name: "/dev/dm-0")

    def fake_run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        if command == ["findmnt", "-rn", "/dev/dm-0"]:
            return subprocess.CompletedProcess(command, 0, stdout="/dev/dm-0 /media/alex/data\n", stderr="")
        if command == ["findmnt", "-nro", "TARGET", "/dev/dm-0"]:
            return subprocess.CompletedProcess(command, 0, stdout="/media/alex/data\n", stderr="")
        raise AssertionError(f"Unexpected command: {command}")

    def fail_interactive(command: list[str]) -> subprocess.CompletedProcess[str]:
        raise AssertionError(f"Interactive command should not run: {command}")

    monkeypatch.setattr(linux, "run_command", fake_run_command)
    monkeypatch.setattr(linux, "run_command_interactive", fail_interactive)

    linux._mount_udisksctl_linux("/dev/sda1", read_only=True)


def test_mount_udisksctl_linux_unlocks_then_mounts_when_mapper_appears(monkeypatch: pytest.MonkeyPatch) -> None:
    mapper_states = iter([None, None, "/dev/dm-0"])
    interactive_calls: list[list[str]] = []
    sleep_calls: list[float] = []

    monkeypatch.setattr(linux, "_find_crypt_device", lambda _part_name: next(mapper_states))
    monkeypatch.setattr(linux.time, "sleep", lambda delay_seconds: sleep_calls.append(delay_seconds))
    monkeypatch.setattr(
        linux,
        "run_command",
        lambda command: (_ for _ in ()).throw(AssertionError(f"Unexpected non-interactive command: {command}")),
    )

    def fake_run_command_interactive(command: list[str]) -> subprocess.CompletedProcess[str]:
        interactive_calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(linux, "run_command_interactive", fake_run_command_interactive)

    linux._mount_udisksctl_linux("/dev/sda1", read_only=True)

    assert interactive_calls == [
        ["udisksctl", "unlock", "-b", "/dev/sda1", "--read-only"],
        ["udisksctl", "mount", "-b", "/dev/dm-0"],
    ]
    assert sleep_calls == [linux.CRYPT_DEVICE_LOOKUP_DELAY_SECONDS]


def test_mount_udisksctl_linux_raises_when_mapper_never_appears(monkeypatch: pytest.MonkeyPatch) -> None:
    sleep_calls: list[float] = []

    monkeypatch.setattr(linux, "_find_crypt_device", lambda _part_name: None)
    monkeypatch.setattr(linux.time, "sleep", lambda delay_seconds: sleep_calls.append(delay_seconds))
    monkeypatch.setattr(
        linux,
        "run_command",
        lambda command: (_ for _ in ()).throw(AssertionError(f"Unexpected non-interactive command: {command}")),
    )
    monkeypatch.setattr(
        linux,
        "run_command_interactive",
        lambda command: subprocess.CompletedProcess(command, 0, stdout="", stderr=""),
    )

    with pytest.raises(RuntimeError, match="Could not find mapped cleartext device after unlock"):
        linux._mount_udisksctl_linux("/dev/sda1", read_only=False)

    assert sleep_calls == [linux.CRYPT_DEVICE_LOOKUP_DELAY_SECONDS] * (linux.CRYPT_DEVICE_LOOKUP_ATTEMPTS - 1)
