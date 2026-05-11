from pathlib import Path

import pytest
from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_devops import cli_self
from stackops.utils.installer_utils import installer_offline


def test_build_installer_help_lists_options() -> None:
    result = CliRunner().invoke(cli_self.get_app(), ["build-installer", "--help"])

    assert result.exit_code == 0
    assert "--output-root" in result.stdout
    assert "--include-configs" in result.stdout
    assert "--include-uv-bundle" in result.stdout
    assert "--keep-unpacked" in result.stdout
    assert "--upload-to-cloud" in result.stdout


def test_build_installer_passes_explicit_options(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: list[installer_offline.OfflineInstallerOptions] = []

    def fake_export(*, options: installer_offline.OfflineInstallerOptions, console: object) -> installer_offline.OfflineInstallerReport:
        del console
        captured.append(options)
        return installer_offline.OfflineInstallerReport(
            platform_name="Linux",
            arch_name="x86_64",
            output_dir=tmp_path.joinpath("installer_offline-linux-x86_64"),
            archive_path=tmp_path.joinpath("installer_offline-linux-x86_64.zip"),
            binary_results=[],
            step_results=[],
        )

    monkeypatch.setattr("stackops.utils.installer_utils.installer_offline.export", fake_export)

    result = CliRunner().invoke(
        cli_self.get_app(),
        [
            "build-installer",
            "--output-root",
            str(tmp_path),
            "--no-include-configs",
            "--no-include-uv-bundle",
            "--keep-unpacked",
            "--upload-to-cloud",
        ],
    )

    assert result.exit_code == 0
    assert captured == [
        installer_offline.OfflineInstallerOptions(
            output_root=tmp_path,
            include_configs=False,
            include_uv_bundle=False,
            keep_unpacked=True,
            upload_to_cloud=True,
        )
    ]
