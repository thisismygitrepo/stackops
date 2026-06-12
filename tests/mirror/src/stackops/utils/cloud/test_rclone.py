import re
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

import stackops.utils.cloud.rclone as rclone
from stackops.scripts.python import cloud as cloud_cli
from stackops.scripts.python.helpers.helpers_cloud import cloud_copy
from stackops.scripts.python.helpers.helpers_cloud.cloud_copy import _resolve_share_options
from stackops.utils.cloud.encryption import EncryptionMode


def test_link_maps_generic_share_options_to_onedrive_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[list[str]] = []

    def fake_run_rclone(command: list[str], *, show_command: bool, show_progress: bool) -> subprocess.CompletedProcess[str]:
        _ = show_command
        _ = show_progress
        commands.append(command)
        if command == ["rclone", "config", "dump"]:
            return subprocess.CompletedProcess(command, 0, """{"docs":{"type":"onedrive","token":"SECRET_TOKEN"}}""", "")
        return subprocess.CompletedProcess(command, 0, "https://example.test/share\n", "")

    monkeypatch.setattr(rclone, "_run_rclone", fake_run_rclone)

    share_url = rclone.link(
        target="docs:report.pdf", remote_name="docs", share_options=rclone.ShareLinkOptions(scope="organization", link_type="edit"), show_command=True
    )

    assert share_url == "https://example.test/share"
    assert commands == [
        ["rclone", "config", "dump"],
        ["rclone", "link", "--onedrive-link-scope=organization", "--onedrive-link-type=edit", "docs:report.pdf"],
    ]
    assert all("SECRET_TOKEN" not in " ".join(command) for command in commands)


def test_remote_backend_type_resolves_wrapped_remote(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_rclone(command: list[str], *, show_command: bool, show_progress: bool) -> subprocess.CompletedProcess[str]:
        _ = show_command
        _ = show_progress
        assert command == ["rclone", "config", "dump"]
        return subprocess.CompletedProcess(command, 0, """{"secure":{"type":"crypt","remote":"docs:encrypted"},"docs":{"type":"onedrive"}}""", "")

    monkeypatch.setattr(rclone, "_run_rclone", fake_run_rclone)

    assert rclone.remote_backend_type(remote_name="secure") == "onedrive"


def test_plain_public_view_share_uses_plain_link_for_other_backends(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[list[str]] = []

    def fake_run_rclone(command: list[str], *, show_command: bool, show_progress: bool) -> subprocess.CompletedProcess[str]:
        _ = show_command
        _ = show_progress
        commands.append(command)
        if command == ["rclone", "config", "dump"]:
            return subprocess.CompletedProcess(command, 0, """{"archive":{"type":"pcloud","token":"SECRET_TOKEN"}}""", "")
        return subprocess.CompletedProcess(command, 0, "https://example.test/share\n", "")

    monkeypatch.setattr(rclone, "_run_rclone", fake_run_rclone)

    share_url = rclone.link(
        target="archive:report.pdf",
        remote_name="archive",
        share_options=rclone.ShareLinkOptions(scope="anonymous", link_type="view"),
        show_command=False,
    )

    assert share_url == "https://example.test/share"
    assert commands == [["rclone", "config", "dump"], ["rclone", "link", "archive:report.pdf"]]
    assert all("SECRET_TOKEN" not in " ".join(command) for command in commands)


def test_unsupported_share_option_error_does_not_include_config_values(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_rclone(command: list[str], *, show_command: bool, show_progress: bool) -> subprocess.CompletedProcess[str]:
        _ = show_command
        _ = show_progress
        assert command == ["rclone", "config", "dump"]
        return subprocess.CompletedProcess(command, 0, """{"archive":{"type":"pcloud","token":"SECRET_TOKEN"}}""", "")

    monkeypatch.setattr(rclone, "_run_rclone", fake_run_rclone)

    with pytest.raises(rclone.RcloneConfigError) as error:
        rclone.link(
            target="archive:report.pdf",
            remote_name="archive",
            share_options=rclone.ShareLinkOptions(scope="anonymous", link_type="edit"),
            show_command=False,
        )

    assert "pcloud" in str(error.value)
    assert "SECRET_TOKEN" not in str(error.value)


def test_cloud_copy_share_options_accept_choice_aliases() -> None:
    share_options = _resolve_share_options(share_scope="o", share_type="m")

    assert share_options == rclone.ShareLinkOptions(scope="organization", link_type="embed")


def test_cloud_copy_help_uses_record_name_as_recording_trigger() -> None:
    result = CliRunner().invoke(cloud_cli.get_app(), ["copy", "--help"])

    assert result.exit_code == 0
    assert "--record-name" in result.output
    assert "--record-group" in result.output
    assert re.search(r"(?<![\w-])--record(?![\w-])", result.output) is None


def test_cloud_copy_record_name_records_upload(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source_file = tmp_path.joinpath("report.txt")
    source_file.write_text("content\n", encoding="utf-8")
    upload_calls: list[str] = []
    record_calls: list[str] = []

    def fake_to_cloud(
        *,
        local_path: Path,
        cloud: str,
        remote_path: Path,
        share: bool,
        share_options: rclone.ShareLinkOptions | None,
        verbose: bool,
        transfers: int,
    ) -> str:
        assert local_path == source_file.absolute()
        assert cloud == "docs"
        assert remote_path == Path("reports/report.txt")
        assert share
        assert share_options == rclone.ShareLinkOptions(scope=None, link_type="view")
        assert verbose
        assert transfers == 10
        upload_calls.append(f"{cloud}:{remote_path.as_posix()}")
        return "https://example.test/share"

    def fake_record_upload(
        *,
        source_path: Path,
        original_target: str,
        cloud: str,
        remote_path: Path,
        share_url: str | None,
        zip_requested: bool,
        encrypt_requested: bool,
        encryption_mode: EncryptionMode | None,
        rel2home: bool,
        record_group: str,
        record_name: str,
        record_os: str,
        expand_symbol: str,
    ) -> tuple[Path, str, bool]:
        assert source_path == source_file.absolute()
        assert original_target == "docs:reports/report.txt"
        assert cloud == "docs"
        assert remote_path == Path("reports/report.txt")
        assert share_url == "https://example.test/share"
        assert not zip_requested
        assert not encrypt_requested
        assert encryption_mode is None
        assert not rel2home
        assert record_group == "shared"
        assert record_name == "report"
        assert record_os == "linux"
        assert expand_symbol == "^"
        record_calls.append(record_name)
        return tmp_path.joinpath("data.yaml"), record_name, False

    monkeypatch.setattr(cloud_copy.rclone_wrapper, "to_cloud", fake_to_cloud)
    monkeypatch.setattr(cloud_copy, "_record_upload", fake_record_upload)

    cloud_copy.main(
        source=source_file.as_posix(),
        target="docs:reports/report.txt",
        overwrite=False,
        share_scope=None,
        share_type="v",
        record_group="shared",
        record_name="report",
        record_os="linux",
        rel2home=False,
        root="myhome",
        pwd=None,
        encrypt=False,
        encryption=None,
        zip_=False,
        os_specific=False,
    )

    assert upload_calls == ["docs:reports/report.txt"]
    assert record_calls == ["report"]


def test_share_choice_parsers_accept_aliases() -> None:
    assert rclone.parse_share_scope("a") == "anonymous"
    assert rclone.parse_share_scope("o") == "organization"
    assert rclone.parse_share_link_type("v") == "view"
    assert rclone.parse_share_link_type("e") == "edit"
    assert rclone.parse_share_link_type("m") == "embed"


def test_share_choice_parsers_reject_unknown_aliases() -> None:
    with pytest.raises(ValueError, match="anonymous, a, organization, o"):
        rclone.parse_share_scope("x")
    with pytest.raises(ValueError, match="view, v, edit, e, embed, m"):
        rclone.parse_share_link_type("x")
