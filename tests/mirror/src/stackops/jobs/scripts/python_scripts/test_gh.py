import shlex
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from stackops.jobs.scripts.python_scripts import gh


def test_resolve_codespace_name_skips_picker_for_single_target(monkeypatch: pytest.MonkeyPatch) -> None:
    filters = gh.CodespaceFilters(repo=None, repo_owner=None, limit=30)
    target = gh.CodespaceSummary(
        name="sole-target",
        display_name="Sole target",
        repository="owner/repository",
        state="Available",
        machine="standardLinux32gb",
        last_used_at="2026-07-31T00:00:00Z",
        created_at="2026-07-30T00:00:00Z",
        owner="owner",
        raw={},
    )
    load_codespaces = Mock(return_value=[target])
    choose_labels = Mock(side_effect=AssertionError("Interactive picker must not run for one target."))
    monkeypatch.setattr(gh, "load_codespaces", load_codespaces)
    monkeypatch.setattr(gh, "choose_labels", choose_labels)

    resolved_name = gh.resolve_codespace_name(codespace=None, filters=filters, msg="Select target")

    assert resolved_name == target.name
    load_codespaces.assert_called_once_with(filters=filters)
    choose_labels.assert_not_called()


def test_exec_uses_interactive_login_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    target = gh.CodespaceSummary(
        name="sole-target",
        display_name="Sole target",
        repository="owner/repository",
        state="Available",
        machine="standardLinux32gb",
        last_used_at="2026-07-31T00:00:00Z",
        created_at="2026-07-30T00:00:00Z",
        owner="owner",
        raw={},
    )
    run_gh_stream = Mock()
    monkeypatch.setattr(gh, "load_codespaces", Mock(return_value=[target]))
    monkeypatch.setattr(gh, "run_gh_stream", run_gh_stream)
    monkeypatch.setattr(gh.sys, "stdin", Mock(isatty=Mock(return_value=True)))

    gh.exec_cmd(command="$HOME/remote-script.sh", codespace=None, repo=None, repo_owner=None, limit=30)

    run_gh_stream.assert_called_once_with(
        args=[
            "codespace",
            "ssh",
            "--codespace",
            target.name,
            "--",
            "-t",
            shlex.join(
                [
                    "env",
                    f"{gh.REMOTE_EXEC_COMMAND_ENV}=$HOME/remote-script.sh",
                    "bash",
                    "-lic",
                    gh.REMOTE_EXEC_WRAPPER,
                ]
            ),
        ]
    )


def test_remote_exec_wrapper_sources_standalone_shell_script(tmp_path: Path) -> None:
    script = tmp_path.joinpath("remote-script.sh")
    script.write_text("printf sourced", encoding="utf-8")

    result = subprocess.run(
        ["bash", "--noprofile", "--norc", "-c", gh.REMOTE_EXEC_WRAPPER],
        check=True,
        capture_output=True,
        env={gh.REMOTE_EXEC_COMMAND_ENV: str(script)},
        text=True,
    )

    assert result.stdout == "sourced"
