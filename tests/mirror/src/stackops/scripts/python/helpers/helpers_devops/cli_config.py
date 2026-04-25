from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_devops import cli_config


def test_dump_ve_config_creates_sibling_schema(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    cli_config._dump_ve_config()

    yaml_path = tmp_path / ".ve.example.yaml"
    schema_path = tmp_path / ".ve.example.schema.json"
    assert schema_path.is_file()
    assert yaml_path.read_text(encoding="utf-8").startswith(
        "# yaml-language-server: $schema=./.ve.example.schema.json\n"
    )
    assert '"StackOps .ve.yaml"' in schema_path.read_text(encoding="utf-8")
