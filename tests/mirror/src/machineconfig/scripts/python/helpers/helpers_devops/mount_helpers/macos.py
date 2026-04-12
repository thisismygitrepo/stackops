from __future__ import annotations

import plistlib
import subprocess
from pathlib import Path

import pytest

from machineconfig.scripts.python.helpers.helpers_devops.mount_helpers.device_entry import DeviceEntry
from machineconfig.scripts.python.helpers.helpers_devops.mount_helpers import macos as module_under_test


def make_completed_process(args: list[str], *, returncode: int, stdout: str, stderr: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=args, returncode=returncode, stdout=stdout, stderr=stderr)


def plist_text(data: dict[str, object]) -> str:
    return plistlib.dumps(data).decode("utf-8")


def make_entry(key: str) -> DeviceEntry:
    return DeviceEntry(
        platform_name="Darwin",
        key=key,
        device_path=f"/dev/{key}",
        device_type="part",
        label=None,
        mount_point=None,
        fs_type=None,
        size=None,
        extra=None,
        disk_number=None,
        partition_number=None,
        drive_letter=None,
    )


def test_diskutil_info_decodes_plist(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = {"VolumeName": "Data", "TotalSize": 1024}

    monkeypatch.setattr(
        module_under_test, "run_command", lambda command: make_completed_process(command, returncode=0, stdout=plist_text(expected), stderr="")
    )

    returned = module_under_test._diskutil_info(identifier="disk3s1")

    assert returned == expected


def test_list_macos_devices_parses_partitions_and_whole_disks(monkeypatch: pytest.MonkeyPatch) -> None:
    list_data = {
        "AllDisksAndPartitions": [{"DeviceIdentifier": "disk3", "Partitions": [{"DeviceIdentifier": "disk3s1"}]}, {"DeviceIdentifier": "disk4"}]
    }
    info_by_identifier: dict[str, dict[str, object]] = {
        "disk3s1": {"VolumeName": "Data", "FileSystemType": "apfs", "TotalSize": 2048, "MediaName": "SSD Partition", "MountPoint": "/Volumes/Data"},
        "disk4": {"VolumeName": "External", "FilesystemType": "exfat", "TotalSize": 4096, "MediaName": "USB Disk"},
    }

    def fake_run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        if command == ["diskutil", "list", "-plist"]:
            return make_completed_process(command, returncode=0, stdout=plist_text(list_data), stderr="")
        identifier = command[-1]
        return make_completed_process(command, returncode=0, stdout=plist_text(info_by_identifier[identifier]), stderr="")

    monkeypatch.setattr(module_under_test, "run_command", fake_run_command)

    entries = module_under_test.list_macos_devices()

    assert entries == [
        DeviceEntry(
            platform_name="Darwin",
            key="disk3s1",
            device_path="/dev/disk3s1",
            device_type="part",
            label="Data",
            mount_point="/Volumes/Data",
            fs_type="apfs",
            size="2.0 KB",
            extra="SSD Partition",
            disk_number=None,
            partition_number=None,
            drive_letter=None,
        ),
        DeviceEntry(
            platform_name="Darwin",
            key="disk4",
            device_path="/dev/disk4",
            device_type="disk",
            label="External",
            mount_point=None,
            fs_type="exfat",
            size="4.0 KB",
            extra="USB Disk",
            disk_number=None,
            partition_number=None,
            drive_letter=None,
        ),
    ]


def test_mount_macos_uses_default_mount_for_dash(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    monkeypatch.setattr(
        module_under_test, "run_command", lambda command: calls.append(command) or make_completed_process(command, returncode=0, stdout="", stderr="")
    )

    module_under_test.mount_macos(entry=make_entry("disk3s1"), mount_point="-")

    assert calls == [["diskutil", "mount", "disk3s1"]]


def test_mount_macos_creates_explicit_mount_point(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []
    mount_point = tmp_path.joinpath("external")

    monkeypatch.setattr(
        module_under_test, "run_command", lambda command: calls.append(command) or make_completed_process(command, returncode=0, stdout="", stderr="")
    )

    module_under_test.mount_macos(entry=make_entry("disk4"), mount_point=str(mount_point))

    assert mount_point.is_dir()
    assert calls == [["diskutil", "mount", "-mountPoint", str(mount_point), "disk4"]]
