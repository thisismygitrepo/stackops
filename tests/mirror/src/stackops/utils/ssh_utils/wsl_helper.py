

from collections.abc import Callable
from pathlib import Path
import subprocess

import pytest

from stackops.utils.ssh_utils import wsl_helper as sut


def _make_path_factory(mappings: dict[str, Path]) -> Callable[..., Path]:
    real_path = Path

    def fake_path(*parts: object) -> Path:
        path_text = str(real_path(*[str(part) for part in parts]))
        mapped = mappings.get(path_text)
        if mapped is not None:
            return mapped
        return real_path(*[str(part) for part in parts])

    return fake_path


def test_ensure_relative_path_accepts_clean_relative_and_rejects_escaping() -> None:
    assert sut.ensure_relative_path("nested/file.txt") == Path("nested/file.txt")

    with pytest.raises(ValueError, match="relative to the home directory"):
        sut.ensure_relative_path("/tmp/file.txt")

    with pytest.raises(ValueError, match="stay within the home directory"):
        sut.ensure_relative_path("../escape.txt")


def test_resolve_windows_home_from_wsl_prefers_existing_userprofile_translation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    translated_root = tmp_path / "mnt"
    translated_candidate = translated_root / "c" / "Users" / "Alex"
    translated_candidate.mkdir(parents=True)
    monkeypatch.setattr(sut, "Path", _make_path_factory({"/mnt": translated_root}))
    monkeypatch.setenv("USERPROFILE", r"C:\Users\Alex")

    def fail_infer(windows_username: str | None) -> Path:
        _ = windows_username
        raise AssertionError("fallback not expected")

    monkeypatch.setattr(sut, "infer_windows_home_from_permissions", fail_infer)

    assert sut.resolve_windows_home_from_wsl(windows_username=None) == translated_candidate


def test_get_single_wsl_distribution_parses_utf16_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    stdout = "Windows Subsystem for Linux Distributions:\r\n* Ubuntu (Default)\r\n".encode("utf-16-le")

    def fake_run(args: list[str], capture_output: bool, text: bool, check: bool) -> subprocess.CompletedProcess[bytes]:
        _ = args, capture_output, text, check
        return subprocess.CompletedProcess(args=["wsl.exe", "-l"], returncode=0, stdout=stdout, stderr=b"")

    monkeypatch.setattr(sut.subprocess, "run", fake_run)

    assert sut.get_single_wsl_distribution() == "Ubuntu"


def test_run_windows_copy_command_adds_recurse_for_directories(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    target_path = tmp_path / "target" / "copied"
    recorded_commands: list[list[str]] = []

    def fake_run(args: list[str], check: bool) -> subprocess.CompletedProcess[str]:
        _ = check
        recorded_commands.append(args)
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(sut.subprocess, "run", fake_run)

    sut.run_windows_copy_command(source_dir, target_path)

    command = recorded_commands[0][4]
    assert "Copy-Item" in command
    assert "-Recurse -Force" in command
    assert str(source_dir) in command
    assert str(target_path) in command


def test_ensure_symlink_reuses_and_retargets_existing_link(tmp_path: Path) -> None:
    first_target = tmp_path / "first"
    second_target = tmp_path / "second"
    link_path = tmp_path / "link"
    first_target.mkdir()
    second_target.mkdir()

    assert sut.ensure_symlink(link_path, first_target) is True
    assert sut.ensure_symlink(link_path, first_target) is False
    assert sut.ensure_symlink(link_path, second_target) is True
    assert link_path.resolve() == second_target.resolve()


def test_port_helpers_parse_and_normalize_specs() -> None:
    assert sut.parse_port_spec("3000-3002, 8080") == [3000, 3001, 3002, 8080]
    assert sut.normalize_port_spec_for_firewall("3000-3002, 8080") == ("3000-3002,8080", "3000-3002, 8080")

    with pytest.raises(ValueError, match="No valid ports provided"):
        sut.normalize_port_spec_for_firewall(" , ")
