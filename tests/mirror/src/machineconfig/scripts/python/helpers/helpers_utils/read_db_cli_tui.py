from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from machineconfig.scripts.python.helpers.helpers_utils import read_db_cli_tui as module


def test_find_files_obeys_recursive_flag(tmp_path: Path) -> None:
    top_level = tmp_path.joinpath("top.duckdb")
    top_level.write_text("", encoding="utf-8")
    nested = tmp_path.joinpath("nested", "inner.duckdb")
    nested.parent.mkdir(parents=True)
    nested.write_text("", encoding="utf-8")

    find_files = cast(Callable[[str, Path, bool], list[Path]], getattr(module, "_find_files"))
    flat_result = find_files("*.duckdb", tmp_path, False)
    recursive_result = find_files("*.duckdb", tmp_path, True)

    assert flat_result == [top_level.resolve()]
    assert recursive_result == sorted([top_level.resolve(), nested.resolve()])


def test_validate_backend_rejects_unsupported_duckdb_backend(tmp_path: Path) -> None:
    duckdb_path = tmp_path.joinpath("warehouse.duckdb")
    duckdb_path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="does not support DuckDB"):
        validate_backend = cast(Callable[[str, list[Path]], None], getattr(module, "_validate_backend"))
        validate_backend("lazysql", [duckdb_path.resolve()])


def test_app_rejects_path_and_find_together() -> None:
    with pytest.raises(ValueError, match="either `path` or `find`"):
        module.app(path="db.sqlite", find="*.sqlite")


def test_app_builds_harlequin_command_for_multiple_matches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    first = tmp_path.joinpath("a.duckdb")
    second = tmp_path.joinpath("sub", "b.duckdb")
    second.parent.mkdir(parents=True)
    first.write_text("", encoding="utf-8")
    second.write_text("", encoding="utf-8")
    commands: list[list[str]] = []

    monkeypatch.setattr(module, "_launch_interactive_command", lambda command: commands.append(command.copy()))

    module.app(find="*.duckdb", find_root=str(tmp_path), recursive=True, backend="harlequin", read_only=True, theme="nord", limit=25)

    assert commands == [
        [
            "harlequin",
            "--adapter",
            "duckdb",
            "--read-only",
            "--theme",
            "nord",
            "--limit",
            "25",
            str(first.resolve()),
            str(second.resolve()),
        ]
    ]


def test_app_defaults_to_harlequin_read_only_for_sqlite_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sqlite_path = tmp_path.joinpath("demo.sqlite")
    sqlite_path.write_text("", encoding="utf-8")
    commands: list[list[str]] = []

    monkeypatch.setattr(module, "_launch_interactive_command", lambda command: commands.append(command.copy()))

    module.app(path=str(sqlite_path))

    assert commands == [["harlequin", "--adapter", "sqlite", "--read-only", str(sqlite_path.resolve())]]


def test_app_rejects_unverified_read_only_backend_for_local_files(tmp_path: Path) -> None:
    sqlite_path = tmp_path.joinpath("demo.sqlite")
    sqlite_path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="does not provide a verified read-only mode"):
        module.app(path=str(sqlite_path), backend="rainfrog")


def test_app_allows_explicit_read_write_rainfrog_for_sqlite_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sqlite_path = tmp_path.joinpath("demo.sqlite")
    sqlite_path.write_text("", encoding="utf-8")
    commands: list[list[str]] = []

    monkeypatch.setattr(module, "_launch_interactive_command", lambda command: commands.append(command.copy()))

    module.app(path=str(sqlite_path), backend="rainfrog", read_only=False)

    assert commands == [["rainfrog", "--driver", "sqlite", "--database", str(sqlite_path.resolve())]]
