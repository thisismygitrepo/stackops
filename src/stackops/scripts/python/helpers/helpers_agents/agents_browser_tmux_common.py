from collections.abc import Sequence
import shlex
import shutil
import subprocess
from typing import NoReturn


def require_tmux() -> None:
    if shutil.which("tmux") is None:
        raise RuntimeError("tmux is required for browser tmux launches. Pass --detached to use the background process mode.")


def run_optional_tmux_command(*, command: Sequence[str]) -> subprocess.CompletedProcess[str] | None:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode == 0:
        return result
    detail = (result.stderr or result.stdout or "").strip().lower()
    if "no server running" in detail or "failed to connect to server" in detail or "can't find session" in detail:
        return None
    raise_tmux_command_failure(command=command, result=result)


def run_required_tmux_command(*, command: Sequence[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise_tmux_command_failure(command=command, result=result)


def raise_tmux_command_failure(*, command: Sequence[str], result: subprocess.CompletedProcess[str]) -> NoReturn:
    detail = (result.stderr or result.stdout or f"exit code {result.returncode}").strip()
    raise RuntimeError(f"""tmux command failed: {shlex.join(command)}: {detail}""")
