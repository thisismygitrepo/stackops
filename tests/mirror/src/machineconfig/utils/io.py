from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from machineconfig.utils import io as io_module


def test_save_json_creates_parent_directory_and_trailing_newline(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "nested" / "data.json"

    saved_path = io_module.save_json({"hello": "world"}, output_path, indent=2)

    assert saved_path == output_path
    assert output_path.read_text(encoding="utf-8").endswith("\n")


def test_remove_c_style_comments_preserves_urls() -> None:
    text = """
{
  "url": "https://example.com/a//b",
  // remove this line
  "value": 1 /* remove this block */
}
""".strip()

    cleaned = io_module.remove_c_style_comments(text)

    assert "remove this line" not in cleaned
    assert "remove this block" not in cleaned
    assert "https://example.com/a//b" in cleaned


def test_run_gpg_raises_gpg_command_error_with_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completed = subprocess.CompletedProcess[list[str]](
        args=["gpg", "--decrypt"],
        returncode=2,
        stdout="",
        stderr="bad passphrase",
    )

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[list[str]]:
        _ = args, kwargs
        return completed

    monkeypatch.setattr(io_module.subprocess, "run", fake_run)
    monkeypatch.setattr(io_module, "build_gpg_environment", lambda: {})

    with pytest.raises(io_module.GpgCommandError) as exc_info:
        io_module._run_gpg(["gpg", "--decrypt"], pwd="secret")

    assert exc_info.value.hint == (
        "The provided password was rejected by GPG. Verify --password and try again."
    )
    assert "Exit code: 2" in str(exc_info.value)


def test_encrypt_and_decrypt_file_wrappers_build_expected_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], str | None]] = []

    def fake_run(command: list[str], pwd: str | None = None) -> None:
        calls.append((command, pwd))

    monkeypatch.setattr(io_module, "_run_gpg", fake_run)

    plain_text_path = tmp_path / "plain.txt"
    encrypted_input_path = tmp_path / "plain.txt.gpg"
    plain_text_path.write_text("secret", encoding="utf-8")
    encrypted_input_path.write_text("cipher", encoding="utf-8")

    encrypted_path = io_module.encrypt_file_symmetric(plain_text_path, "pw")
    decrypted_path = io_module.decrypt_file_symmetric(encrypted_input_path, "pw")

    assert encrypted_path == plain_text_path.with_name("plain.txt.gpg")
    assert decrypted_path == encrypted_input_path.with_name("plain.txt")
    assert calls[0][1] == "pw"
    assert calls[1][1] == "pw"
    assert "--symmetric" in calls[0][0]
    assert "--decrypt" in calls[1][0]
