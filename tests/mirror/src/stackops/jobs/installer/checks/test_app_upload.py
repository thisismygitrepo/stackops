from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from subprocess import CalledProcessError
from unittest.mock import Mock

import pytest
from typer.testing import CliRunner

from stackops.jobs.installer.checks import app_upload, security_cli
from stackops.utils.cloud.share_models import ShareLinkOptions


@dataclass
class _Upload:
    snapshot: Path
    destination: Path
    contents: bytes


@dataclass
class _CloudCalls:
    remote: Mock
    upload: Mock
    requests: list[_Upload]
    failure: CalledProcessError | None
    share_url: str | None


@pytest.fixture
def cloud_calls(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> _CloudCalls:
    monkeypatch.setattr(Path, "home", Mock(return_value=tmp_path))
    monkeypatch.setattr("stackops.utils.cloud.rclone_wrapper.platform.system", Mock(return_value="Linux"))
    calls = _CloudCalls(remote=Mock(return_value="archive"), upload=Mock(), requests=[], failure=None, share_url="https://example.test/shared-binary")

    def record_upload(
        *,
        local_path: Path,
        cloud: str,
        remote_path: Path,
        overwrite: bool,
        share: bool,
        share_options: ShareLinkOptions | None,
        verbose: bool,
        show_progress: bool,
        transfers: int,
    ) -> str | None:
        assert cloud == "archive"
        assert overwrite is False
        assert share is True
        assert share_options is None
        assert verbose is False
        assert show_progress is False
        assert transfers == 10
        calls.requests.append(_Upload(snapshot=local_path, destination=remote_path, contents=local_path.read_bytes()))
        if calls.failure is not None:
            raise calls.failure
        return calls.share_url

    calls.upload.side_effect = record_upload
    monkeypatch.setattr(app_upload, "read_default_rclone_remote", calls.remote)
    monkeypatch.setattr(app_upload, "to_cloud", calls.upload)
    return calls


@pytest.fixture
def app_path(tmp_path: Path) -> Path:
    path = tmp_path / ".local" / "bin" / "tool.exe"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"first-version")
    return path


def test_upload_uses_original_app_name_and_content_hash(app_path: Path, cloud_calls: _CloudCalls) -> None:
    expected_hash = sha256(app_path.read_bytes()).hexdigest()

    result = app_upload.upload_app(app_path, expected_sha256=expected_hash)

    assert result == "https://example.test/shared-binary"
    assert len(cloud_calls.requests) == 1
    request = cloud_calls.requests[0]
    assert request.destination == Path("myhome/security/linux/.local/bin/tool") / expected_hash / "tool.exe"
    assert request.contents == b"first-version"
    assert request.snapshot.name == app_path.name
    assert request.snapshot != app_path
    assert not request.snapshot.parent.exists()
    assert app_path.read_bytes() == b"first-version"


def test_changed_bytes_get_a_new_path_and_identical_bytes_reuse_it(app_path: Path, cloud_calls: _CloudCalls) -> None:
    first_hash = sha256(app_path.read_bytes()).hexdigest()
    assert app_upload.upload_app(app_path, expected_sha256=None) is not None
    app_path.write_bytes(b"second-version")
    second_hash = sha256(app_path.read_bytes()).hexdigest()
    assert app_upload.upload_app(app_path, expected_sha256=second_hash) is not None
    assert app_upload.upload_app(app_path, expected_sha256=second_hash) is not None

    destinations = [request.destination for request in cloud_calls.requests]
    base = Path("myhome/security/linux/.local/bin/tool")
    assert destinations == [base / first_hash / "tool.exe", base / second_hash / "tool.exe", base / second_hash / "tool.exe"]
    assert all(not request.snapshot.parent.exists() for request in cloud_calls.requests)


def test_linux_hash_directory_preserves_previous_flat_upload(tmp_path: Path, cloud_calls: _CloudCalls) -> None:
    path = tmp_path / ".local" / "bin" / "tool"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"new-version")
    remote_root = tmp_path / "remote"
    previous_upload = remote_root / "myhome" / "linux" / ".local" / "bin" / "tool"
    previous_upload.parent.mkdir(parents=True)
    previous_upload.write_bytes(b"old-version")

    app_upload.upload_app(path, expected_sha256=sha256(b"new-version").hexdigest())

    request = cloud_calls.requests[0]
    destination = remote_root / request.destination
    destination.parent.mkdir(parents=True)
    destination.write_bytes(request.contents)
    assert destination.read_bytes() == b"new-version"
    assert previous_upload.read_bytes() == b"old-version"


def test_upload_command_uses_content_addressed_path(app_path: Path, cloud_calls: _CloudCalls) -> None:
    result = CliRunner().invoke(security_cli.get_app(), ["upload", str(app_path)])

    assert result.exit_code == 0, result.output
    assert result.output.strip() == "https://example.test/shared-binary"
    expected_hash = sha256(app_path.read_bytes()).hexdigest()
    assert cloud_calls.requests[0].destination == Path("myhome/security/linux/.local/bin/tool") / expected_hash / "tool.exe"


def test_hash_mismatch_prevents_remote_config_lookup_and_upload(app_path: Path, cloud_calls: _CloudCalls) -> None:
    expected_hash = sha256(b"scanned-older-version").hexdigest()

    with pytest.raises(ValueError):
        app_upload.upload_app(app_path, expected_sha256=expected_hash)

    cloud_calls.remote.assert_not_called()
    cloud_calls.upload.assert_not_called()


def test_upload_snapshot_keeps_the_hashed_bytes_if_original_changes(app_path: Path, cloud_calls: _CloudCalls) -> None:
    expected_hash = sha256(app_path.read_bytes()).hexdigest()

    def change_original() -> str:
        app_path.write_bytes(b"changed-during-upload")
        return "archive"

    cloud_calls.remote.side_effect = change_original

    assert app_upload.upload_app(app_path, expected_sha256=expected_hash) is not None

    assert cloud_calls.requests[0].contents == b"first-version"
    assert cloud_calls.requests[0].destination.parent.name == expected_hash
    assert app_path.read_bytes() == b"changed-during-upload"
    assert not cloud_calls.requests[0].snapshot.parent.exists()


def test_remote_failure_propagates_and_removes_snapshot(app_path: Path, cloud_calls: _CloudCalls) -> None:
    cloud_calls.failure = CalledProcessError(returncode=1, cmd=["rclone", "copyto"])

    with pytest.raises(CalledProcessError):
        app_upload.upload_app(app_path, expected_sha256=None)

    assert len(cloud_calls.requests) == 1
    assert not cloud_calls.requests[0].snapshot.parent.exists()
    assert app_path.read_bytes() == b"first-version"


def test_missing_share_url_fails_and_removes_snapshot(app_path: Path, cloud_calls: _CloudCalls) -> None:
    cloud_calls.share_url = None

    with pytest.raises(RuntimeError, match="No sharing URL returned"):
        app_upload.upload_app(app_path, expected_sha256=None)

    assert len(cloud_calls.requests) == 1
    assert not cloud_calls.requests[0].snapshot.parent.exists()
