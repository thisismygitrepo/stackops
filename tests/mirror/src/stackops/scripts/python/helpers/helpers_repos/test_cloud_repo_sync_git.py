import io
import sys
from pathlib import Path

import pytest
import typer
from git.repo import Repo
from rich.console import Console

from stackops.scripts.python.helpers.helpers_repos import cloud_repo_sync_git


class TerminalInput(io.StringIO):
    def isatty(self) -> bool:
        return True


def fail_prompt(_label: str, default: str | None, type: type[str]) -> str:
    raise AssertionError(f"Prompted despite non-interactive mode: {default} {type}")


def test_missing_git_identity_stops_without_prompting_in_a_terminal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STACKOPS_NON_INTERACTIVE", "1")
    monkeypatch.setattr(sys, "stdin", TerminalInput())
    monkeypatch.setattr(sys, "stdout", TerminalInput())
    monkeypatch.setattr(cloud_repo_sync_git, "_has_git_identity", lambda repo: False)
    monkeypatch.setattr(typer, "prompt", fail_prompt)
    output = io.StringIO()
    with pytest.raises(typer.Exit) as exit_info:
        cloud_repo_sync_git.ensure_git_identity(repo=Repo.init(tmp_path), console=Console(file=output))
    assert exit_info.value.exit_code == 1
    assert "configure user.name and user.email" in output.getvalue().replace("\n", " ")
