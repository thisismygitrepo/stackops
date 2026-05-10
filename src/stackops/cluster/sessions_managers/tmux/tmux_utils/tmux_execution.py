#!/usr/bin/env python3
import os
import shlex
import subprocess

from stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_common import shell_quote


_TMUX_ATTACH_OR_SWITCH_PREFIX = 'if [ -n "${TMUX:-}" ]; then '
_TMUX_ATTACH_OR_SWITCH_SEPARATOR = '; else '
_TMUX_ATTACH_OR_SWITCH_SUFFIX = '; fi'
_TMUX_NEW_SESSION_COMMAND = (
    'if [ -n "${TMUX:-}" ]; then '
    """new_session_name=$(tmux new-session -d -P -F '#{session_name}') && """
    'tmux switch-client -t "$new_session_name"; '
    'else '
    'tmux new-session; '
    'fi'
)


def build_tmux_attach_or_switch_command(session_name: str) -> str:
    quoted_session_name = shell_quote(session_name)
    return (
        'if [ -n "${TMUX:-}" ]; then '
        f"tmux switch-client -t {quoted_session_name}; "
        "else "
        f"tmux attach -t {quoted_session_name}; "
        "fi"
    )


def build_tmux_new_session_command() -> str:
    return _TMUX_NEW_SESSION_COMMAND


def _split_tmux_command(command: str) -> list[str]:
    return shlex.split(command, posix=True)


def _is_interactive_tmux_command(command: str) -> bool:
    command_parts = _split_tmux_command(command)
    if command_parts[:2] == ["tmux", "attach"]:
        return True
    if command_parts[:2] != ["tmux", "new-session"]:
        return False
    return "-d" not in command_parts


def _resolve_tmux_timeout(command: str, timeout_seconds: float | None) -> float | None:
    if _is_interactive_tmux_command(command):
        return None
    return timeout_seconds


def _raise_tmux_command_failure(
    command: str,
    result: subprocess.CompletedProcess[str],
) -> None:
    detail = (result.stderr or result.stdout or f"exit code {result.returncode}").strip()
    raise RuntimeError(f"tmux command failed: {command}: {detail}")


def _run_tmux_command(
    command: str,
    timeout_seconds: float | None,
    capture_output: bool,
) -> subprocess.CompletedProcess[str]:
    resolved_timeout = _resolve_tmux_timeout(
        command=command,
        timeout_seconds=timeout_seconds,
    )
    result = subprocess.run(
        _split_tmux_command(command),
        capture_output=capture_output,
        text=True,
        timeout=resolved_timeout,
        check=False,
    )
    if result.returncode != 0:
        _raise_tmux_command_failure(command=command, result=result)
    return result


def _run_tmux_kill_server(
    timeout_seconds: float | None,
    ignore_missing_server: bool,
) -> None:
    result = subprocess.run(
        ["tmux", "kill-server"],
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    if result.returncode == 0:
        return
    if ignore_missing_server:
        detail = (result.stderr or result.stdout or "").strip().lower()
        if "no server running" in detail or "failed to connect to server" in detail:
            return
    _raise_tmux_command_failure(command="tmux kill-server", result=result)


def _resolve_attach_or_switch_command(command: str) -> str:
    if (
        not command.startswith(_TMUX_ATTACH_OR_SWITCH_PREFIX)
        or not command.endswith(_TMUX_ATTACH_OR_SWITCH_SUFFIX)
    ):
        return command
    command_body = command.removeprefix(_TMUX_ATTACH_OR_SWITCH_PREFIX).removesuffix(
        _TMUX_ATTACH_OR_SWITCH_SUFFIX,
    )
    attach_or_switch_commands = command_body.split(
        _TMUX_ATTACH_OR_SWITCH_SEPARATOR,
        maxsplit=1,
    )
    if len(attach_or_switch_commands) != 2:
        return command
    if os.environ.get("TMUX"):
        return attach_or_switch_commands[0]
    return attach_or_switch_commands[1]


def start_tmux_new_session(
    kill_all: bool,
    timeout_seconds: float | None,
) -> None:
    if kill_all:
        _run_tmux_kill_server(
            timeout_seconds=timeout_seconds,
            ignore_missing_server=True,
        )

    if os.environ.get("TMUX"):
        result = subprocess.run(
            ["tmux", "new-session", "-d", "-P", "-F", "#{session_name}"],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        if result.returncode != 0:
            _raise_tmux_command_failure(
                command="tmux new-session -d -P -F '#{session_name}'",
                result=result,
            )
        lines = [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]
        if len(lines) == 0:
            raise RuntimeError("tmux did not report the new session name.")
        _run_tmux_command(
            command=f"tmux switch-client -t {shell_quote(lines[-1])}",
            timeout_seconds=timeout_seconds,
            capture_output=True,
        )
        return

    result = subprocess.run(
        ["tmux", "new-session"],
        timeout=_resolve_tmux_timeout(
            command="tmux new-session",
            timeout_seconds=timeout_seconds,
        ),
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("tmux command failed: tmux new-session")


def run_tmux_commands(
    commands: list[str],
    timeout_seconds: float | None,
    capture_output: bool = True,
) -> list[subprocess.CompletedProcess[str]]:
    results: list[subprocess.CompletedProcess[str]] = []
    for command in commands:
        command_stripped = command.strip()
        if not command_stripped:
            continue
        results.append(
            _run_tmux_command(
                command=command_stripped,
                timeout_seconds=timeout_seconds,
                capture_output=capture_output,
            )
        )
    return results


def run_tmux_script(
    script: str,
    timeout_seconds: float | None,
    capture_output: bool = True,
) -> list[subprocess.CompletedProcess[str]]:
    commands = [
        line.strip()
        for line in script.splitlines()
        if line.strip() and not line.startswith("#!") and line.strip() != "set -e"
    ]
    results: list[subprocess.CompletedProcess[str]] = []
    for index, command in enumerate(commands):
        if command == _TMUX_NEW_SESSION_COMMAND:
            start_tmux_new_session(kill_all=False, timeout_seconds=timeout_seconds)
            continue
        if (
            command == "tmux kill-server"
            and index < len(commands) - 1
            and commands[index + 1] == _TMUX_NEW_SESSION_COMMAND
        ):
            _run_tmux_kill_server(
                timeout_seconds=timeout_seconds,
                ignore_missing_server=True,
            )
            continue
        results.append(
            _run_tmux_command(
                command=_resolve_attach_or_switch_command(command),
                timeout_seconds=timeout_seconds,
                capture_output=capture_output,
            )
        )
    return results