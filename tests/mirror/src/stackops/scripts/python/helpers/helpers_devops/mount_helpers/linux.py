from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_devops.mount_helpers.device_entry import DeviceEntry
from stackops.scripts.python.helpers.helpers_devops.mount_helpers import linux as module_under_test


def make_completed_process(args: list[str], *, returncode: int, stdout: str, stderr: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=args, returncode=returncode, stdout=stdout, stderr=stderr)


def make_entry(key: str, *, device_type: str, fs_type: str | None, mount_point: str | None) -> DeviceEntry:
    return DeviceEntry(
        platform_name="Linux",
        key=key,
        device_path=f"/dev/{key}",
        device_type=device_type,
        label=None,
        mount_point=mount_point,
        fs_type=fs_type,
        size=None,
        extra=None,
        disk_number=None,
        partition_number=None,
        drive_letter=None,
    )


def test_flatten_lsblk_devices_keeps_breadth_first_order() -> None:
    flattened = module_under_test._flatten_lsblk_devices(
        devices=[{"name": "sda", "children": [{"name": "sda1", "children": [{"name": "cryptroot"}]}, {"name": "sda2"}]}]
    )

    assert [item["name"] for item in flattened] == ["sda", "sda1", "sda2", "cryptroot"]


def test_list_linux_devices_parses_lsblk_json_and_filters_unsupported_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    lsblk_data = {
        "blockdevices": [
            {
                "name": "sda",
                "type": "disk",
                "size": "1T",
                "fstype": "",
                "label": "",
                "mountpoint": "",
                "model": "FastDisk",
                "children": [
                    {"name": "sda1", "type": "part", "size": "100G", "fstype": "ext4", "label": "root", "mountpoint": "/", "model": ""},
                    {"name": "loop0", "type": "loop"},
                ],
            },
            {"name": 7, "type": "disk"},
        ]
    }

    monkeypatch.setattr(
        module_under_test, "run_command", lambda _command: make_completed_process(["lsblk"], returncode=0, stdout=json.dumps(lsblk_data), stderr="")
    )

    entries = module_under_test.list_linux_devices()

    assert entries == [
        DeviceEntry(
            platform_name="Linux",
            key="sda",
            device_path="/dev/sda",
            device_type="disk",
            label=None,
            mount_point=None,
            fs_type=None,
            size="1T",
            extra="FastDisk",
            disk_number=None,
            partition_number=None,
            drive_letter=None,
        ),
        DeviceEntry(
            platform_name="Linux",
            key="sda1",
            device_path="/dev/sda1",
            device_type="part",
            label="root",
            mount_point="/",
            fs_type="ext4",
            size="100G",
            extra=None,
            disk_number=None,
            partition_number=None,
            drive_letter=None,
        ),
    ]


def test_find_crypt_device_returns_matching_mapper(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        module_under_test,
        "run_command",
        lambda _command: make_completed_process(
            ["lsblk"], returncode=0, stdout=("/dev/nvme0n1 disk -\n/dev/nvme0n1p3 part nvme0n1\n/dev/mapper/secret crypt nvme0n1p3\n"), stderr=""
        ),
    )

    mapped = module_under_test._find_crypt_device(part_name="nvme0n1p3")

    assert mapped == "/dev/mapper/secret"


def test_mount_udisksctl_linux_returns_when_mapper_is_already_mounted(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    calls: list[list[str]] = []

    def fake_run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if command == ["findmnt", "-rn", "/dev/mapper/clear"]:
            return make_completed_process(command, returncode=0, stdout="", stderr="")
        if command == ["findmnt", "-nro", "TARGET", "/dev/mapper/clear"]:
            return make_completed_process(command, returncode=0, stdout="/media/clear\n", stderr="")
        raise AssertionError(f"Unexpected command: {command}")

    monkeypatch.setattr(module_under_test, "_find_crypt_device", lambda _part_name: "/dev/mapper/clear")
    monkeypatch.setattr(module_under_test, "run_command", fake_run_command)

    module_under_test._mount_udisksctl_linux(device_path="/dev/sdb1", read_only=False)

    captured = capsys.readouterr()
    assert "Already mounted: /dev/mapper/clear at /media/clear" in captured.out
    assert calls == [["findmnt", "-rn", "/dev/mapper/clear"], ["findmnt", "-nro", "TARGET", "/dev/mapper/clear"]]


def test_mount_linux_falls_back_to_bitlocker_on_mount_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    entry = make_entry("sdb1", device_type="part", fs_type="ntfs", mount_point=None)
    bitlocker_calls: list[tuple[str, str, bool]] = []

    def fake_mount_bitlocker(device_path: str, mount_point: str, read_only: bool) -> None:
        bitlocker_calls.append((device_path, mount_point, read_only))

    monkeypatch.setattr(module_under_test.os, "geteuid", lambda: 1000)
    monkeypatch.setattr(
        module_under_test,
        "run_command_sudo",
        lambda command: make_completed_process(command, returncode=1, stdout="", stderr="BitLocker signature found"),
    )
    monkeypatch.setattr(module_under_test, "_mount_bitlocker_linux", fake_mount_bitlocker)

    mount_point = tmp_path.joinpath("mnt")
    module_under_test.mount_linux(entry=entry, mount_point=str(mount_point), read_only=True, backend="mount")

    assert mount_point.is_dir()
    assert bitlocker_calls == [(entry.device_path, str(mount_point), True)]


def test_select_linux_partition_prefers_partition_with_filesystem() -> None:
    disk = make_entry("nvme0n1", device_type="disk", fs_type=None, mount_point=None)
    plain_partition = make_entry("nvme0n1p1", device_type="part", fs_type=None, mount_point=None)
    fs_partition = make_entry("nvme0n1p2", device_type="part", fs_type="ext4", mount_point=None)

    selected = module_under_test.select_linux_partition(entries=[disk, plain_partition, fs_partition], entry=disk)

    assert selected == fs_partition


def test_select_linux_partition_raises_when_disk_has_no_mountable_partitions() -> None:
    disk = make_entry("sdc", device_type="disk", fs_type=None, mount_point=None)

    with pytest.raises(RuntimeError, match="No mountable partitions found"):
        module_under_test.select_linux_partition(entries=[disk], entry=disk)
