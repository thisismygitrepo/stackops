from unittest.mock import patch

from typer.testing import CliRunner

from machineconfig.jobs.installer.checks import security_cli
from machineconfig.scripts.python.helpers.helpers_repos import download_repo_licenses


runner = CliRunner()


class StubConsole:
    def __init__(self) -> None:
        self.calls: list[object] = []

    def print(self, value: object) -> None:
        self.calls.append(value)


def _build_hydrated_engine_row() -> dict[str, str | None]:
    return {
        "app_name": "uv",
        "version": "0.7.0",
        "scan_time": "2026-03-28 00:00",
        "app_path": "~/.local/bin/uv",
        "app_url": "",
        "engine_name": "ClamAV",
        "engine_category": "undetected",
        "engine_result": None,
    }


def _build_stored_engine_row() -> dict[str, str | None]:
    return {
        "app_name": "uv",
        "engine_name": "ClamAV",
        "engine_category": "undetected",
        "engine_result": None,
    }


def _build_app_data() -> dict[str, str | float | int | None]:
    return {
        "app_name": "uv",
        "version": "0.7.0",
        "positive_pct": 0.0,
        "flagged_engines": 0,
        "verdict_engines": 1,
        "total_engines": 1,
        "malicious_engines": 0,
        "suspicious_engines": 0,
        "harmless_engines": 0,
        "undetected_engines": 1,
        "unsupported_engines": 0,
        "timeout_engines": 0,
        "failure_engines": 0,
        "other_engines": 0,
        "notes": "",
        "scan_time": "2026-03-28 00:00",
        "app_path": "~/.local/bin/uv",
        "app_url": "",
    }


def test_repo_licenses_command_passes_github_token() -> None:
    with patch.object(download_repo_licenses, "run_download") as run_download:
        result = runner.invoke(security_cli.get_app(), ["repo-licenses", "--github-token", "token-value"])

    assert result.exit_code == 0
    run_download.assert_called_once_with(github_token="token-value")


def test_repo_licenses_command_surfaces_missing_token_error() -> None:
    with patch.object(download_repo_licenses, "run_download", side_effect=RuntimeError("missing token")):
        result = runner.invoke(security_cli.get_app(), ["repo-licenses"])

    assert result.exit_code == 2
    assert "missing token" in result.output


def test_report_command_defaults_to_full_engine_view() -> None:
    console = StubConsole()
    hydrated_engine_row = _build_hydrated_engine_row()
    stored_engine_row = _build_stored_engine_row()

    with (
        patch.object(security_cli, "_console", return_value=console),
        patch.object(security_cli, "load_filtered_report_rows", return_value=([], [stored_engine_row], [], [hydrated_engine_row])),
        patch("machineconfig.jobs.installer.checks.report_utils.build_engine_results_table", return_value="ENGINE_TABLE"),
    ):
        result = runner.invoke(security_cli.get_app(), ["report"])

    assert result.exit_code == 0
    assert console.calls == ["ENGINE_TABLE"]


def test_report_command_app_summary_view_remains_available() -> None:
    console = StubConsole()
    app_data = _build_app_data()

    with (
        patch.object(security_cli, "_console", return_value=console),
        patch.object(security_cli, "load_filtered_report_rows", return_value=([], [], [app_data], [])),
        patch("machineconfig.jobs.installer.checks.report_utils.build_summary_group", return_value="SUMMARY_GROUP"),
    ):
        result = runner.invoke(security_cli.get_app(), ["report", "--view", "app-summary"])

    assert result.exit_code == 0
    assert console.calls == ["SUMMARY_GROUP"]
