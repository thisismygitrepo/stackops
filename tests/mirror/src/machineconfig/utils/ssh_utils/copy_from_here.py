from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from machineconfig.utils.ssh_utils import copy_from_here as sut


class FakeProgress:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs
        self.updates: list[tuple[int, int]] = []

    def __enter__(self) -> "FakeProgress":
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        _ = exc_type, exc_val, exc_tb

    def view_bar(self, transferred: int, total: int) -> None:
        self.updates.append((transferred, total))


@dataclass
class PutCall:
    localpath: str
    remotepath: str


@dataclass
class FakeSFTP:
    put_calls: list[PutCall] = field(default_factory=list)

    def put(self, localpath: str, remotepath: str, callback: object | None = None) -> None:
        self.put_calls.append(PutCall(localpath=localpath, remotepath=remotepath))
        if callable(callback):
            callback(1, 1)


@dataclass
class FakeRunResponse:
    op: str


@dataclass
class FakeSSH:
    remote_specs: dict[str, str]
    hostname: str
    sftp: FakeSFTP | None
    created_dirs: list[tuple[str, bool]] = field(default_factory=list)
    run_commands: list[str] = field(default_factory=list)
    copy_calls: list[tuple[str, str | None, bool, bool, bool]] = field(default_factory=list)
    tqdm_wrap: type[FakeProgress] = FakeProgress

    def create_parent_dir_and_check_if_exists(self, path_rel2home: str, overwrite_existing: bool) -> None:
        self.created_dirs.append((path_rel2home, overwrite_existing))

    def run_shell_cmd_on_remote(
        self, command: str, verbose_output: bool, description: str, strict_stderr: bool, strict_return_code: bool
    ) -> FakeRunResponse:
        _ = verbose_output, description, strict_stderr, strict_return_code
        self.run_commands.append(command)
        return FakeRunResponse(op="")

    def copy_from_here(
        self, source_path: str, target_rel2home: str | None, compress_with_zip: bool, recursive: bool, overwrite_existing: bool
    ) -> None:
        self.copy_calls.append((source_path, target_rel2home, compress_with_zip, recursive, overwrite_existing))
        sut.copy_from_here(
            self,
            source_path=source_path,
            target_rel2home=target_rel2home,
            compress_with_zip=compress_with_zip,
            recursive=recursive,
            overwrite_existing=overwrite_existing,
        )


def test_build_remote_path_respects_remote_platform() -> None:
    linux_ssh = FakeSSH(remote_specs={"system": "Linux", "home_dir": "/remote/home"}, hostname="remote", sftp=FakeSFTP())
    windows_ssh = FakeSSH(remote_specs={"system": "Windows", "home_dir": r"C:\Users\alex"}, hostname="remote", sftp=FakeSFTP())

    assert sut._build_remote_path(linux_ssh, "/remote/home", r"nested\file.txt") == "/remote/home/nested/file.txt"
    assert sut._build_remote_path(windows_ssh, r"C:\Users\alex", "nested/file.txt") == r"C:\Users\alex\nested\file.txt"


def test_copy_from_here_requires_sftp_connection(tmp_path: Path) -> None:
    source_file = tmp_path / "source.txt"
    source_file.write_text("payload", encoding="utf-8")
    fake_ssh = FakeSSH(remote_specs={"system": "Linux", "home_dir": "/remote/home"}, hostname="remote", sftp=None)

    with pytest.raises(RuntimeError, match="SFTP connection not available"):
        sut.copy_from_here(
            fake_ssh, source_path=str(source_file), target_rel2home="target.txt", compress_with_zip=False, recursive=False, overwrite_existing=False
        )


def test_copy_from_here_rejects_implicit_target_outside_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setenv("HOME", str(home_dir))
    source_file = tmp_path / "outside.txt"
    source_file.write_text("payload", encoding="utf-8")
    fake_ssh = FakeSSH(remote_specs={"system": "Linux", "home_dir": "/remote/home"}, hostname="remote", sftp=FakeSFTP())

    with pytest.raises(RuntimeError, match="source must be relative to home directory"):
        sut.copy_from_here(
            fake_ssh, source_path=str(source_file), target_rel2home=None, compress_with_zip=False, recursive=False, overwrite_existing=False
        )


def test_copy_from_here_recurses_over_directory_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home_dir = tmp_path / "home"
    source_dir = home_dir / "projects" / "source"
    nested_dir = source_dir / "nested"
    nested_dir.mkdir(parents=True)
    source_dir.joinpath("a.txt").write_text("a", encoding="utf-8")
    nested_dir.joinpath("b.txt").write_text("b", encoding="utf-8")
    monkeypatch.setenv("HOME", str(home_dir))

    fake_ssh = FakeSSH(remote_specs={"system": "Linux", "home_dir": "/remote/home"}, hostname="remote", sftp=FakeSFTP())

    fake_ssh.copy_from_here(source_path=str(source_dir), target_rel2home=None, compress_with_zip=False, recursive=True, overwrite_existing=True)

    assert {call.remotepath for call in fake_ssh.sftp.put_calls} == {
        "/remote/home/projects/source/a.txt",
        "/remote/home/projects/source/nested/b.txt",
    }
    assert fake_ssh.created_dirs[0] == ("projects/source", True)


def test_copy_from_here_zips_file_uploads_archive_and_runs_remote_unzip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setattr(sut, "randstr", lambda: "fixed")
    monkeypatch.setattr(sut, "lambda_to_python_script", lambda fn, in_global, import_module: "print('ok')")
    monkeypatch.setattr(sut, "get_uv_command", lambda platform: "uv")

    source_file = home_dir / "file.txt"
    source_file.write_text("payload", encoding="utf-8")
    fake_sftp = FakeSFTP()
    fake_ssh = FakeSSH(remote_specs={"system": "Linux", "home_dir": "/remote/home"}, hostname="remote", sftp=fake_sftp)

    fake_ssh.copy_from_here(
        source_path=str(source_file), target_rel2home="dest/file.txt", compress_with_zip=True, recursive=False, overwrite_existing=True
    )

    uploaded_paths = {call.remotepath for call in fake_sftp.put_calls}
    assert "/remote/home/dest/file.txt.zip" in uploaded_paths
    assert f"/remote/home/{sut.DEFAULT_PICKLE_SUBDIR}/create_target_dir_fixed.py" in uploaded_paths
    assert fake_ssh.run_commands == [f"uv run python {sut.DEFAULT_PICKLE_SUBDIR}/create_target_dir_fixed.py"]
    assert not home_dir.joinpath("file.txt_archive.zip").exists()
    assert not home_dir.joinpath(sut.DEFAULT_PICKLE_SUBDIR, "create_target_dir_fixed.py").exists()
