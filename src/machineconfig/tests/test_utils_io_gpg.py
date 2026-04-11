from dataclasses import dataclass
from pathlib import Path
import subprocess

import pytest

import machineconfig.utils.io as io_module


@dataclass
class RunCall:
    command: list[str]
    check: bool
    capture_output: bool
    text: bool
    input_text: str | None


def _install_fake_run(monkeypatch: pytest.MonkeyPatch) -> list[RunCall]:
    calls: list[RunCall] = []

    def fake_run(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        input: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(
            RunCall(
                command=command,
                check=check,
                capture_output=capture_output,
                text=text,
                input_text=input,
            )
        )
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(io_module.subprocess, "run", fake_run)
    return calls


def test_encrypt_file_symmetric_uses_gpg_loopback_passphrase(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path.joinpath("plain.txt")
    source.write_text("payload", encoding="utf-8")
    calls = _install_fake_run(monkeypatch)

    result = io_module.encrypt_file_symmetric(file_path=source, pwd="hunter2")

    assert result == tmp_path.joinpath("plain.txt.gpg")
    assert calls == [
        RunCall(
            command=[
                "gpg",
                "--batch",
                "--yes",
                "--pinentry-mode",
                "loopback",
                "--passphrase-fd",
                "0",
                "--symmetric",
                "--cipher-algo",
                "AES256",
                "--output",
                str(result),
                str(source.resolve()),
            ],
            check=True,
            capture_output=True,
            text=True,
            input_text="hunter2\n",
        )
    ]


def test_decrypt_file_symmetric_removes_gpg_suffix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path.joinpath("plain.txt.gpg")
    source.write_text("payload", encoding="utf-8")
    calls = _install_fake_run(monkeypatch)

    result = io_module.decrypt_file_symmetric(file_path=source, pwd="hunter2")

    assert result == tmp_path.joinpath("plain.txt")
    assert calls == [
        RunCall(
            command=[
                "gpg",
                "--batch",
                "--yes",
                "--pinentry-mode",
                "loopback",
                "--passphrase-fd",
                "0",
                "--decrypt",
                "--output",
                str(result),
                str(source.resolve()),
            ],
            check=True,
            capture_output=True,
            text=True,
            input_text="hunter2\n",
        )
    ]


def test_encrypt_file_asymmetric_uses_default_recipient_self(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path.joinpath("plain.txt")
    source.write_text("payload", encoding="utf-8")
    calls = _install_fake_run(monkeypatch)

    result = io_module.encrypt_file_asymmetric(file_path=source)

    assert result == tmp_path.joinpath("plain.txt.gpg")
    assert calls == [
        RunCall(
            command=[
                "gpg",
                "--batch",
                "--yes",
                "--default-recipient-self",
                "--encrypt",
                "--output",
                str(result),
                str(source.resolve()),
            ],
            check=True,
            capture_output=True,
            text=True,
            input_text=None,
        )
    ]


def test_decrypt_file_asymmetric_uses_gpg_decrypt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path.joinpath("plain.txt.gpg")
    source.write_text("payload", encoding="utf-8")
    calls = _install_fake_run(monkeypatch)

    result = io_module.decrypt_file_asymmetric(file_path=source)

    assert result == tmp_path.joinpath("plain.txt")
    assert calls == [
        RunCall(
            command=[
                "gpg",
                "--batch",
                "--yes",
                "--decrypt",
                "--output",
                str(result),
                str(source.resolve()),
            ],
            check=True,
            capture_output=True,
            text=True,
            input_text=None,
        )
    ]