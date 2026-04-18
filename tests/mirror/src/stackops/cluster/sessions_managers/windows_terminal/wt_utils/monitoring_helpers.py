from __future__ import annotations

import pytest

from stackops.cluster.sessions_managers.windows_terminal.wt_utils import monitoring_helpers as helpers_module


class FakeProcessMonitor:
    def __init__(self, status: dict[str, dict[str, object]]) -> None:
        self.status: dict[str, dict[str, object]] = status

    def check_all_commands_status(
        self,
        tabs: list[dict[str, object]],
    ) -> dict[str, dict[str, object]]:
        assert tabs
        return self.status


class FakeSessionManager:
    def __init__(self, status: dict[str, object]) -> None:
        self.status: dict[str, object] = status

    def check_wt_session_status(self) -> dict[str, object]:
        return self.status


class FakeManagerWithProcessMonitor:
    def __init__(
        self,
        status: dict[str, dict[str, object]],
        session_status: dict[str, object],
    ) -> None:
        self.layout_config: dict[str, object] = {
            "layoutTabs": [{"tabName": "api", "command": "python api.py"}],
        }
        self.process_monitor = FakeProcessMonitor(status)
        self.session_manager = FakeSessionManager(session_status)


class FakeManagerWithoutProcessMonitor:
    def __init__(
        self,
        status: dict[str, dict[str, object]],
        session_status: dict[str, object],
    ) -> None:
        self.layout_config: dict[str, object] = {
            "layoutTabs": [{"tabName": "worker", "command": "python worker.py"}],
        }
        self._status: dict[str, dict[str, object]] = status
        self.session_manager = FakeSessionManager(session_status)

    def check_all_commands_status(self) -> dict[str, dict[str, object]]:
        return self._status


def test_collect_status_data_from_managers_uses_available_api() -> None:
    managers: list[object] = [
        FakeManagerWithProcessMonitor(
            {"api": {"running": True, "command": "python api.py"}},
            {"wt_running": True},
        ),
        FakeManagerWithoutProcessMonitor(
            {"worker": {"running": False, "command": "python worker.py"}},
            {"wt_running": False},
        ),
    ]

    statuses = helpers_module.collect_status_data_from_managers(managers)

    assert statuses == [
        {"api": {"running": True, "command": "python api.py"}},
        {"worker": {"running": False, "command": "python worker.py"}},
    ]


def test_flatten_stop_checks_and_print_helpers(
    capsys: pytest.CaptureFixture[str],
) -> None:
    statuses = [
        {"api": {"running": True, "command": "python api.py"}},
        {"worker": {"running": False, "command": "python worker.py"}},
    ]
    managers: list[object] = [
        FakeManagerWithProcessMonitor(
            {"api": {"running": True, "command": "python api.py"}},
            {"wt_running": True},
        ),
        FakeManagerWithoutProcessMonitor(
            {"worker": {"running": False, "command": "python worker.py"}},
            {"wt_running": False},
        ),
    ]

    flattened = helpers_module.flatten_status_data(statuses)
    all_stopped = helpers_module.check_if_all_stopped(flattened)
    session_statuses = helpers_module.collect_session_statuses(managers)
    helpers_module.print_status_table(flattened)
    helpers_module.print_session_statuses(session_statuses)

    output = capsys.readouterr().out
    assert flattened == [
        {"tabName": "api", "status": {"running": True, "command": "python api.py"}},
        {"tabName": "worker", "status": {"running": False, "command": "python worker.py"}},
    ]
    assert all_stopped is False
    assert session_statuses == [{"wt_running": True}, {"wt_running": False}]
    assert "Tab: api" in output
    assert "Manager 0" in output
