from __future__ import annotations

from dataclasses import dataclass, field
import io
from pathlib import Path
from types import MethodType

import getpass
import pytest

from stackops.utils import ssh as sut
from stackops.utils.terminal import Response


@dataclass
class FakeChannel:
    exit_status: int

    def recv_exit_status(self) -> int:
        return self.exit_status


class FakeStream(io.BytesIO):
    channel: FakeChannel

    def __init__(self, text: str, exit_status: int) -> None:
        super().__init__(text.encode())
        self.channel = FakeChannel(exit_status=exit_status)


@dataclass
class FakeSFTP:
    closed: bool = False
    get_calls: list[tuple[str, str]] = field(default_factory=list)

    def get(self, remotepath: str, localpath: str) -> None:
        self.get_calls.append((remotepath, localpath))
        local_path = Path(localpath)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_text("payload", encoding="utf-8")

    def close(self) -> None:
        self.closed = True


@dataclass
class FakeSSHClient:
    stdout_text: str = ""
    stderr_text: str = ""
    exit_status: int = 0
    commands: list[str] = field(default_factory=list)
    closed: bool = False

    def exec_command(self, command: str) -> tuple[io.BytesIO, FakeStream, io.BytesIO]:
        self.commands.append(command)
        return (io.BytesIO(b""), FakeStream(self.stdout_text, self.exit_status), io.BytesIO(self.stderr_text.encode()))

    def close(self) -> None:
        self.closed = True


def _make_ssh_instance() -> sut.SSH:
    ssh_instance = sut.SSH.__new__(sut.SSH)
    ssh_instance.host = "alias"
    ssh_instance.hostname = "remote"
    ssh_instance.username = "alex"
    ssh_instance.port = 2200
    ssh_instance.password = None
    ssh_instance.enable_compression = False
    ssh_instance.proxycommand = None
    ssh_instance.ssh_key_path = "/tmp/key"
    ssh_instance.remote_specs = {"system": "Linux", "distro": "Ubuntu", "home_dir": "/remote/home"}
    ssh_instance.local_specs = {"system": "Linux", "distro": "Ubuntu"}
    ssh_instance.sftp = FakeSFTP()
    ssh_instance.ssh = FakeSSHClient()
    ssh_instance.terminal_responses = []
    return ssh_instance


def test_callable_name_uses_function_name_or_class_name() -> None:
    class CallableObject:
        def __call__(self) -> None:
            return None

    def named_function() -> None:
        return None

    assert sut.SSH._callable_name(named_function) == "named_function"
    assert sut.SSH._callable_name(CallableObject()) == "CallableObject"


def test_repr_helpers_and_ssh_command_string(monkeypatch: pytest.MonkeyPatch) -> None:
    ssh_instance = _make_ssh_instance()
    monkeypatch.setattr(getpass, "getuser", lambda: "local-user")
    monkeypatch.setattr(sut.platform, "node", lambda: "local-node")
    monkeypatch.setattr(sut.platform, "system", lambda: "Linux")

    assert ssh_instance.get_remote_repr(add_machine=True) == "alex@remote:2200 [Linux][Ubuntu]"
    assert ssh_instance.get_local_repr(add_machine=True) == "local-user@local-node [Linux][Ubuntu]"
    ssh_command = ssh_instance.get_ssh_conn_str("ls")
    assert "-i /tmp/key" in ssh_command
    assert "alex@remote -p 2200" in ssh_command
    assert "-t ls" in ssh_command
    assert "SSH TO" in repr(ssh_instance)


def test_run_shell_cmd_on_remote_captures_streams_and_exit_status(monkeypatch: pytest.MonkeyPatch) -> None:
    ssh_instance = _make_ssh_instance()
    fake_client = FakeSSHClient(stdout_text="stdout\n", stderr_text="", exit_status=7)
    ssh_instance.ssh = fake_client

    def fake_print_if_unsuccessful(self: Response, desc: str, strict_err: bool, strict_returncode: bool, assert_success: bool) -> Response:
        _ = desc, strict_err, strict_returncode, assert_success
        return self

    monkeypatch.setattr(sut.Response, "print_if_unsuccessful", fake_print_if_unsuccessful)

    response = ssh_instance.run_shell_cmd_on_remote(
        command="echo hi", verbose_output=False, description="desc", strict_stderr=True, strict_return_code=True
    )

    assert fake_client.commands == ["echo hi"]
    assert response.op == "stdout"
    assert response.err == ""
    assert response.returncode == 7


def test_run_py_prep_writes_script_uploads_it_and_formats_uv_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ssh_instance = _make_ssh_instance()
    copied_calls: list[tuple[str, str | None, bool, bool, bool]] = []
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(sut, "randstr", lambda: "fixed")
    monkeypatch.setattr(sut, "get_uv_command", lambda platform: "uv")

    def fake_copy_from_here(
        self: sut.SSH, source_path: str, target_rel2home: str | None, compress_with_zip: bool, recursive: bool, overwrite_existing: bool
    ) -> None:
        _ = self
        copied_calls.append((source_path, target_rel2home, compress_with_zip, recursive, overwrite_existing))

    ssh_instance.copy_from_here = MethodType(fake_copy_from_here, ssh_instance)

    uv_command = ssh_instance._run_py_prep(python_code="print('hi')", uv_with=["pkg1", "pkg2"], uv_project_dir="/project", on="remote")

    script_path = tmp_path / sut.DEFAULT_PICKLE_SUBDIR / "runpy_fixed.py"
    assert script_path.read_text(encoding="utf-8") == "print('hi')"
    assert copied_calls == [(str(script_path), None, False, False, False)]
    assert '--with "pkg1,pkg2"' in uv_command
    assert "--project /project" in uv_command
    assert uv_command.endswith(f"python {sut.DEFAULT_PICKLE_SUBDIR}/runpy_fixed.py")


def test_run_lambda_function_wraps_linux_command_in_login_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    ssh_instance = _make_ssh_instance()
    recorded_commands: list[tuple[str, str]] = []
    monkeypatch.setattr(sut, "lambda_to_python_script", lambda func, in_global, import_module: "print('ok')")

    def fake_run_py_prep(self: sut.SSH, python_code: str, uv_with: list[str] | None, uv_project_dir: str | None, on: str) -> str:
        _ = self, python_code, uv_with, uv_project_dir, on
        return "uv run python tmp.py"

    def fake_run_shell_cmd_on_remote(
        self: sut.SSH, command: str, verbose_output: bool, description: str, strict_stderr: bool, strict_return_code: bool
    ) -> Response:
        _ = self, verbose_output, strict_stderr, strict_return_code
        recorded_commands.append((command, description))
        return Response(cmd=command, desc=description)

    ssh_instance._run_py_prep = MethodType(fake_run_py_prep, ssh_instance)
    ssh_instance.run_shell_cmd_on_remote = MethodType(fake_run_shell_cmd_on_remote, ssh_instance)

    class Runner:
        def __call__(self) -> None:
            return None

    ssh_instance.run_lambda_function(func=Runner(), import_module=False, uv_with=None, uv_project_dir=None)

    assert recorded_commands == [('bash -l -c "uv run python tmp.py"', "run_py_func Runner on alex@remote:2200")]


def test_simple_sftp_get_creates_parent_dirs_and_close_releases_connections(tmp_path: Path) -> None:
    ssh_instance = _make_ssh_instance()
    fake_sftp = FakeSFTP()
    fake_ssh_client = FakeSSHClient()
    ssh_instance.sftp = fake_sftp
    ssh_instance.ssh = fake_ssh_client
    local_path = tmp_path / "nested" / "payload.txt"

    ssh_instance.simple_sftp_get("/remote/payload.txt", local_path)
    ssh_instance.close()

    assert local_path.read_text(encoding="utf-8") == "payload"
    assert fake_sftp.get_calls == [("/remote/payload.txt", str(local_path))]
    assert fake_sftp.closed is True
    assert ssh_instance.sftp is None
    assert fake_ssh_client.closed is True
