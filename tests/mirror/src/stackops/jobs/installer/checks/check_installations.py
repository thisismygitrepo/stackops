# pyright: reportPrivateUsage=false

from __future__ import annotations

from contextlib import AbstractContextManager, nullcontext
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

from stackops.jobs.installer.checks import check_installations

if TYPE_CHECKING:
    from stackops.utils.path_extended import PathExtended


class FakeConsole:
    def __init__(self) -> None:
        self.messages: list[object] = []

    def print(self, message: object) -> None:
        self.messages.append(message)

    def rule(self, message: str) -> None:
        self.messages.append(message)

    def status(self, _message: str) -> AbstractContextManager[None]:
        return nullcontext()


class FakeProgress:
    def __init__(self, *args: object, console: object, **kwargs: object) -> None:
        self.console = console

    def add_task(self, description: str, total: int) -> int:
        assert description == "[cyan]Scanning apps..."
        assert total >= 0
        return 1

    def update(self, task_id: int, description: str) -> None:
        assert task_id == 1
        assert description

    def advance(self, task_id: int) -> None:
        assert task_id == 1

    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None


class FakeLive:
    def __init__(self, renderable: object, console: object, refresh_per_second: int) -> None:
        self.renderable = renderable
        self.console = console
        self.refresh_per_second = refresh_per_second
        self.updates: list[object] = []

    def __enter__(self) -> FakeLive:
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: object | None) -> None:
        return None

    def update(self, renderable: object) -> None:
        self.updates.append(renderable)


def test_build_version_lookup_reads_only_visible_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "alpha.txt").write_text("1.2.3\n", encoding="utf-8")
    (tmp_path / ".hidden").write_text("ignore", encoding="utf-8")
    (tmp_path / "dir").mkdir()

    monkeypatch.setattr(check_installations, "INSTALL_VERSION_ROOT", tmp_path)

    assert check_installations._build_version_lookup() == {"alpha": "1.2.3"}


def test_collect_apps_to_scan_filters_requested_names(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_console = FakeConsole()
    monkeypatch.setattr(check_installations, "console", fake_console)
    monkeypatch.setattr(check_installations, "get_installed_cli_apps", lambda: [Path("/tmp/Foo"), Path("/tmp/bar"), Path("/tmp/baz")])
    monkeypatch.setattr(check_installations, "_build_version_lookup", lambda: {"Foo": "1.0.0", "bar": "2.0.0"})

    apps_to_scan = check_installations.collect_apps_to_scan([" foo ", "BAR"])

    assert [(app_path.stem, version) for app_path, version in apps_to_scan] == [("Foo", "1.0.0"), ("bar", "2.0.0")]


def test_scan_apps_with_vt_returns_fallback_records_when_credentials_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_console = FakeConsole()
    monkeypatch.setattr(check_installations, "console", fake_console)
    monkeypatch.setattr(check_installations, "Progress", FakeProgress)
    monkeypatch.setattr(check_installations, "Live", FakeLive)

    def fake_get_vt_client() -> object:
        raise FileNotFoundError("missing VT credentials")

    monkeypatch.setattr(check_installations, "get_vt_client", fake_get_vt_client)

    apps_to_scan = cast(
        "list[tuple[PathExtended, str | None]]",
        [(cast("PathExtended", Path("/tmp/alpha")), "1.0.0"), (cast("PathExtended", Path("/tmp/beta")), None)],
    )
    records = check_installations.scan_apps_with_vt(apps_to_scan)

    assert [record["app_data"]["app_name"] for record in records] == ["alpha", "beta"]
    assert all(record["app_data"]["notes"] == "VirusTotal credentials missing." for record in records)
    assert all(record["app_data"]["positive_pct"] is None for record in records)


def test_write_reports_writes_app_and_engine_csvs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app_metadata_path = tmp_path / "apps.csv"
    engine_results_path = tmp_path / "engines.csv"
    monkeypatch.setattr(check_installations, "APP_METADATA_PATH", app_metadata_path)
    monkeypatch.setattr(check_installations, "ENGINE_RESULTS_PATH", engine_results_path)

    scan_record = check_installations.build_scan_record(
        app_path=cast("PathExtended", Path("/tmp/tool")),
        version="1.2.3",
        scan_time="2026-04-12 10:00",
        app_url="https://example.test/tool",
        scan_summary={
            "positive_pct": 0.0,
            "flagged_engines": 0,
            "verdict_engines": 2,
            "total_engines": 4,
            "malicious_engines": 0,
            "suspicious_engines": 0,
            "harmless_engines": 2,
            "undetected_engines": 2,
            "unsupported_engines": 0,
            "timeout_engines": 0,
            "failure_engines": 0,
            "other_engines": 0,
            "notes": "clean",
        },
        scan_results=[{"engine_name": "A", "category": "harmless", "result": "ok"}, {"engine_name": "B", "category": "undetected", "result": None}],
        fallback_notes="fallback",
    )

    result_paths = check_installations.write_reports([scan_record])

    assert result_paths == (app_metadata_path, engine_results_path)
    assert "app_name,version,scan_time,app_path,app_url,scan_summary_available,notes" in app_metadata_path.read_text(encoding="utf-8")
    assert "tool,1.2.3,2026-04-12 10:00,/tmp/tool,https://example.test/tool,True,clean" in app_metadata_path.read_text(encoding="utf-8")
    assert "app_name,engine_name,engine_category,engine_result" in engine_results_path.read_text(encoding="utf-8")
    assert "tool,A,harmless,ok" in engine_results_path.read_text(encoding="utf-8")


def test_scan_installed_apps_skips_writing_when_recording_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_console = FakeConsole()
    monkeypatch.setattr(check_installations, "console", fake_console)
    monkeypatch.setattr(check_installations, "collect_apps_to_scan", lambda app_names: [(Path("/tmp/tool"), "1.0.0")])
    monkeypatch.setattr(check_installations, "build_summary_group", lambda app_data_list: "summary")

    scan_record = check_installations.build_scan_record(
        app_path=cast("PathExtended", Path("/tmp/tool")),
        version="1.0.0",
        scan_time="2026-04-12 10:30",
        app_url="",
        scan_summary=None,
        scan_results=[],
        fallback_notes="no summary",
    )
    monkeypatch.setattr(check_installations, "scan_apps_with_vt", lambda apps_to_scan: [scan_record])

    def fail_write_reports(scan_records: list[object]) -> tuple[Path, Path]:
        raise AssertionError(f"write_reports should not run: {scan_records!r}")

    monkeypatch.setattr(check_installations, "write_reports", fail_write_reports)

    app_data_list = check_installations.scan_installed_apps(None, write_reports_to_repo=False)

    assert [item["app_name"] for item in app_data_list] == ["tool"]
    assert "summary" in fake_console.messages
    assert "[yellow]Scan results were not saved to the repo reports.[/yellow]" in fake_console.messages
