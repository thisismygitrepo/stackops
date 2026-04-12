from __future__ import annotations

import subprocess

import pytest

from machineconfig.scripts.python.helpers.helpers_devops.mount_helpers import commands as module_under_test


def make_completed_process(args: list[str], *, returncode: int, stdout: str, stderr: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=args, returncode=returncode, stdout=stdout, stderr=stderr)


def test_run_command_calls_subprocess_with_plain_command(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[list[str], bool, bool, bool]] = []
    result = make_completed_process(["echo", "ok"], returncode=0, stdout="ok\n", stderr="")

    def fake_run(command: list[str], *, capture_output: bool, text: bool, check: bool) -> subprocess.CompletedProcess[str]:
        calls.append((command, capture_output, text, check))
        return result

    monkeypatch.setattr(module_under_test.subprocess, "run", fake_run)

    returned = module_under_test.run_command(command=["echo", "ok"])

    assert returned is result
    assert calls == [(["echo", "ok"], True, True, False)]


def test_run_command_sudo_prefixes_sudo(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    result = make_completed_process(["sudo", "mount"], returncode=0, stdout="", stderr="")

    def fake_run(command: list[str], *, capture_output: bool, text: bool, check: bool) -> subprocess.CompletedProcess[str]:
        _ = capture_output
        _ = text
        _ = check
        calls.append(command)
        return result

    monkeypatch.setattr(module_under_test.subprocess, "run", fake_run)

    returned = module_under_test.run_command_sudo(command=["mount", "/dev/sdb1"])

    assert returned is result
    assert calls == [["sudo", "mount", "/dev/sdb1"]]


def test_run_powershell_wraps_command(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    result = make_completed_process(["powershell", "-NoProfile", "-Command", "Get-Volume"], returncode=0, stdout="volume", stderr="")

    def fake_run(command: list[str], *, capture_output: bool, text: bool, check: bool) -> subprocess.CompletedProcess[str]:
        _ = capture_output
        _ = text
        _ = check
        calls.append(command)
        return result

    monkeypatch.setattr(module_under_test.subprocess, "run", fake_run)

    returned = module_under_test.run_powershell(command="Get-Volume")

    assert returned is result
    assert calls == [["powershell", "-NoProfile", "-Command", "Get-Volume"]]


def test_ensure_ok_returns_stdout_on_success() -> None:
    result = make_completed_process(["cmd"], returncode=0, stdout="done\n", stderr="")

    returned = module_under_test.ensure_ok(result=result, context="demo")

    assert returned == "done\n"


@pytest.mark.parametrize(
    ("stderr_value", "stdout_value", "expected_message"),
    [("bad stderr\n", "bad stdout\n", "demo failed: bad stderr"), ("", "bad stdout\n", "demo failed: bad stdout")],
)
def test_ensure_ok_prefers_stderr_then_stdout_for_errors(stderr_value: str, stdout_value: str, expected_message: str) -> None:
    result = make_completed_process(["cmd"], returncode=1, stdout=stdout_value, stderr=stderr_value)

    with pytest.raises(RuntimeError, match=expected_message):
        module_under_test.ensure_ok(result=result, context="demo")
