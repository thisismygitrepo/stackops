from inspect import signature
from pathlib import Path

from typer.testing import CliRunner

from stackops.jobs.scripts_dynamic import download_stackops_offline_installer
from stackops.scripts.python.helpers.helpers_devops import cli_self
from stackops.utils.installer_utils import installer_offline_constants, installer_offline_publish


def test_offline_installer_defaults_live_under_stackops_config_root() -> None:
    expected_output_root = Path.home().joinpath(".config", "stackops", "offline_installers")

    assert installer_offline_constants.DEFAULT_OUTPUT_ROOT == expected_output_root
    assert signature(cli_self.export).parameters["output_root"].default == expected_output_root
    assert download_stackops_offline_installer.DEFAULT_OUTPUT_DIR == expected_output_root / "stackops-offline-installer"


def test_offline_installer_upload_mirrors_home_relative_output_path(tmp_path: Path, monkeypatch) -> None:
    captured_remote_paths: list[Path] = []
    url_map_path = tmp_path / "download_stackops_offline_installer.json"
    url_map_path.write_text("{}\n", encoding="utf-8")

    def fake_to_cloud(
        *,
        local_path: Path,
        cloud: str,
        remote_path: Path,
        share: bool,
        verbose: bool,
        transfers: int,
    ) -> str:
        _ = local_path, cloud, share, verbose, transfers
        captured_remote_paths.append(remote_path)
        return "https://drive.google.com/file/d/example/view"

    monkeypatch.setattr(installer_offline_publish.rclone_wrapper, "to_cloud", fake_to_cloud)
    monkeypatch.setattr(installer_offline_publish, "_resolve_url_map_path", lambda: url_map_path)

    archive_path = installer_offline_constants.DEFAULT_OUTPUT_ROOT / "stackops-offline-installer-linux-x86_64.zip"

    installer_offline_publish.publish_archive(archive_path=archive_path, system_name="Linux", arch_name="x86_64")

    assert captured_remote_paths == [
        Path("myhome/generic_os/.config/stackops/offline_installers/stackops-offline-installer-linux-x86_64.zip")
    ]


def test_self_download_installer_command_is_registered() -> None:
    runner = CliRunner()

    help_result = runner.invoke(cli_self.get_app(), ["download-installer", "--help"])
    alias_result = runner.invoke(cli_self.get_app(), ["D", "--help"])

    assert help_result.exit_code == 0
    assert "--target" in help_result.stdout
    assert "--output-dir" in help_result.stdout
    assert alias_result.exit_code == 0
    assert "--target" in alias_result.stdout


def test_self_download_installer_invokes_dynamic_downloader(tmp_path: Path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_download_installer(*, target_key: str | None, output_dir: Path | None) -> Path:
        captured["target_key"] = target_key
        captured["output_dir"] = output_dir
        return output_dir or tmp_path

    monkeypatch.setattr(download_stackops_offline_installer, "download_installer", fake_download_installer)

    result = CliRunner().invoke(
        cli_self.get_app(),
        ["download-installer", "--target", "linux-x64", "--output-dir", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert captured == {"target_key": "linux-x64", "output_dir": tmp_path}


def test_dynamic_downloader_supports_non_interactive_target(tmp_path: Path, monkeypatch) -> None:
    url_map = {target_key: None for target_key in download_stackops_offline_installer.KNOWN_TARGETS}
    url_map["linux-x64"] = "https://drive.google.com/file/d/example/view"
    captured: dict[str, object] = {}

    def fake_download_and_extract(*, url: str, output_dir: Path) -> None:
        captured["url"] = url
        captured["output_dir"] = output_dir

    monkeypatch.setattr(download_stackops_offline_installer, "_load_url_map", lambda: url_map)
    monkeypatch.setattr(download_stackops_offline_installer, "_download_and_extract", fake_download_and_extract)

    output_dir = tmp_path / "installer"

    resolved_output_dir = download_stackops_offline_installer.download_installer(
        target_key="linux-x64",
        output_dir=output_dir,
    )

    assert resolved_output_dir == output_dir.resolve()
    assert captured == {
        "url": "https://drive.google.com/file/d/example/view",
        "output_dir": output_dir.resolve(),
    }
