from typing import cast

import pytest
from typer.testing import CliRunner

from stackops.scripts.python import devops
from stackops.scripts.python.helpers.helpers_devops import run_script


@pytest.mark.parametrize("command_name", ["execute", "e"])
def test_execute_help_does_not_search_for_help_script(monkeypatch: pytest.MonkeyPatch, command_name: str) -> None:
    def fail_if_script_lookup_runs(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("script lookup ran while rendering command help")

    monkeypatch.setattr(run_script, "run_py_script", fail_if_script_lookup_runs)

    result = CliRunner().invoke(devops.get_app(), [command_name, "--help"])

    assert result.exit_code == 0, result.output
    assert "Execute python/shell scripts" in result.output
    assert "--subprocess" in result.output
    assert "Could not find script" not in result.output


def test_execute_forwards_target_help_and_enables_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_calls: list[tuple[str, bool, list[str]]] = []

    def capture_run_py_script(**arguments: object) -> None:
        captured_calls.append(
            (
                cast(str, arguments["name"]),
                cast(bool, arguments["run_in_subprocess"]),
                cast(list[str], arguments["forwarded_args"]),
            )
        )

    monkeypatch.setattr(run_script, "run_py_script", capture_run_py_script)

    result = CliRunner().invoke(devops.get_app(), ["e", "example", "--subprocess", "--help"])

    assert result.exit_code == 0, result.output
    assert captured_calls == [("example", True, ["--help"])]
