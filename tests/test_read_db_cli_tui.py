from unittest.mock import patch

import pytest

from machineconfig.scripts.python.helpers.helpers_utils import read_db_cli_tui


def test_rainfrog_duckdb_uses_direct_driver_args() -> None:
    with patch.object(read_db_cli_tui, "_launch_interactive_command") as launch_interactive_command:
        read_db_cli_tui.app(
            path="/tmp/example.duckdb",
            find=None,
            find_root=None,
            recursive=False,
            backend="rainfrog",
            read_only=False,
            theme=None,
            limit=None,
        )

    command = launch_interactive_command.call_args.args[0]
    assert command == ["rainfrog", "--driver", "duckdb", "--database", "/tmp/example.duckdb"]


def test_rainfrog_sqlite_uses_direct_driver_args() -> None:
    with patch.object(read_db_cli_tui, "_launch_interactive_command") as launch_interactive_command:
        read_db_cli_tui.app(
            path="/tmp/example.sqlite",
            find=None,
            find_root=None,
            recursive=False,
            backend="rainfrog",
            read_only=False,
            theme=None,
            limit=None,
        )

    command = launch_interactive_command.call_args.args[0]
    assert command == ["rainfrog", "--driver", "sqlite", "--database", "/tmp/example.sqlite"]


def test_validate_backend_lists_rainfrog_as_duckdb_capable_backend() -> None:
    with pytest.raises(ValueError) as exc_info:
        read_db_cli_tui.app(
            path="/tmp/example.duckdb",
            find=None,
            find_root=None,
            recursive=False,
            backend="lazysql",
            read_only=False,
            theme=None,
            limit=None,
        )

    assert "DuckDB-capable backends: harlequin, rainfrog, usql" in str(exc_info.value)
