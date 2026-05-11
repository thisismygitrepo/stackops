from pathlib import Path

import pytest

from stackops.utils.installer_utils import installer_offline_publish


@pytest.mark.parametrize(
    ("system_name", "arch_name", "relative_path"),
    [
        ("Linux", "x86_64", "src/stackops/jobs/scripts/bash_scripts/download-stackops-offline-installer-linux-x64.sh"),
        ("Linux", "aarch64", "src/stackops/jobs/scripts/bash_scripts/download-stackops-offline-installer-linux-arm.sh"),
        ("Darwin", "amd64", "src/stackops/jobs/scripts/bash_scripts/download-stackops-offline-installer-macos-x64.sh"),
        ("Darwin", "arm64", "src/stackops/jobs/scripts/bash_scripts/download-stackops-offline-installer-macos-arm.sh"),
        ("Windows", "x86_64", "src/stackops/jobs/scripts/powershell_scripts/download-stackops-offline-installer-windows-x64.ps1"),
        ("Windows", "arm64", "src/stackops/jobs/scripts/powershell_scripts/download-stackops-offline-installer-windows-arm.ps1"),
    ],
)
def test_resolve_download_script_path_uses_platform_specific_script(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    system_name: str,
    arch_name: str,
    relative_path: str,
) -> None:
    repo_root = tmp_path.joinpath("repo")
    expected_path = repo_root.joinpath(relative_path)
    expected_path.parent.mkdir(parents=True, exist_ok=True)
    expected_path.write_text("<URL>\n", encoding="utf-8")
    monkeypatch.setattr(installer_offline_publish, "_resolve_repo_root", lambda: repo_root)

    resolved_path = installer_offline_publish._resolve_download_script_path(system_name=system_name, arch_name=arch_name)

    assert resolved_path == expected_path


def test_publish_archive_uploads_and_updates_matching_script(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path.joinpath("repo")
    script_path = repo_root.joinpath("src/stackops/jobs/scripts/bash_scripts/download-stackops-offline-installer-linux-x64.sh")
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text("<URL>\n", encoding="utf-8")
    archive_path = tmp_path.joinpath("stackops-offline-installer-linux-x86_64.zip")
    archive_path.write_text("zip-bytes", encoding="utf-8")
    captured_calls: list[tuple[Path, str, Path, bool, bool, int]] = []

    def fake_to_cloud(*, local_path: Path, cloud: str, remote_path: Path, share: bool, verbose: bool, transfers: int) -> str:
        captured_calls.append((local_path, cloud, remote_path, share, verbose, transfers))
        return "https://drive.google.com/open?id=test"

    monkeypatch.setattr(installer_offline_publish, "_resolve_repo_root", lambda: repo_root)
    monkeypatch.setattr(installer_offline_publish.rclone_wrapper, "to_cloud", fake_to_cloud)

    step_results = installer_offline_publish.publish_archive(
        archive_path=archive_path,
        system_name="Linux",
        arch_name="x86_64",
    )

    assert captured_calls == [
        (
            archive_path,
            "gdp",
            Path("/stackops/stackops-offline-installer-linux-x86_64.zip"),
            True,
            True,
            10,
        )
    ]
    assert archive_path.with_suffix(".share_url_gdp").read_text(encoding="utf-8") == "https://drive.google.com/open?id=test"
    assert script_path.read_text(encoding="utf-8") == (
        "utils file download --decompress --output-dir ~/tmp_results/installer/stackops-offline-installer "
        "'https://drive.google.com/open?id=test'\n"
    )
    assert [(result.label, result.status) for result in step_results] == [
        ("cloud upload", "included"),
        ("download script", "included"),
    ]
