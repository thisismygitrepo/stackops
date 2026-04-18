from collections.abc import Sequence
from pathlib import Path

import pytest

from stackops.settings.yazi.scripts import open_db_readonly


def test_build_command_uses_duckdb_readonly_for_duckdb_files(tmp_path: Path) -> None:
    target_path = tmp_path.joinpath("warehouse.duckdb")
    target_path.write_text("", encoding="utf-8")

    command = open_db_readonly.build_command(target_path=target_path, launch_ui=False)

    assert command == ["duckdb", "-readonly", str(target_path)]


def test_build_command_attaches_sqlite_file_read_only_for_cli(tmp_path: Path) -> None:
    target_path = tmp_path.joinpath("cache.sqlite3")
    target_path.write_text("", encoding="utf-8")

    command = open_db_readonly.build_command(target_path=target_path, launch_ui=False)

    assert command[0] == "duckdb"
    assert command[1] == "-cmd"
    assert "READ_ONLY" in command[2]
    assert "TYPE SQLITE" in command[2]
    assert command[3] == ":memory:"


@pytest.mark.parametrize("filename", ["warehouse.duckdb", "cache.sqlite3"])
def test_build_command_uses_ui_catalog_for_read_only_ui_targets(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, filename: str) -> None:
    target_path = tmp_path.joinpath(filename)
    target_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(open_db_readonly.Path, "home", lambda: Path("/home/tester"))

    command = open_db_readonly.build_command(target_path=target_path, launch_ui=True)

    assert command[:3] == ["duckdb", "-ui", "-cmd"]
    assert "READ_ONLY" in command[3]
    assert command[4] == "/home/tester/.cache/stackops/yazi/duckdb-ui-catalog.duckdb"


def test_main_maps_runtime_errors_to_exit_codes(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def fake_exec_command(command: Sequence[str]) -> None:
        raise FileNotFoundError(command[0])

    monkeypatch.setattr(open_db_readonly, "exec_command", fake_exec_command)

    exit_code = open_db_readonly.main(arguments=["missing.duckdb"])

    assert exit_code == 1
    assert "Expected a database file" in capsys.readouterr().err
