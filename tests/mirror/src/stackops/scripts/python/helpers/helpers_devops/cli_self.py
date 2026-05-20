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
    repo_root = tmp_path.joinpath("repo")
    repo_package_path = repo_root.joinpath("src", "stackops", "jobs", "scripts_dynamic", "__init__.py")
    repo_package_path.parent.mkdir(parents=True)
    repo_package_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(cli_self, "_developer_repo_root", lambda: repo_root)
    monkeypatch.setattr("stackops.jobs.scripts_dynamic.__file__", str(repo_package_path))
    monkeypatch.setattr("stackops.utils.path_reference.LIBRARY_ROOT", repo_root.joinpath("src", "stackops"))

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


def test_build_installer_expands_user_in_output_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: list[installer_offline.OfflineInstallerOptions] = []
    fake_home = tmp_path.joinpath("home")
    monkeypatch.setenv("HOME", str(fake_home))

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

    result = CliRunner().invoke(cli_self.get_app(), ["build-installer", "--output-root", "~/exports"])

    assert result.exit_code == 0
    assert captured == [
        installer_offline.OfflineInstallerOptions(
            output_root=fake_home.joinpath("exports"),
            include_configs=True,
            include_uv_bundle=True,
            keep_unpacked=False,
            upload_to_cloud=False,
        )
    ]


def test_build_installer_rejects_upload_when_url_map_is_not_repo_backed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: list[installer_offline.OfflineInstallerOptions] = []
    repo_root = tmp_path.joinpath("repo")
    repo_root.joinpath("src", "stackops", "jobs", "scripts_dynamic").mkdir(parents=True)
    installed_package_path = tmp_path.joinpath("site-packages", "stackops", "jobs", "scripts_dynamic", "__init__.py")
    installed_package_path.parent.mkdir(parents=True)
    installed_package_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(cli_self, "_developer_repo_root", lambda: repo_root)
    monkeypatch.setattr("stackops.jobs.scripts_dynamic.__file__", str(installed_package_path))
    monkeypatch.setattr("stackops.utils.path_reference.LIBRARY_ROOT", tmp_path.joinpath("site-packages", "stackops"))

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

    result = CliRunner().invoke(cli_self.get_app(), ["build-installer", "--upload-to-cloud"])

    assert result.exit_code == 1
    assert "requires an editable install backed by ~/code/stackops" in result.stdout
    assert captured == []


def test_readme_uses_installed_package_metadata_when_developer_repo_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    rendered_markdown: list[str] = []

    class FakeMetadata:
        def get_payload(self) -> str:
            return "# installed readme\n"

    class FakeConsole:
        def print(self, rendered: str) -> None:
            rendered_markdown.append(rendered)

    def fake_markdown(text: str) -> str:
        return text

    monkeypatch.setattr(cli_self, "_developer_repo_root", lambda: None)
    monkeypatch.setattr("importlib.metadata.metadata", lambda package_name: FakeMetadata())
    monkeypatch.setattr("rich.console.Console", FakeConsole)
    monkeypatch.setattr("rich.markdown.Markdown", fake_markdown)

    cli_self.readme()

    assert rendered_markdown == ["# installed readme\n"]
