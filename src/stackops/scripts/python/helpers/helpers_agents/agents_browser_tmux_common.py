from collections.abc import Sequence
import shlex
import shutil
import subprocess
from typing import NoReturn


def require_tmux() -> None:
    if shutil.which("tmux") is None:
        raise RuntimeError("tmux is required for browser tmux launches. Pass --runtime detached to use background processes.")


def run_optional_tmux_command(*, command: Sequence[str]) -> subprocess.CompletedProcess[str] | None:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode == 0:
        return result
    detail = (result.stderr or result.stdout or "").strip().lower()
    missing_socket = "error connecting to" in detail and "no such file or directory" in detail
    silent_psmux_miss = detail == ""
    if missing_socket or silent_psmux_miss or any(marker in detail for marker in ("no server running", "failed to connect to server", "can't find session", "can't find window")):
        return None
    raise_tmux_command_failure(command=command, result=result)


def run_required_tmux_command(*, command: Sequence[str]) -> str:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise_tmux_command_failure(command=command, result=result)
    return result.stdout


def raise_tmux_command_failure(*, command: Sequence[str], result: subprocess.CompletedProcess[str]) -> NoReturn:
    detail = (result.stderr or result.stdout or f"exit code {result.returncode}").strip()
    raise RuntimeError(f"""tmux command failed: {shlex.join(command)}: {detail}""")
