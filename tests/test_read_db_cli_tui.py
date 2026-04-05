from unittest.mock import patch

import pytest

from machineconfig.scripts.python.helpers.helpers_utils import read_db_cli_tui


def test_validate_backend_accepts_rainfrog_for_duckdb_when_driver_is_available() -> None:
    with (
        patch.object(read_db_cli_tui, "_rainfrog_supports_duckdb", return_value=True),
        patch("machineconfig.utils.code.exit_then_run_shell_script") as exit_then_run_shell_script,
    ):
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

    script = exit_then_run_shell_script.call_args.args[0]
    assert 'rainfrog --url "duckdb:///tmp/example.duckdb"' in script


def test_validate_backend_rejects_rainfrog_for_duckdb_when_driver_is_unavailable() -> None:
    with (
        patch.object(read_db_cli_tui, "_rainfrog_supports_duckdb", return_value=False),
        pytest.raises(ValueError) as exc_info,
    ):
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

    assert "Installed rainfrog binary does not include DuckDB support." in str(exc_info.value)
    assert "Use harlequin or usql" in str(exc_info.value)


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
