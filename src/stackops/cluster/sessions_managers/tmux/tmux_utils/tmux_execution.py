#!/usr/bin/env python3
import os
import platform
import shlex
import subprocess

from stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_common import shell_quote


_TMUX_ATTACH_OR_SWITCH_PREFIX = 'if [ -n "${TMUX:-}" ]; then '
_TMUX_ATTACH_OR_SWITCH_SEPARATOR = '; else '
_TMUX_ATTACH_OR_SWITCH_SUFFIX = '; fi'
_TMUX_NEW_SESSION_COMMAND = (
    "stackops_next_tmux_session_name() {\n"
    "    session_name=1\n"
    "    existing_sessions=\"$(tmux list-sessions -F '#{session_name}' 2>/dev/null || true)\"\n"
    "    while printf '%s\\n' \"$existing_sessions\" | grep -Fxq \"$session_name\"; do\n"
    "        session_name=$((session_name + 1))\n"
    "    done\n"
    "    printf '%s\\n' \"$session_name\"\n"
    "}\n"
    "new_session_name=\"$(stackops_next_tmux_session_name)\"\n"
    'if [ -n "${TMUX:-}" ]; then\n'
    '    tmux new-session -d -s "$new_session_name" && tmux switch-client -t "$new_session_name"\n'
    "else\n"
    '    tmux new-session -s "$new_session_name"\n'
    "fi"
)
_TMUX_NEW_SESSION_POWERSHELL_COMMAND = (
    "$existingSessions = @(tmux list-sessions -F '#{session_name}' 2>$null); "
    "if ($LASTEXITCODE -ne 0) { $existingSessions = @() }; "
    "$newSessionName = 1; "
    "while ($existingSessions -contains [string]$newSessionName) { $newSessionName += 1 }; "
    "if ($env:TMUX) { "
    "tmux new-session -d -s $newSessionName; "
    "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; "
    "tmux switch-client -t $newSessionName "
    "} else { "
    "tmux new-session -s $newSessionName "
    "}"
)


def build_next_numeric_tmux_session_name(existing_sessions: set[str]) -> str:
    candidate = 1
    while str(candidate) in existing_sessions:
        candidate += 1
    return str(candidate)


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


def _powershell_quote(value: str) -> str:
    escaped_value = value.replace("'", "''")
    return f"'{escaped_value}'"


def quote_tmux_handoff_argument(value: str) -> str:
    if platform.system() == "Windows":
        return _powershell_quote(value)
    return shell_quote(value)


def build_tmux_attach_or_switch_handoff_script(session_name: str) -> str:
    if platform.system() != "Windows":
        return build_tmux_attach_or_switch_command(session_name=session_name)

    quoted_session_name = quote_tmux_handoff_argument(session_name)
    return (
        f"if ($env:TMUX) {{ tmux switch-client -t {quoted_session_name} }} "
        f"else {{ tmux attach -t {quoted_session_name} }}"
    )


def build_tmux_new_session_handoff_script() -> str:
    if platform.system() != "Windows":
        return build_tmux_new_session_command()
    return _TMUX_NEW_SESSION_POWERSHELL_COMMAND


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


def _list_tmux_session_names(timeout_seconds: float | None) -> set[str]:
    result = subprocess.run(
        ["tmux", "list-sessions", "-F", "#{session_name}"],
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip().lower()
        if "no server running" in detail or "failed to connect to server" in detail:
            return set()
        return set()
    return {line.strip() for line in (result.stdout or "").splitlines() if line.strip()}


def _normalize_tmux_script_lines(script: str) -> list[str]:
    return [
        line.strip()
        for line in script.splitlines()
        if line.strip() and not line.startswith("#!") and line.strip() != "set -e"
    ]


def _new_tmux_session(
    *,
    session_name: str,
    detached: bool,
    timeout_seconds: float | None,
) -> subprocess.CompletedProcess[str]:
    command = ["tmux", "new-session"]
    if detached:
        command.append("-d")
    command.extend(["-s", session_name])
    return subprocess.run(
        command,
        capture_output=detached,
        text=True,
        timeout=_resolve_tmux_timeout(
            command=f"tmux new-session {'-d ' if detached else ''}-s {shell_quote(session_name)}",
            timeout_seconds=timeout_seconds,
        ),
        check=False,
    )


def _is_duplicate_session_error(result: subprocess.CompletedProcess[str]) -> bool:
    detail = (result.stderr or result.stdout or "").strip().lower()
    return "duplicate session" in detail or "session already exists" in detail


def start_tmux_new_session(
    kill_all: bool,
    timeout_seconds: float | None,
) -> None:
    if kill_all:
        _run_tmux_kill_server(
            timeout_seconds=timeout_seconds,
            ignore_missing_server=True,
        )

    for _ in range(100):
        session_name = build_next_numeric_tmux_session_name(
            _list_tmux_session_names(timeout_seconds=timeout_seconds),
        )
        result = _new_tmux_session(
            session_name=session_name,
            detached=bool(os.environ.get("TMUX")),
            timeout_seconds=timeout_seconds,
        )
        if result.returncode != 0 and _is_duplicate_session_error(result):
            continue
        if result.returncode != 0:
            _raise_tmux_command_failure(
                command=f"tmux new-session -s {shell_quote(session_name)}",
                result=result,
            )
        if os.environ.get("TMUX"):
            _run_tmux_command(
                command=f"tmux switch-client -t {shell_quote(session_name)}",
                timeout_seconds=timeout_seconds,
                capture_output=True,
            )
        return

    raise RuntimeError("Unable to allocate a free numeric tmux session name.")


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
    commands = _normalize_tmux_script_lines(script)
    new_session_commands = _normalize_tmux_script_lines(_TMUX_NEW_SESSION_COMMAND)
    results: list[subprocess.CompletedProcess[str]] = []
    index = 0
    while index < len(commands):
        command = commands[index]
        if commands[index:index + len(new_session_commands)] == new_session_commands:
            start_tmux_new_session(kill_all=False, timeout_seconds=timeout_seconds)
            index += len(new_session_commands)
            continue
        if (
            command == "tmux kill-server"
            and commands[index + 1:index + 1 + len(new_session_commands)] == new_session_commands
        ):
            start_tmux_new_session(kill_all=True, timeout_seconds=timeout_seconds)
            index += 1 + len(new_session_commands)
            continue
        results.append(
            _run_tmux_command(
                command=_resolve_attach_or_switch_command(command),
                timeout_seconds=timeout_seconds,
                capture_output=capture_output,
            )
        )
        index += 1
    return results
