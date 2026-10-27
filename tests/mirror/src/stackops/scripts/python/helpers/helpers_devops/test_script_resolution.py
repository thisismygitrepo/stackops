from pathlib import Path
from unittest.mock import Mock

import pytest
from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_devops import cli_scripts, script_resolution


@pytest.mark.parametrize("source", ("all", "project", "user", "library", "dynamic"))
def test_explicit_script_path_overrides_source(source: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    script_path = tmp_path / "custom.py"
    script_path.write_text("pass\n", encoding="utf-8")
    source_lookup = Mock(side_effect=AssertionError("Explicit script paths must bypass source lookup"))
    dynamic_fetch = Mock(side_effect=AssertionError("Explicit script paths must not be downloaded"))
    monkeypatch.setattr(script_resolution, "get_script_locations", source_lookup)
    monkeypatch.setattr(script_resolution, "_fetch_dynamic_script", dynamic_fetch)

    result = CliRunner().invoke(cli_scripts.get_app(), ["path", str(script_path), "--source", source])

    assert result.exit_code == 0, result.output
    assert result.output.strip() == str(script_path)
    source_lookup.assert_not_called()
    dynamic_fetch.assert_not_called()
