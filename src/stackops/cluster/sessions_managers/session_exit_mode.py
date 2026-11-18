from base64 import b64encode
import platform
import shlex
from typing import Literal


type SessionExitMode = Literal[
    "backToShell",
    "terminate",
    "killWindow",
]


def build_tmux_exit_mode_command(command: str, exit_mode: SessionExitMode) -> str:
    if platform.system() == "Windows":
        return " ".join(
            build_powershell_exit_mode_command_parts(
                command=command,
                exit_mode=exit_mode,
                emit_osc133=False,
                close_block="""tmux kill-pane -t $env:TMUX_PANE
exit $stackopsExitCode""",
            )
        )
    script_body = _build_tmux_script_body(command=command, exit_mode=exit_mode)
    return f"bash -lc {shlex.quote(script_body)}"


def build_powershell_exit_mode_command_parts(
    command: str,
    exit_mode: SessionExitMode,
    emit_osc133: bool,
    close_block: str,
) -> list[str]:
    encoded_command = b64encode(command.encode("utf-8")).decode("ascii")
    announce_start = ""
    announce_end = ""
    if emit_osc133:
        announce_start = """[Console]::Write("`e]133;A`a`$ `e]133;B`a$stackopsCommand`n`e]133;C`a")"""
        announce_end = """[Console]::Write("`e]133;D;$stackopsExitCode`a")"""
    run_block = f"""$stackopsCommand = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded_command}'))
{announce_start}
$global:LASTEXITCODE = 0
$stackopsSucceeded = $false
try {{
    Invoke-Expression -Command "$stackopsCommand`n`$stackopsSucceeded = `$?"
}} catch {{
    Write-Error -ErrorRecord $_
}}
$stackopsExitCode = if ($stackopsSucceeded) {{ 0 }} elseif ($LASTEXITCODE -ne 0) {{ [int]$LASTEXITCODE }} else {{ 1 }}
{announce_end}"""
    match exit_mode:
        case "backToShell":
            script = run_block
        case "killWindow":
            script = f"""{run_block}
{close_block}"""
        case "terminate":
            script = f"""while ($true) {{
{run_block}
$stackopsReply = Read-Host -Prompt ("Process completed with exit code {{0}}. Press Enter to restart, or type anything and press Enter to close" -f $stackopsExitCode)
if ($stackopsReply -ne "") {{
{close_block}
}}
}}"""
    encoded_script = b64encode(script.encode("utf-16le")).decode("ascii")
    return ["pwsh", "-NoLogo", "-NoExit" if exit_mode == "backToShell" else "-NoProfile", "-EncodedCommand", encoded_script]


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
