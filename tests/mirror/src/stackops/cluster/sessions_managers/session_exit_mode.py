from base64 import b64decode
import shlex

from stackops.cluster.sessions_managers import session_exit_mode


def _decode_encoded_command(parts: list[str]) -> str:
    encoded_index = parts.index("-EncodedCommand") + 1
    return b64decode(parts[encoded_index]).decode("utf-16le")


def test_build_tmux_exit_mode_command_wraps_back_to_shell_script() -> None:
    command = session_exit_mode.build_tmux_exit_mode_command(command="python app.py", exit_mode="backToShell")

    parts = shlex.split(command)

    assert parts[0:2] == ["bash", "-lc"]
    assert parts[2] == 'python app.py\nexec "${SHELL:-bash}" -i'


def test_build_powershell_exit_mode_command_parts_back_to_shell_uses_no_exit() -> None:
    parts = session_exit_mode.build_powershell_exit_mode_command_parts(command="Write-Host 'hi'", exit_mode="backToShell", shell_name="pwsh")
    decoded_script = _decode_encoded_command(parts)

    assert parts[0:4] == ["pwsh", "-NoLogo", "-NoProfile", "-NoExit"]
    assert "$stackopsCommand = 'Write-Host ''hi'''" in decoded_script
    assert "Invoke-Expression -Command $stackopsCommand" in decoded_script


def test_build_powershell_exit_mode_command_parts_kill_window_exits() -> None:
    parts = session_exit_mode.build_powershell_exit_mode_command_parts(command="Write-Host done", exit_mode="killWindow", shell_name="powershell")
    decoded_script = _decode_encoded_command(parts)

    assert "-NoExit" not in parts
    assert decoded_script.endswith("exit $stackopsExitCode")


def test_build_tmux_exit_mode_command_terminate_contains_restart_prompt() -> None:
    command = session_exit_mode.build_tmux_exit_mode_command(command="python worker.py", exit_mode="terminate")
    script_body = shlex.split(command)[2]

    assert "while true; do" in script_body
    assert "Press Enter to restart" in script_body
    assert 'tmux kill-pane -t "${TMUX_PANE}"' in script_body
