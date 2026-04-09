from base64 import b64encode
import shlex
from typing import Literal


type SessionExitMode = Literal[
    "backToShell",
    "terminate",
    "killWindow",
]


def build_tmux_exit_mode_command(command: str, exit_mode: SessionExitMode) -> str:
    script_body = _build_tmux_script_body(command=command, exit_mode=exit_mode)
    return f"bash -lc {shlex.quote(script_body)}"


def build_powershell_exit_mode_command_parts(
    command: str,
    exit_mode: SessionExitMode,
    shell_name: str,
) -> list[str]:
    script = _build_powershell_script(command=command, exit_mode=exit_mode)
    encoded_script = b64encode(script.encode("utf-16le")).decode("ascii")
    parts: list[str] = [shell_name, "-NoLogo", "-NoProfile"]
    if exit_mode == "backToShell":
        parts.append("-NoExit")
    parts.extend(["-EncodedCommand", encoded_script])
    return parts


def _build_tmux_script_body(command: str, exit_mode: SessionExitMode) -> str:
    close_command = 'tmux kill-pane -t "${TMUX_PANE}" 2>/dev/null || exit "$exit_code"'
    match exit_mode:
        case "backToShell":
            return "\n".join((command, 'exec "${SHELL:-bash}" -i'))
        case "terminate":
            return "\n".join(
                (
                    "while true; do",
                    f"  {command}",
                    "  exit_code=$?",
                    '  printf \'\\nProcess completed with exit code %s. Press Enter to restart, or type anything and press Enter to close.\\n\' "$exit_code"',
                    "  if ! IFS= read -r restart_reply; then",
                    f"    {close_command}",
                    "  fi",
                    '  if [ -n "$restart_reply" ]; then',
                    f"    {close_command}",
                    "  fi",
                    "done",
                )
            )
        case "killWindow":
            return "\n".join((command, "exit_code=$?", close_command))


def _build_powershell_script(command: str, exit_mode: SessionExitMode) -> str:
    command_literal = _powershell_literal(command)
    run_block = "\n".join(
        (
            "$global:LASTEXITCODE = 0",
            f"$machineconfigCommand = {command_literal}",
            "Invoke-Expression -Command $machineconfigCommand",
            "$machineconfigExitCode = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } elseif ($?) { 0 } else { 1 }",
        )
    )
    match exit_mode:
        case "backToShell":
            return run_block
        case "terminate":
            indented_run_block = _indent(text=run_block, prefix="    ")
            return "\n".join(
                (
                    "while ($true) {",
                    indented_run_block,
                    '    $machineconfigReply = Read-Host -Prompt ("Process completed with exit code {0}. Press Enter to restart, or type anything and press Enter to close" -f $machineconfigExitCode)',
                    '    if ($machineconfigReply -ne "") {',
                    "        exit $machineconfigExitCode",
                    "    }",
                    "}",
                )
            )
        case "killWindow":
            return "\n".join((run_block, "exit $machineconfigExitCode"))


def _powershell_literal(value: str) -> str:
    escaped_value = value.replace("'", "''")
    return f"'{escaped_value}'"


def _indent(text: str, prefix: str) -> str:
    return "\n".join(f"{prefix}{line}" for line in text.splitlines())
