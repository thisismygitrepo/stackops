from pathlib import Path
from typing import TypedDict

import pytest
from typer.testing import CliRunner

from stackops.scripts.python import agents_iter
from stackops.scripts.python.helpers.helpers_agents import agents_iter_rich_output


type CloseCall = tuple[str | None, bool, bool, bool, int, bool, int]
type StatusCall = tuple[str | None, bool, bool, int]
type CleanCall = tuple[Path, str | None, bool, bool, bool]


class CommandCalls(TypedDict):
    close: list[CloseCall]
    status: list[StatusCall]
    clean: list[CleanCall]


@pytest.fixture
def command_calls(monkeypatch: pytest.MonkeyPatch) -> CommandCalls:
    calls = CommandCalls(close=[], status=[], clean=[])

    def capture_close(
        *,
        workspace_id: str | None,
        all_workspaces: bool,
        interactive: bool,
        continuous: bool,
        retain_previous: int,
        dry_run: bool,
        interval_seconds: int,
    ) -> None:
        calls["close"].append((workspace_id, all_workspaces, interactive, continuous, retain_previous, dry_run, interval_seconds))

    def capture_status(*, workspace_id: str | None, all_workspaces: bool, interactive: bool, retain_previous: int) -> None:
        calls["status"].append((workspace_id, all_workspaces, interactive, retain_previous))

    def capture_clean(*, cwd: Path, workspace_id: str | None, all_workspaces: bool, interactive: bool, dry_run: bool) -> None:
        calls["clean"].append((cwd, workspace_id, all_workspaces, interactive, dry_run))

    monkeypatch.setattr(agents_iter_rich_output, "show_close_iter_workspaces_loop", capture_close)
    monkeypatch.setattr(agents_iter_rich_output, "show_iter_status", capture_status)
    monkeypatch.setattr(agents_iter_rich_output, "show_clean_agentops_cache", capture_clean)
    return calls


def test_close_help_exposes_optional_workspace_and_scope_options() -> None:
    result = CliRunner().invoke(agents_iter.get_app(), ["close", "--help"], terminal_width=160)

    assert result.exit_code == 0, result.output
    assert "[WORKSPACE_ID]" in result.output
    assert "--all" in result.output
    assert "-a" in result.output
    assert "--interactive" in result.output
    assert "-I" in result.output
    assert "--interval" in result.output
    assert "-i" in result.output


def test_close_forwards_explicit_workspace_with_defaults(command_calls: CommandCalls) -> None:
    result = CliRunner().invoke(agents_iter.get_app(), ["close", "w7"])

    assert result.exit_code == 0, result.output
    assert command_calls["close"] == [("w7", False, False, False, 3, False, 300)]


def test_close_all_forwards_scope_and_runtime_options(command_calls: CommandCalls) -> None:
    result = CliRunner().invoke(agents_iter.get_app(), ["close", "--all", "--loop", "--retain-previous", "1", "--dry-run", "--interval", "7"])

    assert result.exit_code == 0, result.output
    assert command_calls["close"] == [(None, True, False, True, 1, True, 7)]


@pytest.mark.parametrize("interactive_option", ("--interactive", "-I"))
def test_close_forwards_interactive_scope(interactive_option: str, command_calls: CommandCalls) -> None:
    result = CliRunner().invoke(agents_iter.get_app(), ["close", interactive_option])

    assert result.exit_code == 0, result.output
    assert command_calls["close"] == [(None, False, True, False, 3, False, 300)]


@pytest.mark.parametrize("scope_arguments", ((), ("w7", "--all"), ("w7", "--interactive"), ("--all", "--interactive")))
def test_close_rejects_missing_or_conflicting_scope(scope_arguments: tuple[str, ...], command_calls: CommandCalls) -> None:
    result = CliRunner().invoke(agents_iter.get_app(), ["close", *scope_arguments])

    assert result.exit_code == 2, result.output
    assert "exactly one" in result.output.lower()
    assert command_calls["close"] == []


@pytest.mark.parametrize(("command_name", "command_option"), (("status", "--retain-previous"), ("clean", "--dry-run")))
def test_status_and_clean_help_expose_optional_workspace_and_scope_options(command_name: str, command_option: str) -> None:
    result = CliRunner().invoke(agents_iter.get_app(), [command_name, "--help"], terminal_width=160)

    assert result.exit_code == 0, result.output
    assert "[WORKSPACE_ID]" in result.output
    assert "--all" in result.output
    assert "-a" in result.output
    assert "--interactive" in result.output
    assert "-I" in result.output
    assert command_option in result.output


@pytest.mark.parametrize(
    ("arguments", "expected_call"),
    (
        (("w7",), ("w7", False, False, 3)),
        (("--all", "--retain-previous", "1"), (None, True, False, 1)),
        (("-a",), (None, True, False, 3)),
        (("--interactive",), (None, False, True, 3)),
        (("-I",), (None, False, True, 3)),
    ),
)
def test_status_forwards_each_workspace_scope(
    arguments: tuple[str, ...], expected_call: tuple[str | None, bool, bool, int], command_calls: CommandCalls
) -> None:
    result = CliRunner().invoke(agents_iter.get_app(), ["status", *arguments])

    assert result.exit_code == 0, result.output
    assert command_calls["status"] == [expected_call]


@pytest.mark.parametrize(
    ("arguments", "expected_call"),
    (
        (("w7",), ("w7", False, False, False)),
        (("--all", "--dry-run"), (None, True, False, True)),
        (("-a",), (None, True, False, False)),
        (("--interactive",), (None, False, True, False)),
        (("-I",), (None, False, True, False)),
    ),
)
def test_clean_forwards_each_workspace_scope(
    arguments: tuple[str, ...],
    expected_call: tuple[str | None, bool, bool, bool],
    command_calls: CommandCalls,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(agents_iter.get_app(), ["clean", *arguments])

    assert result.exit_code == 0, result.output
    assert command_calls["clean"] == [(tmp_path, *expected_call)]


@pytest.mark.parametrize("command_name", ("status", "clean"))
@pytest.mark.parametrize("scope_arguments", ((), ("w7", "--all"), ("w7", "--interactive"), ("--all", "--interactive")))
def test_status_and_clean_reject_missing_or_conflicting_scope(
    command_name: str, scope_arguments: tuple[str, ...], command_calls: CommandCalls
) -> None:
    result = CliRunner().invoke(agents_iter.get_app(), [command_name, *scope_arguments])

    assert result.exit_code == 2, result.output
    assert "exactly one" in result.output.lower()
    assert command_calls["status"] == []
    assert command_calls["clean"] == []
