from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from machineconfig.utils.ssh_utils import utils as sut


@dataclass
class FakeRunPyResponse:
    op: str


@dataclass
class FakeRunShellResponse:
    op: str
    printed_descriptions: list[str] = field(default_factory=list)

    def print(self, desc: str) -> "FakeRunShellResponse":
        self.printed_descriptions.append(desc)
        return self


@dataclass
class PutCall:
    localpath: str
    remotepath: str


@dataclass
class FakeSFTP:
    put_calls: list[PutCall] = field(default_factory=list)

    def put(self, localpath: str, remotepath: str) -> None:
        self.put_calls.append(PutCall(localpath=localpath, remotepath=remotepath))


@dataclass
class FakeSSH:
    remote_specs: dict[str, str]
    sftp: FakeSFTP | None
    run_py_response_op: str
    downloaded_json: str
    run_py_descriptions: list[str] = field(default_factory=list)
    shell_commands: list[str] = field(default_factory=list)
    last_shell_response: FakeRunShellResponse | None = None

    def run_py_remotely(
        self,
        python_code: str,
        uv_with: list[str] | None,
        uv_project_dir: str | None,
        description: str,
        verbose_output: bool,
        strict_stderr: bool,
        strict_return_code: bool,
    ) -> FakeRunPyResponse:
        _ = python_code, uv_with, uv_project_dir, verbose_output, strict_stderr, strict_return_code
        self.run_py_descriptions.append(description)
        return FakeRunPyResponse(op=self.run_py_response_op)

    def simple_sftp_get(self, remote_path: str, local_path: Path) -> None:
        _ = remote_path
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_text(self.downloaded_json, encoding="utf-8")

    def run_shell_cmd_on_remote(
        self,
        command: str,
        verbose_output: bool,
        description: str,
        strict_stderr: bool,
        strict_return_code: bool,
    ) -> FakeRunShellResponse:
        _ = verbose_output, description, strict_stderr, strict_return_code
        self.shell_commands.append(command)
        response = FakeRunShellResponse(op="")
        self.last_shell_response = response
        return response


def _make_path_factory(mappings: dict[str, Path]) -> Callable[..., Path]:
    real_path = Path

    def fake_path(*parts: object) -> Path:
        path_text = str(real_path(*[str(part) for part in parts]))
        mapped = mappings.get(path_text)
        if mapped is not None:
            return mapped
        return real_path(*[str(part) for part in parts])

    return fake_path


def test_build_remote_path_and_normalization_follow_remote_platform() -> None:
    linux_ssh = FakeSSH(
        remote_specs={"system": "Linux", "home_dir": "/remote/home"},
        sftp=None,
        run_py_response_op="",
        downloaded_json="true",
    )
    windows_ssh = FakeSSH(
        remote_specs={"system": "Windows", "home_dir": r"C:\Users\alex"},
        sftp=None,
        run_py_response_op="",
        downloaded_json="true",
    )

    assert sut._build_remote_path(linux_ssh, "/remote/home", r"nested\file.txt") == "/remote/home/nested/file.txt"
    assert sut._build_remote_path(windows_ssh, r"C:\Users\alex", "nested/file.txt") == r"C:\Users\alex\nested\file.txt"
    assert sut._normalize_rel_path_for_remote(linux_ssh, r"a\b\c") == "a/b/c"
    assert sut._normalize_rel_path_for_remote(windows_ssh, "a/b/c") == r"a\b\c"


def test_expand_remote_path_handles_home_absolute_and_relative_paths() -> None:
    linux_ssh = FakeSSH(
        remote_specs={"system": "Linux", "home_dir": "/remote/home"},
        sftp=None,
        run_py_response_op="",
        downloaded_json="true",
    )
    windows_ssh = FakeSSH(
        remote_specs={"system": "Windows", "home_dir": r"C:\Users\alex"},
        sftp=None,
        run_py_response_op="",
        downloaded_json="true",
    )

    assert sut.expand_remote_path(linux_ssh, "~/docs/file.txt") == "/remote/home/docs/file.txt"
    assert sut.expand_remote_path(linux_ssh, "docs\\file.txt") == "/remote/home/docs/file.txt"
    assert sut.expand_remote_path(linux_ssh, "/var/log/syslog") == "/var/log/syslog"
    assert sut.expand_remote_path(windows_ssh, r"~\docs\file.txt") == r"C:\Users\alex\docs\file.txt"
    assert sut.expand_remote_path(windows_ssh, r"D:\data\file.txt") == r"D:\data\file.txt"
    assert sut.expand_remote_path(windows_ssh, "docs/file.txt") == r"C:\Users\alex\docs\file.txt"


def test_check_remote_is_dir_reads_boolean_json_and_cleans_temp_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(sut, "randstr", lambda: "fixed")
    fake_ssh = FakeSSH(
        remote_specs={"system": "Linux", "home_dir": "/remote/home"},
        sftp=None,
        run_py_response_op="/remote/result.json",
        downloaded_json="true",
    )

    result = sut.check_remote_is_dir(fake_ssh, source_path="~/data")

    assert result is True
    assert fake_ssh.run_py_descriptions == ["Check if source `~/data` is a dir"]
    local_json_path = tmp_path / sut.DEFAULT_PICKLE_SUBDIR / "local_fixed.json"
    assert not local_json_path.exists()


def test_check_remote_is_dir_rejects_empty_remote_response(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(sut, "randstr", lambda: "fixed")
    fake_ssh = FakeSSH(
        remote_specs={"system": "Linux", "home_dir": "/remote/home"},
        sftp=None,
        run_py_response_op="",
        downloaded_json="true",
    )

    with pytest.raises(RuntimeError, match="no response from remote"):
        sut.check_remote_is_dir(fake_ssh, source_path="~/data")


def test_create_dir_and_check_if_exists_uploads_script_and_runs_remote_python(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(sut, "randstr", lambda: "fixed")
    monkeypatch.setattr(sut, "lambda_to_python_script", lambda fn, in_global, import_module: "print('ok')")
    monkeypatch.setattr(sut, "get_uv_command", lambda platform: "uv")

    fake_sftp = FakeSFTP()
    fake_ssh = FakeSSH(
        remote_specs={"system": "Linux", "home_dir": "/remote/home"},
        sftp=fake_sftp,
        run_py_response_op="",
        downloaded_json="true",
    )

    sut.create_dir_and_check_if_exists(
        fake_ssh,
        path_rel2home="folder/file.txt",
        overwrite_existing=True,
    )

    assert fake_sftp.put_calls == [
        PutCall(
            localpath=str(tmp_path / sut.DEFAULT_PICKLE_SUBDIR / "create_target_dir_fixed.py"),
            remotepath="/remote/home/.tmp_pyfile.py",
        )
    ]
    assert fake_ssh.shell_commands == ["uv run python .tmp_pyfile.py"]
    assert fake_ssh.last_shell_response is not None
    assert fake_ssh.last_shell_response.printed_descriptions == ["Created target dir folder/file.txt"]
