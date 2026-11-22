import asyncio
import os
import platform
import signal
import subprocess
from dataclasses import dataclass

from starlette.types import Receive

from stackops.scripts.python.helpers.helpers_webui.constants import CAPTURE_OUTPUT_COLUMNS, CAPTURE_TIMEOUT_SECONDS
from stackops.scripts.python.helpers.helpers_webui.runs import build_run_environment


@dataclass(frozen=True)
class CaptureResult:
    exit_code: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class CaptureTimeout:
    seconds: float


async def capture_command(executable: str, arguments: tuple[str, ...], working_directory: str, receive: Receive) -> CaptureResult | CaptureTimeout:
    environment = build_run_environment(interactive=False)
    environment["COLUMNS"] = str(CAPTURE_OUTPUT_COLUMNS)
    environment["NO_COLOR"] = "1"
    environment["PYTHONUTF8"] = "1"
    # Its own process group (POSIX only), so that stopping a capture also stops what it started: a search runs ripgrep as a child process.
    process = subprocess.Popen(
        [executable, *arguments], cwd=working_directory, env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True
    )
    finishing = asyncio.create_task(asyncio.to_thread(_finish_capture, process))
    leaving = asyncio.ensure_future(receive())  # The request body is already read, so the next message is the browser dropping the request.
    try:
        await asyncio.wait({finishing, leaving}, return_when=asyncio.FIRST_COMPLETED)
    except asyncio.CancelledError:  # A stopping server cancels requests still in flight; ending normally keeps a traceback out of its terminal.
        pass
    # If the command is still going, nobody is left to read its answer: the request was dropped, the page went away or the server is stopping.
    if not finishing.done():
        _kill_capture(process)
    leaving.cancel()
    return await finishing


def _finish_capture(process: subprocess.Popen[bytes]) -> CaptureResult | CaptureTimeout:
    try:
        stdout, stderr = process.communicate(timeout=CAPTURE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        _kill_capture(process)
        process.communicate()
        return CaptureTimeout(seconds=CAPTURE_TIMEOUT_SECONDS)
    return CaptureResult(
        exit_code=process.returncode, stdout=stdout.decode(encoding="utf-8", errors="replace"), stderr=stderr.decode(encoding="utf-8", errors="replace")
    )


# Design choice: the group is signalled without first checking that the command is still alive. A child can outlive it and keep the output pipes
# open, which is the case this exists for; the group id cannot be handed to another process while any member of the group lives.
def _kill_capture(process: subprocess.Popen[bytes]) -> None:
    if platform.system() == "Windows":
        process.kill()
        return
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:  # The command and everything it started ended between the check and the signal.
        return
