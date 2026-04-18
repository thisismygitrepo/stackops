from __future__ import annotations

from pathlib import Path
from typing import cast

from stackops.cluster.sessions_managers.windows_terminal.wt_utils.process_monitor import WTProcessMonitor
from stackops.cluster.sessions_managers.windows_terminal.wt_utils.session_manager import WTSessionManager
from stackops.cluster.sessions_managers.windows_terminal.wt_utils.status_reporter import WTStatusReporter
from stackops.utils.schemas.layouts.layout_types import TabConfig


class _FakeProcessMonitor:
    def __init__(self) -> None:
        self.location_name = "local"
        self.commands_status: dict[str, dict[str, object]] = {}
        self.single_status: dict[str, object] = {}
        self.windows_info: dict[str, object] = {}

    def check_all_commands_status(self, tabs: list[TabConfig]) -> dict[str, dict[str, object]]:
        assert len(tabs) == 2
        return self.commands_status

    def check_command_status(self, tab_name: str, tabs: list[TabConfig]) -> dict[str, object]:
        assert any(tab["tabName"] == tab_name for tab in tabs)
        return dict(self.single_status)

    def get_windows_terminal_windows(self) -> dict[str, object]:
        return self.windows_info


class _FakeSessionManager:
    def __init__(self) -> None:
        self.session_name = "alpha"
        self.wt_status: dict[str, object] = {}
        self.version_info: dict[str, object] = {}

    def check_wt_session_status(self) -> dict[str, object]:
        return self.wt_status

    def get_wt_version(self) -> dict[str, object]:
        return self.version_info


def _build_tabs() -> list[TabConfig]:
    return [
        {"tabName": "api", "startDir": str(Path("/tmp/api")), "command": "uv run api.py"},
        {"tabName": "worker", "startDir": str(Path("/tmp/worker")), "command": "uv run worker.py"},
    ]


def test_get_comprehensive_status_counts_running_commands() -> None:
    fake_monitor = _FakeProcessMonitor()
    fake_monitor.commands_status = {"api": {"running": True, "command": "uv run api.py"}, "worker": {"running": False, "command": "uv run worker.py"}}
    fake_manager = _FakeSessionManager()
    fake_manager.wt_status = {"session_exists": True, "wt_running": True, "location": "local"}
    reporter = WTStatusReporter(cast(WTProcessMonitor, fake_monitor), cast(WTSessionManager, fake_manager))

    status = reporter.get_comprehensive_status(_build_tabs())

    assert status["summary"] == {"total_commands": 2, "running_commands": 1, "stopped_commands": 1, "session_healthy": True, "location": "local"}


def test_generate_status_summary_uses_overview_counts() -> None:
    fake_monitor = _FakeProcessMonitor()
    fake_monitor.commands_status = {"api": {"running": True, "command": "uv run api.py"}, "worker": {"running": True, "command": "uv run worker.py"}}
    fake_monitor.windows_info = {"success": True, "windows": [{"Id": 1}, {"Id": 2}, {"Id": 3}]}
    fake_manager = _FakeSessionManager()
    fake_manager.wt_status = {"session_exists": True, "wt_running": True, "location": "local"}
    fake_manager.version_info = {"success": True, "version": "1.2.3"}
    reporter = WTStatusReporter(cast(WTProcessMonitor, fake_monitor), cast(WTSessionManager, fake_manager))

    summary = reporter.generate_status_summary(_build_tabs())

    assert summary["session_name"] == "alpha"
    assert summary["all_commands_running"] is True
    assert summary["wt_windows_count"] == 3
    assert summary["wt_version"] == "1.2.3"


def test_check_tab_specific_status_adds_tab_configuration_for_existing_tab() -> None:
    fake_monitor = _FakeProcessMonitor()
    fake_monitor.single_status = {"status": "running", "running": True, "command": "uv run api.py", "tab_name": "api"}
    fake_manager = _FakeSessionManager()
    reporter = WTStatusReporter(cast(WTProcessMonitor, fake_monitor), cast(WTSessionManager, fake_manager))

    result = reporter.check_tab_specific_status("api", _build_tabs())

    assert result["running"] is True
    assert result["tab_config"] == {"working_directory": "/tmp/api", "command": "uv run api.py"}


def test_check_tab_specific_status_rejects_unknown_tab_before_monitor_lookup() -> None:
    fake_monitor = _FakeProcessMonitor()
    fake_manager = _FakeSessionManager()
    reporter = WTStatusReporter(cast(WTProcessMonitor, fake_monitor), cast(WTSessionManager, fake_manager))

    result = reporter.check_tab_specific_status("missing", _build_tabs())

    assert result == {"error": "Tab 'missing' not found in configuration", "tab_name": "missing"}
