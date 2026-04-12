from pathlib import Path

import pytest

import machineconfig.scripts.python.helpers.helpers_network.ssh.ssh_add_key_windows as subject



def _redirect_program_data(monkeypatch: pytest.MonkeyPatch, sshd_dir: Path) -> None:
    def fake_path(value: str) -> Path:
        if value == "C:/ProgramData/ssh":
            return sshd_dir
        return Path(value)

    monkeypatch.setattr(subject, "Path", fake_path)



def test_add_ssh_key_windows_appends_key_and_updates_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    sshd_dir = tmp_path / "ssh"
    sshd_dir.mkdir(parents=True, exist_ok=True)
    admin_auth_keys = sshd_dir / "administrators_authorized_keys"
    sshd_config = sshd_dir / "sshd_config"
    key_file = tmp_path / "id.pub"
    commands: list[tuple[str, bool, bool]] = []

    admin_auth_keys.write_text("existing-key", encoding="utf-8")
    sshd_config.write_text("#PubkeyAuthentication yes\n", encoding="utf-8")
    key_file.write_text("ssh-rsa NEW-KEY\n", encoding="utf-8")
    _redirect_program_data(monkeypatch, sshd_dir)
    monkeypatch.setattr(
        subject.subprocess,
        "run",
        lambda command, *, shell, check: commands.append((command, shell, check)),
    )

    subject.add_ssh_key_windows(key_file)

    assert admin_auth_keys.read_text(encoding="utf-8") == "existing-key\nssh-rsa NEW-KEY\n"
    assert sshd_config.read_text(encoding="utf-8") == "PubkeyAuthentication yes\n"
    assert commands == [
        (
            f'icacls "{admin_auth_keys}" /inheritance:r /grant "Administrators:F" /grant "SYSTEM:F"',
            True,
            True,
        ),
        ("Restart-Service sshd -Force", True, True),
    ]



def test_add_ssh_key_windows_creates_authorized_keys_when_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    sshd_dir = tmp_path / "ssh"
    sshd_dir.mkdir(parents=True, exist_ok=True)
    key_file = tmp_path / "id.pub"
    commands: list[str] = []

    key_file.write_text("ssh-ed25519 KEY\n", encoding="utf-8")
    _redirect_program_data(monkeypatch, sshd_dir)
    monkeypatch.setattr(
        subject.subprocess,
        "run",
        lambda command, *, shell, check: commands.append(command),
    )

    subject.add_ssh_key_windows(key_file)

    assert sshd_dir.joinpath("administrators_authorized_keys").read_text(encoding="utf-8") == "ssh-ed25519 KEY\n"
    assert commands == [
        f'icacls "{sshd_dir / "administrators_authorized_keys"}" /inheritance:r /grant "Administrators:F" /grant "SYSTEM:F"',
        "Restart-Service sshd -Force",
    ]
