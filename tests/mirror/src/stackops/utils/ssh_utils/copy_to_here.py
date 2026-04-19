

from dataclasses import dataclass, field
import json
from pathlib import Path
import zipfile

import pytest

from stackops.utils.ssh_utils import copy_to_here as sut


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
class GetCall:
    remotepath: str
    localpath: str


@dataclass
class FakeSFTP:
    fail_after_write: bool
    get_calls: list[GetCall] = field(default_factory=list)

    def get(self, remotepath: str, localpath: str, callback: object | None = None) -> None:
        self.get_calls.append(GetCall(remotepath=remotepath, localpath=localpath))
        local_path = Path(localpath)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        if remotepath.endswith(".zip"):
            with zipfile.ZipFile(local_path, "w") as archive:
                archive.writestr("payload.txt", "payload")
        else:
            local_path.write_text(f"downloaded:{remotepath}", encoding="utf-8")
        if callable(callback):
            callback(1, 1)
        if self.fail_after_write:
            raise RuntimeError("download failed")


@dataclass
class FakeRunPyResponse:
    op: str


@dataclass
class FakeSSH:
    hostname: str
    sftp: FakeSFTP | None
    run_py_response_ops: list[str]
    json_by_remote_path: dict[str, str]
    is_dir_map: dict[str, bool]
    run_py_descriptions: list[str] = field(default_factory=list)
    copy_calls: list[tuple[str | Path, str | Path | None, bool, bool, bool]] = field(default_factory=list)
    tqdm_wrap: type[FakeProgress] = FakeProgress

    def expand_remote_path(self, source_path: str | Path) -> str:
        source_text = str(source_path)
        if source_text.startswith("~"):
            return "/remote/home/" + source_text[1:].lstrip("/\\")
        return source_text

    def check_remote_is_dir(self, source_path: str | Path) -> bool:
        return self.is_dir_map.get(str(source_path), False)

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
        return FakeRunPyResponse(op=self.run_py_response_ops.pop(0))

    def simple_sftp_get(self, remote_path: str, local_path: Path) -> None:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_text(self.json_by_remote_path[remote_path], encoding="utf-8")

    def copy_to_here(self, source: str | Path, target: str | Path | None, compress_with_zip: bool, recursive: bool, internal_call: bool) -> None:
        self.copy_calls.append((source, target, compress_with_zip, recursive, internal_call))
        sut.copy_to_here(self, source=source, target=target, compress_with_zip=compress_with_zip, recursive=recursive, internal_call=internal_call)


def test_copy_to_here_requires_sftp_connection() -> None:
    fake_ssh = FakeSSH(hostname="remote", sftp=None, run_py_response_ops=[], json_by_remote_path={}, is_dir_map={})

    with pytest.raises(RuntimeError, match="SFTP connection not available"):
        sut.copy_to_here(fake_ssh, source="/remote/source.txt", target="target.txt", compress_with_zip=False, recursive=False)


def test_copy_to_here_recurses_directory_and_derives_default_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(sut, "randstr", lambda: "fixed")
    fake_sftp = FakeSFTP(fail_after_write=False)
    fake_ssh = FakeSSH(
        hostname="remote",
        sftp=fake_sftp,
        run_py_response_ops=["/remote/file_list.json", "/remote/default_target.json"],
        json_by_remote_path={
            "/remote/file_list.json": json.dumps(["/remote/source/a.txt", "/remote/source/nested/b.txt"]),
            "/remote/default_target.json": json.dumps("~/mirror"),
        },
        is_dir_map={"/remote/source": True, "/remote/source/a.txt": False, "/remote/source/nested/b.txt": False},
    )
    fake_ssh.remote_specs = {"system": "Linux", "home_dir": "/remote/home"}  # type: ignore[attr-defined]

    fake_ssh.copy_to_here(source="/remote/source", target=None, compress_with_zip=False, recursive=True, internal_call=False)

    assert tmp_path.joinpath("mirror", "a.txt").read_text(encoding="utf-8") == "downloaded:/remote/source/a.txt"
    assert tmp_path.joinpath("mirror", "nested", "b.txt").read_text(encoding="utf-8") == "downloaded:/remote/source/nested/b.txt"
    assert [call.remotepath for call in fake_sftp.get_calls] == ["/remote/source/a.txt", "/remote/source/nested/b.txt"]


def test_copy_to_here_removes_partial_target_after_download_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    fake_ssh = FakeSSH(
        hostname="remote",
        sftp=FakeSFTP(fail_after_write=True),
        run_py_response_ops=[],
        json_by_remote_path={},
        is_dir_map={"/remote/file.txt": False},
    )
    fake_ssh.remote_specs = {"system": "Linux", "home_dir": "/remote/home"}  # type: ignore[attr-defined]
    target_path = tmp_path / "file.txt"

    with pytest.raises(RuntimeError, match="download failed"):
        fake_ssh.copy_to_here(source="/remote/file.txt", target=target_path, compress_with_zip=False, recursive=False, internal_call=False)

    assert not target_path.exists()


def test_copy_to_here_extracts_zip_and_cleans_remote_temp_archive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(sut, "randstr", lambda: "fixed")
    monkeypatch.setattr(sut, "lambda_to_python_script", lambda fn, in_global, import_module: "print('ok')")
    fake_sftp = FakeSFTP(fail_after_write=False)
    fake_ssh = FakeSSH(
        hostname="remote",
        sftp=fake_sftp,
        run_py_response_ops=["/remote/zipped.json", "cleanup-done"],
        json_by_remote_path={"/remote/zipped.json": json.dumps("/remote/tmp/source_archive.zip")},
        is_dir_map={},
    )
    fake_ssh.remote_specs = {"system": "Linux", "home_dir": "/remote/home"}  # type: ignore[attr-defined]

    fake_ssh.copy_to_here(source="/remote/source", target=tmp_path / "result.txt", compress_with_zip=True, recursive=False, internal_call=False)

    extracted_payload = tmp_path / "result.txt" / "payload.txt"
    assert extracted_payload.read_text(encoding="utf-8") == "payload"
    assert not tmp_path.joinpath("result.txt.zip").exists()
    assert fake_ssh.run_py_descriptions == ["Zipping source file /remote/source", "Cleaning temp zip files @ remote."]
