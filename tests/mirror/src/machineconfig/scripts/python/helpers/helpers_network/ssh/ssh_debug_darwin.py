from __future__ import annotations

from pathlib import Path

import pytest

from machineconfig.scripts.python.helpers.helpers_network.ssh import ssh_debug_darwin as target


def _noop_print(*_args: object, **_kwargs: object) -> None:
    return None


def _map_posix_path(root_dir: Path, value: str | Path) -> Path:
    raw_path = Path(value)
    if raw_path.is_absolute():
        return root_dir.joinpath(*raw_path.parts[1:])
    return raw_path


def _build_path_class(root_dir: Path, home_dir: Path) -> type[object]:
    class MappedPath:
        @classmethod
        def home(cls) -> Path:
            return home_dir

        def __new__(cls, value: str | Path) -> Path:
            return _map_posix_path(root_dir=root_dir, value=value)

    return MappedPath


def test_ssh_debug_darwin_rejects_non_macos(monkeypatch: object) -> None:
    monkeypatch.setattr(target, "system", lambda: "Linux")

    with pytest.raises(NotImplementedError):
        target.ssh_debug_darwin()


def test_ssh_debug_darwin_reports_missing_install_and_keys(monkeypatch: object, tmp_path: Path) -> None:
    root_dir = tmp_path.joinpath("root")
    home_dir = root_dir.joinpath("home", "tester")
    home_dir.mkdir(parents=True)
    home_dir.chmod(0o755)
    root_dir.joinpath("tmp").mkdir(parents=True)

    command_results: dict[tuple[str, ...], tuple[bool, str]] = {
        ("hostname",): (True, "mac-host"),
        ("ifconfig",): (True, "inet 127.0.0.1 netmask 0xff000000"),
        ("lsof", "-nP", "-iTCP", "-sTCP:LISTEN"): (True, ""),
    }

    monkeypatch.setattr(target, "system", lambda: "Darwin")
    monkeypatch.setattr(target, "check_sshd_installed", lambda: (False, ""))
    monkeypatch.setattr(target, "run_cmd", lambda cmd: command_results.get(tuple(cmd), (False, "")))
    monkeypatch.setattr(target, "Path", _build_path_class(root_dir=root_dir, home_dir=home_dir))
    monkeypatch.setattr(target.console, "print", _noop_print)

    results = target.ssh_debug_darwin()

    assert results["installation"]["status"] == "error"
    assert results["ssh_directory"]["status"] == "error"
    assert results["authorized_keys"]["status"] == "error"
    assert results["ssh_service"]["status"] == "error"
    assert results["ssh_listening"]["status"] == "error"
    assert root_dir.joinpath("tmp", "ssh_fix.sh").is_file()


def test_ssh_debug_darwin_reads_main_config_and_listening_port(monkeypatch: object, tmp_path: Path) -> None:
    root_dir = tmp_path.joinpath("root")
    home_dir = root_dir.joinpath("home", "tester")
    ssh_dir = home_dir.joinpath(".ssh")
    ssh_dir.mkdir(parents=True)
    home_dir.chmod(0o755)
    ssh_dir.chmod(0o700)
    ssh_dir.joinpath("authorized_keys").write_text("ssh-ed25519 AAAA key\n", encoding="utf-8")
    ssh_dir.joinpath("authorized_keys").chmod(0o600)
    root_dir.joinpath("private", "etc", "ssh").mkdir(parents=True)
    root_dir.joinpath("tmp").mkdir(parents=True)
    root_dir.joinpath("private", "etc", "ssh", "sshd_config").write_text(
        """
Port 2200
PubkeyAuthentication no
PasswordAuthentication yes
PermitRootLogin no
""".strip(),
        encoding="utf-8",
    )

    command_results: dict[tuple[str, ...], tuple[bool, str]] = {
        ("hostname",): (True, "mac-host"),
        ("launchctl", "list", "com.openssh.sshd"): (True, '{"PID" = 123;}'),
        ("ifconfig",): (True, "inet 127.0.0.1 netmask 0xff000000\ninet 192.168.1.10 netmask 0xffffff00"),
        ("lsof", "-nP", "-iTCP", "-sTCP:LISTEN"): (True, "sshd 123 root 3u IPv4 0 0 TCP *:2200 (LISTEN)"),
    }

    monkeypatch.setattr(target, "system", lambda: "Darwin")
    monkeypatch.setattr(target, "check_sshd_installed", lambda: (True, "/usr/sbin/sshd"))
    monkeypatch.setattr(target, "run_cmd", lambda cmd: command_results.get(tuple(cmd), (False, "")))
    monkeypatch.setattr(target, "Path", _build_path_class(root_dir=root_dir, home_dir=home_dir))
    monkeypatch.setattr(target.console, "print", _noop_print)

    results = target.ssh_debug_darwin()

    assert results["installation"]["status"] == "ok"
    assert results["authorized_keys"]["status"] == "ok"
    assert results["ssh_service"]["status"] == "ok"
    assert results["pubkey_auth"]["status"] == "error"
    assert results["password_auth"]["status"] == "ok"
    assert results["ssh_listening"]["message"] == "Listening on 2200"
