from pathlib import Path

import pytest
from typer.testing import CliRunner

from stackops.scripts.python import agents_iter
from stackops.scripts.python.helpers.helpers_agents import agents_iter_rich_output


type CloseCall = tuple[Path, str | None, bool, bool, bool, int, bool, int]


@pytest.fixture
def close_calls(monkeypatch: pytest.MonkeyPatch) -> list[CloseCall]:
    calls: list[CloseCall] = []

    def capture_close(
        *,
        cwd: Path,
        workspace_id: str | None,
        all_workspaces: bool,
        interactive: bool,
        continuous: bool,
        retain_previous: int,
        dry_run: bool,
        interval_seconds: int,
    ) -> None:
        calls.append(
            (
                cwd,
                workspace_id,
                all_workspaces,
                interactive,
                continuous,
                retain_previous,
                dry_run,
                interval_seconds,
            )
        )

    monkeypatch.setattr(agents_iter_rich_output, "show_close_iter_workspaces_loop", capture_close)
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


def test_close_forwards_explicit_workspace_with_defaults(
    close_calls: list[CloseCall], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(agents_iter.get_app(), ["close", "w7"])

    assert result.exit_code == 0, result.output
    assert close_calls == [(tmp_path, "w7", False, False, False, 3, False, 300)]


def test_close_all_forwards_scope_and_runtime_options(
    close_calls: list[CloseCall], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(
        agents_iter.get_app(),
        ["close", "--all", "--loop", "--retain-previous", "1", "--dry-run", "--interval", "7"],
    )

    assert result.exit_code == 0, result.output
    assert close_calls == [(tmp_path, None, True, False, True, 1, True, 7)]


@pytest.mark.parametrize("interactive_option", ("--interactive", "-I"))
def test_close_forwards_interactive_scope(
    interactive_option: str,
    close_calls: list[CloseCall],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(agents_iter.get_app(), ["close", interactive_option])

    assert result.exit_code == 0, result.output
    assert close_calls == [(tmp_path, None, False, True, False, 3, False, 300)]


@pytest.mark.parametrize(
    "scope_arguments",
    (
        (),
        ("w7", "--all"),
        ("w7", "--interactive"),
        ("--all", "--interactive"),
    ),
)
def test_close_rejects_missing_or_conflicting_scope(
    scope_arguments: tuple[str, ...], close_calls: list[CloseCall]
) -> None:
    result = CliRunner().invoke(agents_iter.get_app(), ["close", *scope_arguments])

    assert result.exit_code == 2, result.output
    assert "exactly one" in result.output.lower()
    assert close_calls == []
