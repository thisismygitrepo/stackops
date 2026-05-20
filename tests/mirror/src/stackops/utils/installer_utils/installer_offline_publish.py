from pathlib import Path
import json

import pytest

from stackops.utils.installer_utils import installer_offline_publish


def test_resolve_url_map_path_uses_path_reference(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path.joinpath("repo")
    expected_package_path = repo_root.joinpath("src/stackops/jobs/scripts_dynamic/__init__.py")
    expected_path = expected_package_path.parent.joinpath(
        installer_offline_publish.scripts_dynamic_assets.OFFLINE_INSTALLER_PATH_REFERENCE
    )
    expected_path.parent.mkdir(parents=True, exist_ok=True)
    expected_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(installer_offline_publish.scripts_dynamic_assets, "__file__", str(expected_package_path))

    resolved_path = installer_offline_publish._resolve_url_map_path()

    assert resolved_path == expected_path


@pytest.mark.parametrize(
    ("system_name", "arch_name", "target_key"),
    [
        ("Linux", "x86_64", "linux-x64"),
        ("Linux", "aarch64", "linux-arm"),
        ("Darwin", "amd64", "macos-x64"),
        ("Darwin", "arm64", "macos-arm"),
        ("Windows", "x86_64", "windows-x64"),
        ("Windows", "arm64", "windows-arm"),
    ],
)
def test_build_target_key_normalizes_platform_and_arch(system_name: str, arch_name: str, target_key: str) -> None:
    assert installer_offline_publish._build_target_key(system_name=system_name, arch_name=arch_name) == target_key


def test_publish_archive_uploads_and_updates_url_map(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path.joinpath("repo")
    package_path = repo_root.joinpath("src/stackops/jobs/scripts_dynamic/__init__.py")
    url_map_path = package_path.parent.joinpath(
        installer_offline_publish.scripts_dynamic_assets.OFFLINE_INSTALLER_PATH_REFERENCE
    )
    url_map_path.parent.mkdir(parents=True, exist_ok=True)
    url_map_path.write_text(
        json.dumps(
            {
                "linux-x64": None,
                "linux-arm": None,
                "macos-x64": None,
                "macos-arm": None,
                "windows-x64": None,
                "windows-arm": None,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    archive_path = tmp_path.joinpath("stackops-offline-installer-linux-x86_64.zip")
    archive_path.write_text("zip-bytes", encoding="utf-8")
    captured_calls: list[tuple[Path, str, Path, bool, bool, int]] = []

    def fake_to_cloud(*, local_path: Path, cloud: str, remote_path: Path, share: bool, verbose: bool, transfers: int) -> str:
        captured_calls.append((local_path, cloud, remote_path, share, verbose, transfers))
        return "https://drive.google.com/open?id=test"

    monkeypatch.setattr(installer_offline_publish.scripts_dynamic_assets, "__file__", str(package_path))
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
    assert json.loads(url_map_path.read_text(encoding="utf-8")) == {
        "linux-x64": "https://drive.google.com/open?id=test",
        "linux-arm": None,
        "macos-x64": None,
        "macos-arm": None,
        "windows-x64": None,
        "windows-arm": None,
    }
    assert [(result.label, result.status) for result in step_results] == [
        ("cloud upload", "included"),
        ("download url map", "included"),
    ]
