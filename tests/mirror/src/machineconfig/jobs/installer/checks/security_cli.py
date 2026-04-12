# pyright: reportPrivateUsage=false

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest
import typer

import machineconfig.utils.code as code_utils
from machineconfig.jobs.installer.checks import check_installations, security_cli, security_helper

if TYPE_CHECKING:
    from rich.table import Table


class FakeConsole:
    def __init__(self) -> None:
        self.messages: list[object] = []

    def print(self, message: object) -> None:
        self.messages.append(message)


def test_resolve_report_view_prefers_explicit_and_summary_modes() -> None:
    assert security_cli._resolve_report_view("stats", summarize=False) == "stats"
    assert security_cli._resolve_report_view(None, summarize=True) == "app-summary"
    assert security_cli._resolve_report_view(None, summarize=False) == "engines"


def test_scan_rejects_apps_and_path_together(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(code_utils, "run_lambda_function", lambda function, uv_with, uv_project_dir: function())

    with pytest.raises(typer.BadParameter):
        security_cli.scan(apps="alpha", path=Path("/tmp/tool"), record=None)


def test_scan_routes_path_and_installed_app_modes(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, object, bool | None]] = []
    uv_calls: list[tuple[list[str], object]] = []

    def fake_run_lambda_function(function: Callable[[], None], uv_with: list[str], uv_project_dir: object) -> None:
        uv_calls.append((uv_with, uv_project_dir))
        function()

    monkeypatch.setattr(code_utils, "run_lambda_function", fake_run_lambda_function)
    monkeypatch.setattr(security_helper, "parse_apps_argument", lambda apps: ["alpha"])
    monkeypatch.setattr(security_helper, "scan_single_path", lambda path, record: calls.append(("path", path, record)))
    monkeypatch.setattr(
        check_installations, "scan_installed_apps", lambda app_names, write_reports_to_repo: calls.append(("apps", app_names, write_reports_to_repo))
    )

    security_cli.scan(apps=None, path=Path("/tmp/tool"), record=None)
    security_cli.scan(apps="alpha", path=None, record=None)

    assert calls == [("path", Path("/tmp/tool"), False), ("apps", ["alpha"], True)]
    assert uv_calls == [(["vt-py"], None), (["vt-py"], None)]


def test_list_apps_renders_installed_apps_table(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_console = FakeConsole()
    monkeypatch.setattr(security_cli, "_console", lambda: fake_console)
    monkeypatch.setattr(check_installations, "collect_apps_to_scan", lambda app_names: [(Path("/tmp/alpha"), "1.0.0")])

    security_cli.list_apps("alpha")

    table = cast("Table", fake_console.messages[0])
    assert table.title == "Installed CLI Apps"
    assert len(table.rows) == 1


def test_upload_and_download_use_console_output(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_console = FakeConsole()
    monkeypatch.setattr(security_cli, "_console", lambda: fake_console)

    monkeypatch.setattr(check_installations, "collect_apps_to_scan", lambda app_names: [])
    monkeypatch.setattr("machineconfig.jobs.installer.checks.install_utils.upload_app", lambda path: "https://example.test/share")
    security_cli.upload(Path("/tmp/tool"))
    assert fake_console.messages[-1] == "https://example.test/share"

    monkeypatch.setattr("machineconfig.jobs.installer.checks.install_utils.upload_app", lambda path: None)
    with pytest.raises(typer.Exit) as exit_info:
        security_cli.upload(Path("/tmp/tool"))
    assert exit_info.value.exit_code == 1

    monkeypatch.setattr("machineconfig.jobs.installer.checks.install_utils.download_google_drive_file", lambda url: Path("/tmp/downloaded"))
    security_cli.download("https://example.test/file")
    assert fake_console.messages[-1] == "/tmp/downloaded"


def test_summary_delegates_to_stats_report(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, object]] = []

    def fake_report(*args: object, **kwargs: object) -> None:
        assert args == ()
        captured.append(dict(kwargs))

    monkeypatch.setattr(security_cli, "report", fake_report)

    security_cli.summary()

    assert captured == [{"view": "stats"}]


def test_report_handles_options_csv_and_empty_stats(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_console = FakeConsole()
    monkeypatch.setattr(security_cli, "_console", lambda: fake_console)
    monkeypatch.setattr(security_cli, "build_report_options_text", lambda: "opts")

    security_cli.report(view="options")
    assert fake_console.messages == ["opts"]

    with pytest.raises(typer.BadParameter):
        security_cli.report(view="stats", format_type="csv")

    monkeypatch.setattr(security_cli, "parse_apps_argument", lambda apps: ["alpha"])
    monkeypatch.setattr(security_cli, "normalize_app_names", lambda app_names: {"alpha"})
    monkeypatch.setattr(
        security_cli,
        "load_filtered_report_rows",
        lambda normalized_app_names: (
            [
                {
                    "app_name": "alpha",
                    "version": "1.0.0",
                    "scan_time": "2026-04-12 12:00",
                    "app_path": "/tmp/alpha",
                    "app_url": "",
                    "scan_summary_available": True,
                    "notes": "",
                }
            ],
            [],
            [
                {
                    "app_name": "alpha",
                    "version": "1.0.0",
                    "positive_pct": 0.0,
                    "flagged_engines": 0,
                    "verdict_engines": 1,
                    "total_engines": 1,
                    "malicious_engines": 0,
                    "suspicious_engines": 0,
                    "harmless_engines": 1,
                    "undetected_engines": 0,
                    "unsupported_engines": 0,
                    "timeout_engines": 0,
                    "failure_engines": 0,
                    "other_engines": 0,
                    "notes": "",
                    "scan_time": "2026-04-12 12:00",
                    "app_path": "/tmp/alpha",
                    "app_url": "",
                }
            ],
            [],
        ),
    )
    monkeypatch.setattr(security_cli, "render_csv_text", lambda rows, columns: "csv-data")

    security_cli.report(apps="alpha", view="apps", format_type="csv")
    assert fake_console.messages[-1] == "csv-data"

    monkeypatch.setattr(security_cli, "load_filtered_report_rows", lambda normalized_app_names: ([], [], [], []))
    with pytest.raises(typer.Exit) as exit_info:
        security_cli.report(view="stats")
    assert exit_info.value.exit_code == 1
