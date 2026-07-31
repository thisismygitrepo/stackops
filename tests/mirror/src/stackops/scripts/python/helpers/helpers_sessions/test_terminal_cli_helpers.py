import subprocess

import pytest

from stackops.scripts.python.helpers.helpers_sessions import terminal_cli_helpers


def test_detached_shell_script_survives_terminal_session_shutdown(monkeypatch: pytest.MonkeyPatch) -> None:
    observed_args: list[tuple[str, ...]] = []
    observed_settings: list[tuple[int, int, int, bool]] = []

    def popen(
        args: tuple[str, ...],
        *,
        stdin: int,
        stdout: int,
        stderr: int,
        start_new_session: bool,
    ) -> object:
        observed_args.append(args)
        observed_settings.append((stdin, stdout, stderr, start_new_session))
        return object()

    monkeypatch.setattr(subprocess, "Popen", popen)

    terminal_cli_helpers.run_detached_shell_script("stop-session && delete-session")

    assert observed_args == [("sh", "-c", "stop-session && delete-session")]
    assert observed_settings == [
        (
            subprocess.DEVNULL,
            subprocess.DEVNULL,
            subprocess.DEVNULL,
            True,
        )
    ]


def test_detached_shell_script_rejects_empty_script() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        terminal_cli_helpers.run_detached_shell_script(" ")
