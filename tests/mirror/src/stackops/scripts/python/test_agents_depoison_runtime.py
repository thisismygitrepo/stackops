import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from stackops.scripts.python import agents, agents_depoison


def test_agents_help_starts_without_tomlkit() -> None:
    source = """
import sys

sys.modules["tomlkit"] = None

from typer.testing import CliRunner
from stackops.scripts.python import agents

app = agents.get_app()
for arguments in (["--help"], ["depoison", "--help"], ["doctor", "--help"]):
    result = CliRunner().invoke(app, arguments)
    assert result.exit_code == 0, result.output
assert sys.modules["tomlkit"] is None
assert "stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_plan" not in sys.modules
"""
    result = subprocess.run(
        ["uv", "run", "--no-project", "--python", sys.executable, "python", "-c", source],
        cwd=Path(__file__).resolve().parents[6],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("returncode", [0, 1, 2, 127])
def test_depoison_propagates_worker_exit_status(returncode: int, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def capture_worker(command: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        assert command[:-1] == ["uv", "run", "--no-project", "--python", sys.executable, "--with", "tomlkit", "python", "-c"]
        assert check is False
        calls.append(command)
        return subprocess.CompletedProcess(args=command, returncode=returncode)

    monkeypatch.setattr(agents_depoison, "subprocess", SimpleNamespace(run=capture_worker))
    result = CliRunner().invoke(agents.get_app(), ["depoison", "claude"])
    assert result.exit_code == returncode, result.output
    assert len(calls) == 1
