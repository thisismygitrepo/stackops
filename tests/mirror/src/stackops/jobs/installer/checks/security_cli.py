from pathlib import Path

from typer.testing import CliRunner

from stackops.jobs.installer.checks import security_cli


def test_list_apps_prints_table_for_matching_apps(monkeypatch) -> None:
    def fake_collect_apps_to_scan(app_names: list[str] | None) -> list[tuple[Path, str | None]]:
        assert app_names == ["demo"]
        return [(Path("/tmp/demo"), "1.2.3")]

    monkeypatch.setattr("stackops.jobs.installer.checks.check_installations.collect_apps_to_scan", fake_collect_apps_to_scan)

    result = CliRunner().invoke(security_cli.get_app(), ["list", "demo"])

    assert result.exit_code == 0
    assert "demo" in result.stdout
    assert "1.2.3" in result.stdout


def test_list_apps_reports_missing_filtered_apps(monkeypatch) -> None:
    def fake_collect_apps_to_scan(app_names: list[str] | None) -> list[tuple[Path, str | None]]:
        assert app_names == ["missing-app"]
        return []

    monkeypatch.setattr("stackops.jobs.installer.checks.check_installations.collect_apps_to_scan", fake_collect_apps_to_scan)

    result = CliRunner().invoke(security_cli.get_app(), ["list", "missing-app"])

    assert result.exit_code == 1
    assert """No installed CLI apps matched: missing-app""" in result.output


def test_list_apps_reports_no_installed_apps(monkeypatch) -> None:
    def fake_collect_apps_to_scan(app_names: list[str] | None) -> list[tuple[Path, str | None]]:
        assert app_names is None
        return []

    monkeypatch.setattr("stackops.jobs.installer.checks.check_installations.collect_apps_to_scan", fake_collect_apps_to_scan)

    result = CliRunner().invoke(security_cli.get_app(), ["list"])

    assert result.exit_code == 1
    assert "No installed CLI apps found." in result.output


def test_install_exits_non_zero_when_install_fails(monkeypatch) -> None:
    def fake_download_safe_apps(name: str) -> bool:
        assert name == "demo"
        return False

    monkeypatch.setattr("stackops.jobs.installer.checks.install_utils.download_safe_apps", fake_download_safe_apps)

    result = CliRunner().invoke(security_cli.get_app(), ["install", "demo"])

    assert result.exit_code == 1


def test_install_returns_zero_when_install_succeeds(monkeypatch) -> None:
    def fake_download_safe_apps(name: str) -> bool:
        assert name == "demo"
        return True

    monkeypatch.setattr("stackops.jobs.installer.checks.install_utils.download_safe_apps", fake_download_safe_apps)

    result = CliRunner().invoke(security_cli.get_app(), ["install", "demo"])

    assert result.exit_code == 0
