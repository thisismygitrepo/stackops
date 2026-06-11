import subprocess

import pytest

import stackops.utils.rclone as rclone
from stackops.scripts.python.helpers.helpers_cloud.cloud_copy import _resolve_share_options


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
