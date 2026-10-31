from base64 import b64decode, b64encode
import re
from shlex import quote

from stackops.cluster.sessions_managers.session_exit_mode import SessionExitMode


def pane_command_parts(command: str, start_dir: str, exit_mode: SessionExitMode) -> list[str]:
    encoded_command = b64encode(command.encode()).decode("ascii")
    encoded_cwd = b64encode(start_dir.encode()).decode("ascii")
    marker = f"""# stackops_zellij_command:{encoded_command}
# stackops_zellij_cwd:{encoded_cwd}
"""
    script = marker + f"""bash -c {quote(command)}
stackops_exit_code=$?
"""
    if exit_mode == "backToShell":
        script += '''exec "${SHELL:-bash}" -i'''
    else:
        script += '''exit "$stackops_exit_code"'''
    return ["bash", "-c", script]


def _command_metadata(terminal_command: str, key: str) -> str | None:
    marker = re.search(rf"# stackops_zellij_{key}:([A-Za-z0-9+/=]+)\n", terminal_command)
    if marker is None:
        return None
    return b64decode(marker[1], validate=True).decode()


def original_command(terminal_command: str) -> str:
    command = _command_metadata(terminal_command=terminal_command, key="command")
    return terminal_command if command is None else command


def original_start_dir(terminal_command: str) -> str:
    start_dir = _command_metadata(terminal_command=terminal_command, key="cwd")
    return "" if start_dir is None else start_dir
