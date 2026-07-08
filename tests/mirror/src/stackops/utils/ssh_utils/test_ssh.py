from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast

import pytest

from stackops.utils.cli_utils.terminal import Response
from stackops.utils.machine.specs import MachineSpecs
from stackops.utils.ssh_utils import ssh as ssh_module
from stackops.utils.ssh_utils.ssh import SSH

if TYPE_CHECKING:
    import paramiko


type RemoteSystem = Literal["Windows", "Linux", "Darwin"]


class _ExitStatusChannel:
    def __init__(self, return_code: int) -> None:
        self.return_code = return_code

    def recv_exit_status(self) -> int:
        return self.return_code


class _CommandStream(BytesIO):
    def __init__(self, content: str, return_code: int) -> None:
        super().__init__(content.encode())
        self.channel = _ExitStatusChannel(return_code=return_code)


class _RemoteClient:
    def __init__(self, stdout: str, stderr: str, return_code: int) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.return_code = return_code

    def exec_command(self, _command: str) -> tuple[_CommandStream, _CommandStream, _CommandStream]:
        return (
            _CommandStream(content="", return_code=self.return_code),
            _CommandStream(content=self.stdout, return_code=self.return_code),
            _CommandStream(content=self.stderr, return_code=self.return_code),
        )


class _StopAfterRemoteCommand(Exception):
    pass


def _remote_specs(system: RemoteSystem, home_dir: str) -> MachineSpecs:
    return {
        "system": system,
        "distro": "test",
        "home_dir": home_dir,
        "hostname": "remote.test",
        "release": "test",
        "version": "test",
        "machine": "test",
        "processor": "test",
        "python_version": "3.13",
        "user": "remote-user",
    }


def _ssh_without_connection(system: RemoteSystem, home_dir: str) -> SSH:
    ssh = object.__new__(SSH)
    ssh.remote_specs = _remote_specs(system=system, home_dir=home_dir)
    return ssh


@pytest.mark.parametrize(
    ("system", "home_dir", "expected_path"),
    [
        ("Linux", "/home/aalsaffa", "/home/aalsaffa/tmp_results/tmp_scripts/ssh/return_token.json"),
        ("Windows", r"C:\Users\aalsaffa", r"C:\Users\aalsaffa\tmp_results\tmp_scripts\ssh\return_token.json"),
    ],
)
def test_remote_json_output_path_uses_remote_home(monkeypatch: pytest.MonkeyPatch, system: RemoteSystem, home_dir: str, expected_path: str) -> None:
    monkeypatch.setattr(ssh_module, "randstr", lambda: "token")
    ssh = _ssh_without_connection(system=system, home_dir=home_dir)

    assert ssh._build_remote_json_output_path() == expected_path


@pytest.mark.parametrize(
    ("system", "home_dir", "expected_path"),
    [
        ("Linux", "/home/aalsaffa", "/home/aalsaffa/tmp_results/tmp_scripts/ssh/return_token.json"),
        ("Windows", r"C:\Users\aalsaffa", r"C:\Users\aalsaffa\tmp_results\tmp_scripts\ssh\return_token.json"),
    ],
)
def test_compressed_download_serializes_remote_json_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, system: RemoteSystem, home_dir: str, expected_path: str
) -> None:
    local_home = tmp_path / "local-home"
    monkeypatch.setattr(ssh_module.Path, "home", lambda: local_home)
    monkeypatch.setattr(ssh_module, "randstr", lambda: "token")
    ssh = _ssh_without_connection(system=system, home_dir=home_dir)
    ssh.sftp = cast("paramiko.SFTPClient", object())
    python_commands: list[str] = []
    strict_return_codes: list[bool] = []

    def capture_remote_command(
        _self: SSH,
        python_code: str,
        uv_with: list[str] | None,
        uv_project_dir: str | None,
        description: str,
        verbose_output: bool,
        strict_stderr: bool,
        strict_return_code: bool,
    ) -> Response:
        _ = uv_with, uv_project_dir, description, verbose_output, strict_stderr
        python_commands.append(python_code)
        strict_return_codes.append(strict_return_code)
        raise _StopAfterRemoteCommand

    monkeypatch.setattr(SSH, "run_py_remotely", capture_remote_command)

    with pytest.raises(_StopAfterRemoteCommand):
        ssh.copy_to_here(
            source="~/code/oracle/caa-acute-inpatient-coding/reports",
            target=tmp_path / "reports",
            compress_with_zip=True,
            recursive=False,
            internal_call=False,
        )

    assert len(python_commands) == 1
    assert f"json_output_path: 'str' = {expected_path!r}" in python_commands[0]
    assert str(local_home) not in python_commands[0]
    assert strict_return_codes == [True]


@pytest.mark.parametrize("verbose_output", [False, True])
def test_strict_remote_failure_raises_with_stderr(verbose_output: bool, capsys: pytest.CaptureFixture[str]) -> None:
    ssh = _ssh_without_connection(system="Linux", home_dir="/home/aalsaffa")
    ssh.ssh = cast("paramiko.SSHClient", _RemoteClient(stdout="", stderr="PermissionError: /Users/alex", return_code=1))

    with pytest.raises(RuntimeError) as raised:
        ssh.run_shell_cmd_on_remote(
            command="remote-command", verbose_output=verbose_output, description="Zipping remote source", strict_stderr=False, strict_return_code=True
        )

    message = str(raised.value)
    assert "Remote command failed: Zipping remote source" in message
    assert "Return code: 1" in message
    assert "PermissionError: /Users/alex" in message
    assert "completed successfully" not in capsys.readouterr().out


def test_strict_stderr_rejects_successful_command_with_stderr() -> None:
    ssh = _ssh_without_connection(system="Linux", home_dir="/home/aalsaffa")
    ssh.ssh = cast("paramiko.SSHClient", _RemoteClient(stdout="complete", stderr="warning", return_code=0))

    with pytest.raises(RuntimeError, match="warning"):
        ssh.run_shell_cmd_on_remote(
            command="remote-command", verbose_output=False, description="Strict stderr command", strict_stderr=True, strict_return_code=True
        )


def test_non_strict_remote_failure_returns_response() -> None:
    ssh = _ssh_without_connection(system="Linux", home_dir="/home/aalsaffa")
    ssh.ssh = cast("paramiko.SSHClient", _RemoteClient(stdout="partial", stderr="failure", return_code=7))

    response = ssh.run_shell_cmd_on_remote(
        command="best-effort-command", verbose_output=False, description="Best effort remote command", strict_stderr=False, strict_return_code=False
    )

    assert response.op == "partial"
    assert response.err == "failure"
    assert response.returncode == 7
