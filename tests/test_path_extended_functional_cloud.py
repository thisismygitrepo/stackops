# pyright: reportArgumentType=false

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import subprocess
import sys
import types

import pytest

from machineconfig.utils import path_extended as legacy
from machineconfig.utils import path_extended_functional as functional
from machineconfig.utils.path_extended import PathExtended
from tests.path_extended_functional_support import assert_matching_outcomes, capture_call


class FixedCloudDatetime:
    @classmethod
    def fromtimestamp(cls, timestamp: float, tz: object | None = None) -> object:
        _ = timestamp, tz
        return cls()

    def isoformat(self) -> str:
        return "2024-01-02T03:04:05"


def _freeze_cloud_datetime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(legacy, "datetime", FixedCloudDatetime)
    monkeypatch.setattr(functional, "datetime", FixedCloudDatetime)


@dataclass
class FakeResponseObject:
    status_code: int = 200
    text: str = "ok"
    content: bytes = b"payload"
    headers: dict[str, str] = field(default_factory=dict)
    history: list[object] = field(default_factory=list)
    url: str = "https://example.com/files/fallback.txt"


@dataclass
class FakeRclone:
    should_fail: bool = False
    copy_calls: list[tuple[str, str]] = field(default_factory=list)

    def copyto(self, *, in_path: str, out_path: str) -> None:
        self.copy_calls.append((in_path, out_path))
        if self.should_fail:
            raise RuntimeError("copy failed")


class FakeTerminalResponse:
    def __init__(self, completed: subprocess.CompletedProcess[str]) -> None:
        self.completed = completed

    @classmethod
    def from_completed_process(cls, completed: subprocess.CompletedProcess[str]) -> FakeTerminalResponse:
        return cls(completed)

    def capture(self) -> FakeTerminalResponse:
        return self

    def op2path(self, strict_err: bool = False, strict_returncode: bool = False) -> Path | None:
        _ = strict_err, strict_returncode
        stdout_text = self.completed.stdout or ""
        stripped = stdout_text.strip()
        return None if stripped == "" else Path(stripped)

    def print(self, capture: bool = False, desc: str | None = None) -> None:
        _ = capture, desc

    def print_if_unsuccessful(self, desc: str, strict_err: bool, strict_returncode: bool) -> None:
        _ = desc, strict_err, strict_returncode

    def is_successful(self, strict_err: bool = False, strict_returcode: bool = True) -> bool:
        _ = strict_err, strict_returcode
        return self.completed.returncode == 0


def _install_fake_rclone(monkeypatch: pytest.MonkeyPatch, fake_rclone: FakeRclone) -> None:
    monkeypatch.setitem(sys.modules, "rclone_python", types.SimpleNamespace(rclone=fake_rclone))


def test_download_matches_requests_handling(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    downloads_root = tmp_path / "home"
    downloads_root.mkdir()
    monkeypatch.setenv("HOME", downloads_root.as_posix())

    response = FakeResponseObject(headers={"Content-Disposition": 'attachment; filename="named.txt"'}, content=b"from-header")
    import requests

    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: response)

    original = capture_call(lambda: PathExtended("https://example.com/archive").download(folder=tmp_path / "dest"))
    functional_result = capture_call(lambda: functional.download(path="https://example.com/archive", folder=tmp_path / "dest"))
    assert_matching_outcomes(original, functional_result, original_root=tmp_path, functional_root=tmp_path)
    assert (tmp_path / "dest" / "named.txt").read_bytes() == b"from-header"

    fallback_response = FakeResponseObject(
        headers={},
        content=b"from-fallback",
        history=[types.SimpleNamespace(url="https://example.com/dir/result file.txt")],
        url="https://example.com/dir/ignored.txt",
    )
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: fallback_response)
    assert functional.download(path="https://example.com/archive", folder=tmp_path / "other").name == PathExtended("https://example.com/archive").download(folder=tmp_path / "other").name


def test_get_remote_path_matches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home_path = tmp_path / "home"
    home_path.mkdir()
    monkeypatch.setenv("HOME", home_path.as_posix())
    nested = home_path / "docs" / "report.txt"
    nested.parent.mkdir(parents=True)
    nested.write_text("payload", encoding="utf-8")

    assert_matching_outcomes(
        capture_call(lambda: PathExtended(nested).get_remote_path(root="myhome", os_specific=False, rel2home=True)),
        capture_call(lambda: functional.get_remote_path(nested, root="myhome", os_specific=False, rel2home=True)),
    )
    assert_matching_outcomes(
        capture_call(lambda: PathExtended(nested).get_remote_path(root=None, os_specific=True, rel2home=False)),
        capture_call(lambda: functional.get_remote_path(nested, root=None, os_specific=True, rel2home=False)),
    )


def test_to_cloud_matches_copy_cleanup_and_share(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _freeze_cloud_datetime(monkeypatch)
    fake_rclone = FakeRclone()
    _install_fake_rclone(monkeypatch, fake_rclone)
    monkeypatch.setattr(legacy, "_run_shell_command", lambda *args, **kwargs: subprocess.CompletedProcess(args=["rclone"], returncode=0, stdout=(tmp_path / "shared.txt").as_posix(), stderr=""))
    monkeypatch.setattr(functional, "_run_shell_command", lambda *args, **kwargs: subprocess.CompletedProcess(args=["rclone"], returncode=0, stdout=(tmp_path / "shared.txt").as_posix(), stderr=""))
    import machineconfig.utils.terminal as terminal

    monkeypatch.setattr(terminal, "Response", FakeTerminalResponse)

    path = tmp_path / "payload.txt"
    path.write_text("payload", encoding="utf-8")

    original = capture_call(lambda: PathExtended(path).to_cloud("demo", root="root", share=True))
    functional_result = capture_call(lambda: functional.to_cloud(path, "demo", root="root", share=True))
    assert_matching_outcomes(original, functional_result, original_root=tmp_path, functional_root=tmp_path)
    assert fake_rclone.copy_calls[0][1].startswith("demo:root/generic_os/")
    assert fake_rclone.copy_calls[1][1].startswith("demo:root/generic_os/")


def test_from_cloud_matches_success_and_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    success_rclone = FakeRclone()
    _install_fake_rclone(monkeypatch, success_rclone)
    target = tmp_path / "payload.txt"
    target.parent.mkdir(parents=True, exist_ok=True)

    original = capture_call(lambda: PathExtended(target).from_cloud("demo", remotepath=Path("remote.txt")))
    functional_result = capture_call(lambda: functional.from_cloud(target, "demo", remotepath=Path("remote.txt")))
    assert_matching_outcomes(original, functional_result, original_root=tmp_path, functional_root=tmp_path)

    failing_rclone = FakeRclone(should_fail=True)
    _install_fake_rclone(monkeypatch, failing_rclone)
    original_failure = capture_call(lambda: PathExtended(target).from_cloud("demo", remotepath=Path("remote.txt")))
    functional_failure = capture_call(lambda: functional.from_cloud(target, "demo", remotepath=Path("remote.txt")))
    assert_matching_outcomes(original_failure, functional_failure, original_root=tmp_path, functional_root=tmp_path)


def test_sync_to_cloud_matches_command_and_return_value(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _freeze_cloud_datetime(monkeypatch)
    import machineconfig.utils.terminal as terminal

    monkeypatch.setattr(terminal, "Response", FakeTerminalResponse)
    monkeypatch.setattr(legacy, "_run_shell_command", lambda *args, **kwargs: subprocess.CompletedProcess(args=["rclone"], returncode=0, stdout="", stderr=""))
    monkeypatch.setattr(functional, "_run_shell_command", lambda *args, **kwargs: subprocess.CompletedProcess(args=["rclone"], returncode=0, stdout="", stderr=""))
    monkeypatch.setenv("HOME", tmp_path.as_posix())

    path = tmp_path / "folder"

    original = capture_call(lambda: PathExtended(path).sync_to_cloud("demo", sync_up=True, root="root"))
    functional_result = capture_call(lambda: functional.sync_to_cloud(path, "demo", sync_up=True, root="root"))
    assert_matching_outcomes(original, functional_result, original_root=tmp_path, functional_root=tmp_path)
