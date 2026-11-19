import asyncio
import subprocess
from dataclasses import dataclass

from starlette.types import Receive

from stackops.scripts.python.helpers.helpers_serve.constants import CAPTURE_OUTPUT_COLUMNS, CAPTURE_TIMEOUT_SECONDS
from stackops.scripts.python.helpers.helpers_serve.runs import build_run_environment


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
    process = subprocess.Popen(
        [executable, *arguments], cwd=working_directory, env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    finishing = asyncio.create_task(asyncio.to_thread(_finish_capture, process))
    leaving = asyncio.ensure_future(receive())  # The request body is already read, so the next message is the browser dropping the request.
    try:
        await asyncio.wait({finishing, leaving}, return_when=asyncio.FIRST_COMPLETED)
    except asyncio.CancelledError:  # A stopping server cancels requests still in flight; ending normally keeps a traceback out of its terminal.
        pass
    # If the command is still going, nobody is left to read its answer: the page went away or the server is stopping.
    # Design choice: only the command itself is killed, not processes it started; captures are read-only queries that work in-process.
    if not finishing.done():
        process.kill()
    leaving.cancel()
    return await finishing


def _finish_capture(process: subprocess.Popen[bytes]) -> CaptureResult | CaptureTimeout:
    try:
        stdout, stderr = process.communicate(timeout=CAPTURE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        return CaptureTimeout(seconds=CAPTURE_TIMEOUT_SECONDS)
    return CaptureResult(
        exit_code=process.returncode, stdout=stdout.decode(encoding="utf-8", errors="replace"), stderr=stderr.decode(encoding="utf-8", errors="replace")
    )
