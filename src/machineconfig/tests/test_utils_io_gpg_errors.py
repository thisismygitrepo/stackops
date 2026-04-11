from pathlib import Path
import subprocess

import pytest

import machineconfig.utils.io as io_module


class _FakeTTY:
    def isatty(self) -> bool:
        return True

    def fileno(self) -> int:
        return 7


def test_gpg_environment_sets_gpg_tty_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GPG_TTY", raising=False)
    monkeypatch.setattr(io_module.sys, "stdin", _FakeTTY())
    monkeypatch.setattr(io_module.os, "ttyname", lambda fd: "/dev/pts/42")

    env = io_module.build_gpg_environment()

    assert env["GPG_TTY"] == "/dev/pts/42"


def test_decrypt_file_asymmetric_surfaces_gpg_stderr(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path.joinpath("plain.txt.gpg")
    source.write_text("payload", encoding="utf-8")
    monkeypatch.setattr(io_module, "build_gpg_environment", lambda: {})

    def fake_run(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        input: str | None = None,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        assert check is False
        assert capture_output is True
        assert text is True
        assert input is None
        assert env == {}
        return subprocess.CompletedProcess(
            command,
            2,
            "",
            "gpg: decryption failed: No secret key\n",
        )

    monkeypatch.setattr(io_module.subprocess, "run", fake_run)

    with pytest.raises(io_module.GpgCommandError) as exc_info:
        io_module.decrypt_file_asymmetric(file_path=source)

    error_text = str(exc_info.value)
    assert "Command: gpg --batch --yes --decrypt --output" in error_text
    assert "Exit code: 2" in error_text
    assert "gpg: decryption failed: No secret key" in error_text
    assert "If this file was password-encrypted, rerun the command with --password" in error_text