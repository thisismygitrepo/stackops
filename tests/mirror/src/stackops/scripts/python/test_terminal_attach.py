from typing import Literal, NoReturn

import pytest
from typer.testing import CliRunner

from stackops.scripts.python import terminal
from stackops.scripts.python.helpers.helpers_sessions import attach_impl
from stackops.utils import code

type AttachBackend = Literal["tmux", "herdr", "aoe"]
type AttachCall = tuple[AttachBackend, str | None, bool, bool, bool, bool]


@pytest.mark.parametrize(
    ("arguments", "expected_first"),
    [
        ([], False),
        (["--first"], True),
        (["-f"], True),
    ],
)
def test_attach_forwards_first_option_and_preserves_default(
    monkeypatch: pytest.MonkeyPatch,
    arguments: list[str],
    expected_first: bool,
) -> None:
    observed_calls: list[AttachCall] = []
    observed_handoffs: list[tuple[str, bool]] = []

    def fake_choose_session(
        backend: AttachBackend,
        name: str | None,
        new_session: bool,
        kill_all: bool,
        window: bool,
        first: bool,
    ) -> attach_impl.AttachSessionChoice:
        observed_calls.append((backend, name, new_session, kill_all, window, first))
        return ("handoff_script", "attach-first-session")

    def fake_exit_then_run_shell_script(script: str, strict: bool) -> None:
        observed_handoffs.append((script, strict))

    monkeypatch.setattr(attach_impl, "choose_session", fake_choose_session)
    monkeypatch.setattr(code, "exit_then_run_shell_script", fake_exit_then_run_shell_script)

    result = CliRunner().invoke(terminal.get_app(), ["attach", *arguments])

    assert result.exit_code == 0, result.output
    assert observed_calls == [("tmux", None, False, False, False, expected_first)]
    assert observed_handoffs == [("attach-first-session", True)]


@pytest.mark.parametrize(
    ("arguments", "expected_fragments"),
    [
        (["alpha", "--first"], ("NAME", "--first")),
        (["--new-session", "--first"], ("--new-session", "--first")),
        (["--kill-all", "--first"], ("--kill-all", "--first")),
        (["--window", "--first"], ("--window", "--first")),
        (["--backend", "herdr", "--first"], ("--first", "tmux")),
        (["--backend", "aoe", "--first"], ("--first", "tmux")),
    ],
)
def test_attach_rejects_first_option_conflicts(
    monkeypatch: pytest.MonkeyPatch,
    arguments: list[str],
    expected_fragments: tuple[str, ...],
) -> None:
    def fail_choose_session(
        backend: AttachBackend,
        name: str | None,
        new_session: bool,
        kill_all: bool,
        window: bool,
        first: bool,
    ) -> NoReturn:
        _ = backend, name, new_session, kill_all, window, first
        raise AssertionError("Attach implementation must not run for conflicting options.")

    monkeypatch.setattr(attach_impl, "choose_session", fail_choose_session)

    result = CliRunner().invoke(terminal.get_app(), ["attach", *arguments])

    assert result.exit_code == 1
    for fragment in expected_fragments:
        assert fragment in result.output
