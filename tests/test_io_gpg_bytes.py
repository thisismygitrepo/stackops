import subprocess

import pytest

from stackops.utils import io as stackops_io


def test_encrypt_bytes_asymmetric_runs_gpg_with_stdin(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        seen["command"] = command
        seen["input"] = kwargs["input"]
        return subprocess.CompletedProcess(command, 0, stdout=b"encrypted", stderr=b"")

    monkeypatch.setattr(stackops_io.subprocess, "run", fake_run)

    assert stackops_io.encrypt_bytes_asymmetric(b"cleartext") == b"encrypted"
    assert seen["command"] == [
        "gpg",
        "--batch",
        "--yes",
        "--default-recipient-self",
        "--encrypt",
        "--output",
        "-",
    ]
    assert seen["input"] == b"cleartext"


def test_decrypt_bytes_asymmetric_surfaces_gpg_errors(monkeypatch) -> None:
    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(command, 2, stdout=b"", stderr=b"no secret key")

    monkeypatch.setattr(stackops_io.subprocess, "run", fake_run)

    with pytest.raises(stackops_io.GpgCommandError) as exc_info:
        stackops_io.decrypt_bytes_asymmetric(b"encrypted")

    assert exc_info.value.hint is not None
    assert "private key" in exc_info.value.hint
