import subprocess
from dataclasses import dataclass

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


def capture_command(executable: str, arguments: tuple[str, ...], working_directory: str) -> CaptureResult | CaptureTimeout:
    environment = build_run_environment(interactive=False)
    environment["COLUMNS"] = str(CAPTURE_OUTPUT_COLUMNS)
    environment["NO_COLOR"] = "1"
    environment["PYTHONUTF8"] = "1"
    try:
        completed = subprocess.run(
            [executable, *arguments],
            cwd=working_directory,
            env=environment,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=CAPTURE_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return CaptureTimeout(seconds=CAPTURE_TIMEOUT_SECONDS)
    return CaptureResult(
        exit_code=completed.returncode,
        stdout=completed.stdout.decode(encoding="utf-8", errors="replace"),
        stderr=completed.stderr.decode(encoding="utf-8", errors="replace"),
    )
