from __future__ import annotations

import json
import subprocess

import pytest

from machineconfig.scripts.python.helpers.helpers_devops.mount_helpers import windows as windows_module
from machineconfig.scripts.python.helpers.helpers_devops.mount_helpers.device_entry import DeviceEntry


def test_normalize_ps_json_handles_blank_dict_and_filtered_list() -> None:
    assert windows_module._normalize_ps_json("") == []
    assert windows_module._normalize_ps_json("""{"DiskNumber": 1}""") == [{"DiskNumber": 1}]
    assert windows_module._normalize_ps_json("""[{"DiskNumber": 1}, 2, "x"]""") == [{"DiskNumber": 1}]


def test_list_windows_devices_combines_partition_and_volume_data(monkeypatch: pytest.MonkeyPatch) -> None:
    partition_json = json.dumps(
        [
            {"DiskNumber": 1, "PartitionNumber": 2, "DriveLetter": "d", "Size": 2048, "Type": "Basic", "Guid": "vol-guid"},
            {"DiskNumber": 3, "PartitionNumber": 4, "DriveLetter": "", "Size": 512, "Type": "Reserved"},
        ]
    )
    volume_json = json.dumps([{"DriveLetter": "D", "FileSystemLabel": "DATA", "FileSystem": "NTFS", "Path": None}])
    commands: list[str] = []

    def fake_run_powershell(command: str) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(args=["powershell"], returncode=0, stdout="", stderr="")

    def fake_ensure_ok(result: subprocess.CompletedProcess[str], context: str) -> str:
        _ = result
        if context == "Get-Partition":
            return partition_json
        if context == "Get-Volume":
            return volume_json
        raise AssertionError(f"Unexpected context: {context}")

    monkeypatch.setattr(windows_module, "run_powershell", fake_run_powershell)
    monkeypatch.setattr(windows_module, "ensure_ok", fake_ensure_ok)

    entries = windows_module.list_windows_devices()

    assert commands == [
        "Get-Partition | Select-Object DiskNumber,PartitionNumber,DriveLetter,Size,Type,Guid | ConvertTo-Json",
        "Get-Volume | Select-Object DriveLetter,FileSystemLabel,FileSystem,Size,SizeRemaining,DriveType,Path | ConvertTo-Json",
    ]
    assert entries == [
        DeviceEntry(
            platform_name="Windows",
            key="Disk 1 Part 2",
            device_path="vol-guid",
            device_type="part",
            label="DATA",
            mount_point="D:\\",
            fs_type="NTFS",
            size="2.0 KB",
            extra="Basic",
            disk_number=1,
            partition_number=2,
            drive_letter="D",
        ),
        DeviceEntry(
            platform_name="Windows",
            key="Disk 3 Part 4",
            device_path="Disk 3 Part 4",
            device_type="part",
            label=None,
            mount_point=None,
            fs_type=None,
            size="512 B",
            extra="Reserved",
            disk_number=3,
            partition_number=4,
            drive_letter=None,
        ),
    ]


def test_mount_windows_validates_partition_details_and_builds_command(monkeypatch: pytest.MonkeyPatch) -> None:
    missing_partition_entry = DeviceEntry(
        platform_name="Windows",
        key="Disk 1 Part 1",
        device_path="path",
        device_type="part",
        label=None,
        mount_point=None,
        fs_type=None,
        size=None,
        extra=None,
        disk_number=None,
        partition_number=1,
        drive_letter=None,
    )
    with pytest.raises(RuntimeError, match="Partition details not available"):
        windows_module.mount_windows(missing_partition_entry, "Z:")

    called_commands: list[str] = []
    called_contexts: list[str] = []

    def fake_run_powershell(command: str) -> subprocess.CompletedProcess[str]:
        called_commands.append(command)
        return subprocess.CompletedProcess(args=["powershell"], returncode=0, stdout="", stderr="")

    def fake_ensure_ok(result: subprocess.CompletedProcess[str], context: str) -> str:
        _ = result
        called_contexts.append(context)
        return ""

    monkeypatch.setattr(windows_module, "run_powershell", fake_run_powershell)
    monkeypatch.setattr(windows_module, "ensure_ok", fake_ensure_ok)

    entry = DeviceEntry(
        platform_name="Windows",
        key="Disk 7 Part 3",
        device_path="path",
        device_type="part",
        label=None,
        mount_point=None,
        fs_type=None,
        size=None,
        extra=None,
        disk_number=7,
        partition_number=3,
        drive_letter=None,
    )

    windows_module.mount_windows(entry, "z:\\mounted")

    assert called_commands == ["Get-Partition -DiskNumber 7 -PartitionNumber 3 | Set-Partition -NewDriveLetter Z"]
    assert called_contexts == ["Set-Partition"]

    with pytest.raises(RuntimeError, match="Invalid drive letter"):
        windows_module.mount_windows(entry, "123")
