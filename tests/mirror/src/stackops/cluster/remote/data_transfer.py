

from dataclasses import dataclass
from pathlib import Path

import pytest

import stackops.cluster.remote.data_transfer as data_transfer


@dataclass(frozen=True, slots=True)
class FakeConfig:
    copy_repo: bool
    cloud_name: str | None


@dataclass(frozen=True, slots=True)
class FakeJobParams:
    repo_path_rh: str


@dataclass(frozen=True, slots=True)
class FakeFileManager:
    shell_script_path: Path
    job_root: Path


@dataclass(frozen=True, slots=True)
class RunCall:
    python_code: str
    uv_with: str | None
    uv_project_dir: str | None
    description: str
    verbose_output: bool
    strict_stderr: bool
    strict_return_code: bool


@dataclass(frozen=True, slots=True)
class CopyCall:
    source_path: str
    target_rel2home: str | None
    compress_with_zip: bool
    recursive: bool
    overwrite_existing: bool


class FakeSSH:
    def __init__(self) -> None:
        self.run_calls: list[RunCall] = []
        self.copy_calls: list[CopyCall] = []

    def run_py_remotely(
        self,
        *,
        python_code: str,
        uv_with: str | None,
        uv_project_dir: str | None,
        description: str,
        verbose_output: bool,
        strict_stderr: bool,
        strict_return_code: bool,
    ) -> None:
        self.run_calls.append(
            RunCall(
                python_code=python_code,
                uv_with=uv_with,
                uv_project_dir=uv_project_dir,
                description=description,
                verbose_output=verbose_output,
                strict_stderr=strict_stderr,
                strict_return_code=strict_return_code,
            )
        )

    def copy_from_here(
        self, *, source_path: str, target_rel2home: str | None, compress_with_zip: bool, recursive: bool, overwrite_existing: bool
    ) -> None:
        self.copy_calls.append(
            CopyCall(
                source_path=source_path,
                target_rel2home=target_rel2home,
                compress_with_zip=compress_with_zip,
                recursive=recursive,
                overwrite_existing=overwrite_existing,
            )
        )


def test_transfer_sftp_copies_repo_payloads_and_job_root(tmp_path: Path) -> None:
    ssh = FakeSSH()
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    file_path = tmp_path / "payload.txt"
    file_path.write_text("payload\n", encoding="utf-8")
    dir_path = tmp_path / "dir_payload"
    dir_path.mkdir()
    (dir_path / "nested.txt").write_text("nested\n", encoding="utf-8")
    job_root = tmp_path / "job_root"
    job_root.mkdir()
    file_manager = FakeFileManager(shell_script_path=job_root / "run.sh", job_root=job_root)

    data_transfer.transfer_sftp(
        ssh=ssh,
        config=FakeConfig(copy_repo=True, cloud_name="remote"),
        job_params=FakeJobParams(repo_path_rh=str(repo_path)),
        file_manager=file_manager,
        data=[str(file_path), str(dir_path)],
    )

    assert len(ssh.run_calls) == 1
    assert str(file_manager.shell_script_path) in ssh.run_calls[0].python_code
    assert [call.source_path for call in ssh.copy_calls] == [str(repo_path), str(file_path), str(dir_path), str(job_root)]
    assert ssh.copy_calls[0].compress_with_zip is True
    assert ssh.copy_calls[1].compress_with_zip is False
    assert ssh.copy_calls[2].compress_with_zip is True
    assert ssh.copy_calls[3].recursive is True


def test_transfer_cloud_prepends_download_commands(tmp_path: Path) -> None:
    shell_script_path = tmp_path / "run.sh"
    shell_script_path.write_text("echo existing\n", encoding="utf-8")
    repo_path = Path.home() / "code" / "tool"
    data_path = Path.home() / "downloads" / "input.txt"
    job_root = Path.home() / "tmp_results" / "job-1"

    data_transfer.transfer_cloud(
        ssh=FakeSSH(),
        config=FakeConfig(copy_repo=True, cloud_name="remote"),
        job_params=FakeJobParams(repo_path_rh=str(repo_path)),
        file_manager=FakeFileManager(shell_script_path=shell_script_path, job_root=job_root),
        data=[str(data_path)],
    )

    lines = shell_script_path.read_text(encoding="utf-8").splitlines()

    assert lines == [
        f"rclone copy remote:code/tool {repo_path}",
        f"rclone copy remote:downloads/input.txt {data_path}",
        f"rclone copy remote:tmp_results/job-1 {job_root}",
        "echo existing",
    ]


def test_transfer_cloud_requires_cloud_name(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="cloud_name must be set"):
        data_transfer.transfer_cloud(
            ssh=FakeSSH(),
            config=FakeConfig(copy_repo=False, cloud_name=None),
            job_params=FakeJobParams(repo_path_rh=str(tmp_path / "repo")),
            file_manager=FakeFileManager(shell_script_path=tmp_path / "run.sh", job_root=tmp_path / "job"),
            data=[],
        )


def test_rel2home_returns_relative_only_for_home_descendants(tmp_path: Path) -> None:
    home_child = Path.home() / "code" / "tool"

    assert data_transfer._rel2home(str(home_child)) == "code/tool"
    assert data_transfer._rel2home(str(tmp_path)) == str(tmp_path)
