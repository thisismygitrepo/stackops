from pathlib import Path

import pytest
from sqlalchemy import text

from machineconfig.utils.files.dbms import DBMS


pytest.importorskip("duckdb")
pytest.importorskip("duckdb_engine")


def _make_duckdb(tmp_path: Path) -> tuple[DBMS, str]:
    db_path = tmp_path / "repro.duckdb"
    db = DBMS.from_local_db(path=db_path)
    with db.eng.begin() as conn:
        conn.execute(text("CREATE OR REPLACE TABLE sample (id INTEGER, value VARCHAR)"))
        conn.execute(text("DELETE FROM sample"))
        conn.execute(text("INSERT INTO sample VALUES (1, 'a'), (2, 'b')"))
    return db, "repro.main"


def test_describe_db_handles_duckdb_catalog_schema_names(tmp_path: Path) -> None:
    db, schema_name = _make_duckdb(tmp_path)

    try:
        result = db.describe_db()
    finally:
        db.close(sleep=0)

    rows = result.to_dicts()
    assert len(rows) == 1
    assert rows[0]["table"] == f"{schema_name}.sample"
    assert rows[0]["count"] == 2
    assert rows[0]["columns"] == 2
    assert rows[0]["schema"] == schema_name
    assert rows[0]["size_mb"] == pytest.approx(0.00004)


def test_get_columns_handles_duckdb_catalog_schema_names(tmp_path: Path) -> None:
    db, schema_name = _make_duckdb(tmp_path)

    try:
        columns = db.get_columns(table="sample", sch=schema_name)
    finally:
        db.close(sleep=0)

    assert columns == ["id", "value"]