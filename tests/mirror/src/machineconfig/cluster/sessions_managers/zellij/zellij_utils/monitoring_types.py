from __future__ import annotations

from machineconfig.cluster.sessions_managers.zellij.zellij_utils import monitoring_types as subject


def test_command_status_runtime_schema_matches_expected_keys() -> None:
    assert subject.CommandStatus.__required_keys__ == frozenset({"status", "running", "processes", "command", "tab_name"})
    assert subject.CommandStatus.__optional_keys__ == frozenset(
        {"cwd", "error", "pid", "remote", "check_timestamp", "method", "raw_output", "verification_method"}
    )


def test_process_info_and_manager_data_keep_optional_fields_optional() -> None:
    assert subject.ProcessInfo.__required_keys__ == frozenset({"pid", "name", "cmdline", "status"})
    assert subject.ProcessInfo.__optional_keys__ == frozenset({"cmdline_str", "create_time", "is_direct_command", "verified_alive", "memory_mb"})
    assert subject.ManagerData.__required_keys__ == frozenset({"session_name", "layout_config", "layout_path"})
    assert subject.StatusRow.__required_keys__ == frozenset({"session", "tab", "running", "command", "processes"})
