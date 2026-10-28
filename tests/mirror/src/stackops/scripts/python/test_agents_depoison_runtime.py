import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Literal

import pytest
from typer.testing import CliRunner

from stackops.scripts.python import agents, agents_depoison
from stackops.scripts.python.helpers.helpers_agents.agents_doctor import tui_launch
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_scope import CleanupScope


def test_agents_help_starts_without_tomlkit() -> None:
    source = """
import sys

sys.modules["tomlkit"] = None

from typer.testing import CliRunner
from stackops.scripts.python import agents

app = agents.get_app()
for arguments in (["--help"], ["reset", "--help"], ["doctor", "--help"]):
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
def test_reset_propagates_worker_exit_status(returncode: int, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def capture_worker(command: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        assert command[:-1] == ["uv", "run", "--no-project", "--python", sys.executable, "--with", "tomlkit", "python", "-c"]
        assert check is False
        calls.append(command)
        return subprocess.CompletedProcess(args=command, returncode=returncode)

    monkeypatch.setattr(agents_depoison, "subprocess", SimpleNamespace(run=capture_worker))
    result = CliRunner().invoke(agents.get_app(), ["reset", "claude"])
    assert result.exit_code == returncode, result.output
    assert len(calls) == 1


@pytest.mark.parametrize(
    ("requested_scope", "expected_scope"),
    [("workspace", "workspace"), ("w", "workspace"), ("user", "user"), ("u", "user"), ("all", "all"), ("a", "all")],
)
def test_reset_normalizes_scope_before_launching_tui(
    requested_scope: str, expected_scope: CleanupScope, monkeypatch: pytest.MonkeyPatch,
) -> None:
    received_scopes: list[CleanupScope] = []

    def capture_launch(
        *, mode: Literal["doctor", "depoison"], agent: str, directory: str, resource: str,
        scope: CleanupScope, match: str | None, recursive: bool,
    ) -> None:
        assert mode == "depoison"
        assert agent == "claude"
        assert directory == str(Path.cwd())
        assert resource == "all" and match is None and recursive is False
        received_scopes.append(scope)

    monkeypatch.setattr(tui_launch, "launch_agent_tui", capture_launch)
    result = CliRunner().invoke(agents.get_app(), ["reset", "claude", "--scope", requested_scope, "--tui"])
    assert result.exit_code == 0, result.output
    assert received_scopes == [expected_scope]


@pytest.mark.parametrize("scope", ["local", "global", "project", "p"])
def test_reset_rejects_previous_scope_names(scope: str) -> None:
    result = CliRunner().invoke(agents.get_app(), ["reset", "claude", "--scope", scope])
    assert result.exit_code == 2
    assert "Invalid value" in result.output
