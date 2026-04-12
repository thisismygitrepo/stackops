from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from machineconfig.scripts.python.helpers.helpers_network.ssh import ssh_deploy_key_remote as target


@dataclass(slots=True)
class FakeRemoteResponse:
    op: str
    err: str


def _noop_print(*_args: object, **_kwargs: object) -> None:
    return None


def test_deploy_key_to_remote_returns_false_when_pubkey_missing(monkeypatch: object, tmp_path: Path) -> None:
    ssh_init_calls: list[str] = []

    class FakeSSH:
        def __init__(
            self,
            *,
            host: str,
            username: str | None,
            hostname: str | None,
            ssh_key_path: Path | None,
            password: str | None,
            port: int,
            enable_compression: bool,
        ) -> None:
            _ = (username, hostname, ssh_key_path, password, port, enable_compression)
            ssh_init_calls.append(host)

    monkeypatch.setattr(target, "SSH", FakeSSH)
    monkeypatch.setattr(target.console, "print", _noop_print)

    result = target.deploy_key_to_remote(remote_target="example", pubkey_path=tmp_path.joinpath("missing.pub"), password=None)

    assert result is False
    assert ssh_init_calls == []


def test_deploy_to_unix_remote_appends_missing_key(monkeypatch: object) -> None:
    commands: list[str] = []

    class FakeSSH:
        def __init__(self) -> None:
            self.responses = [FakeRemoteResponse(op="FILE_NOT_FOUND", err=""), FakeRemoteResponse(op="DEPLOYED", err="")]

        def run_shell_cmd_on_remote(
            self, *, command: str, verbose_output: bool, description: str, strict_stderr: bool, strict_return_code: bool
        ) -> FakeRemoteResponse:
            _ = (verbose_output, description, strict_stderr, strict_return_code)
            commands.append(command)
            return self.responses.pop(0)

    monkeypatch.setattr(target.console, "print", _noop_print)

    fake_ssh = FakeSSH()
    result = target._deploy_to_unix_remote(fake_ssh, "ssh-ed25519 AAAA test-key")

    assert result is True
    assert "base64 --decode" in commands[0]
    assert "authorized_keys" in commands[1]


def test_deploy_to_windows_remote_reports_restart_needed(monkeypatch: object) -> None:
    class FakeSSH:
        def run_py_remotely(
            self,
            *,
            python_code: str,
            uv_with: object,
            uv_project_dir: object,
            description: str,
            verbose_output: bool,
            strict_stderr: bool,
            strict_return_code: bool,
        ) -> FakeRemoteResponse:
            _ = (uv_with, uv_project_dir, description, verbose_output, strict_stderr, strict_return_code)
            assert "administrators_authorized_keys" in python_code
            return FakeRemoteResponse(op="DEPLOYED_RESTART_NEEDED", err="")

    monkeypatch.setattr(target.console, "print", _noop_print)

    assert target._deploy_to_windows_remote(FakeSSH(), "ssh-ed25519 AAAA test-key") == (True, True)


def test_deploy_key_to_remote_restarts_windows_service_when_needed(monkeypatch: object, tmp_path: Path) -> None:
    pubkey_path = tmp_path.joinpath("id_test.pub")
    pubkey_path.write_text("ssh-ed25519 AAAA test-key\n", encoding="utf-8")
    restart_calls: list[str] = []
    close_calls: list[str] = []

    class FakeSSH:
        def __init__(
            self,
            *,
            host: str,
            username: str | None,
            hostname: str | None,
            ssh_key_path: Path | None,
            password: str | None,
            port: int,
            enable_compression: bool,
        ) -> None:
            _ = (username, hostname, ssh_key_path, password, port, enable_compression)
            self.remote_specs = {"system": "Windows"}
            self.host = host

        def close(self) -> None:
            close_calls.append(self.host)

        def get_remote_repr(self, add_machine: bool) -> str:
            _ = add_machine
            return "windows-host"

    monkeypatch.setattr(target, "SSH", FakeSSH)
    monkeypatch.setattr(target, "_deploy_to_windows_remote", lambda _ssh, _key: (True, True))
    monkeypatch.setattr(target, "_attempt_sshd_restart_windows", lambda _ssh: restart_calls.append("restart"))
    monkeypatch.setattr(target.console, "print", _noop_print)

    result = target.deploy_key_to_remote(remote_target="windows-host", pubkey_path=pubkey_path, password="pw")

    assert result is True
    assert restart_calls == ["restart"]
    assert close_calls == ["windows-host"]
