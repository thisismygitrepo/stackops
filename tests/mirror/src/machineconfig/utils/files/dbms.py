from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from machineconfig.utils.files import dbms


@dataclass(slots=True)
class FakeUrl:
    drivername: str


@dataclass(slots=True)
class FakeEngine:
    url: FakeUrl


def test_get_table_identifier_formats_duckdb_catalog_schema() -> None:
    duckdb_engine = FakeEngine(url=FakeUrl(drivername="duckdb"))
    sqlite_engine = FakeEngine(url=FakeUrl(drivername="sqlite"))

    assert dbms.DBMS._get_table_identifier(duckdb_engine, "events", "catalog.analytics") == '"catalog"."analytics"."events"'
    assert dbms.DBMS._get_table_identifier(sqlite_engine, "events", "analytics") == '"analytics"."events"'
    assert dbms.DBMS._get_table_identifier(sqlite_engine, "events", None) == '"events"'


def test_to_db_and_from_db_round_trip_pickled_payloads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dbms, "DB_TMP_PATH", tmp_path.joinpath("results.sqlite"))

    dbms.to_db("events", 1, 3, {"status": "ok", "value": 7})
    restored = dbms.from_db("events")

    assert restored.height == 1
    row = restored.to_dicts()[0]
    assert row["idx"] == 1
    assert row["idx_max"] == 3
    assert row["data"] == {"status": "ok", "value": 7}


def test_read_table_returns_requested_number_of_rows(tmp_path: Path) -> None:
    engine = dbms.DBMS.make_sql_engine(path=tmp_path.joinpath("table.sqlite"))
    database = dbms.DBMS(engine=engine)
    database.execute_begin_once("""CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT NOT NULL)""")
    database.execute_begin_once("""INSERT INTO items (id, name) VALUES (1, 'a')""")
    database.execute_begin_once("""INSERT INTO items (id, name) VALUES (2, 'b')""")
    database.execute_begin_once("""INSERT INTO items (id, name) VALUES (3, 'c')""")

    rows = database.read_table(table="items", sch="main", size=2)

    database.close(sleep=0)
    assert rows.height == 2


def test_get_table_specs_includes_columns_primary_keys_and_indexes(tmp_path: Path) -> None:
    engine = dbms.DBMS.make_sql_engine(path=tmp_path.joinpath("specs.sqlite"))
    database = dbms.DBMS(engine=engine)
    database.execute_begin_once("""CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT NOT NULL)""")
    database.execute_begin_once("""CREATE INDEX idx_items_name ON items(name)""")

    specs = dbms.get_table_specs(engine=engine, table_name="items")

    database.close(sleep=0)
    categories = set(specs.get_column("category").to_list())
    assert {"column", "primary_key", "index"} <= categories
