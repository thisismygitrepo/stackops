import asyncio
import os
import platform
import shlex
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import TypedDict
from uuid import uuid4

from stackops.scripts.python.helpers.helpers_serve.constants import (
    FINISHED_RUNS_KEPT,
    LAUNCH_PATH_VARIABLE,
    LAUNCH_VIRTUAL_ENV_VARIABLE,
    SCROLLBACK_LIMIT_BYTES,
    SHUTDOWN_JOIN_SECONDS,
    STOP_GRACE_SECONDS,
    TERMINAL_RESTORE_SEQUENCE,
)
from stackops.scripts.python.helpers.helpers_serve.pty_process import PtyHandle, spawn_pty
from stackops.utils.source_of_truth import HTML_REPORTS_ROOT, LIBRARY_ROOT

POSIX_SHELL_WRAPPER = LIBRARY_ROOT.joinpath("scripts", "linux", "wrap_stackops")


@dataclass(frozen=True)
class RunExit:
    exit_code: int
    finished_at: float
    reports: tuple[str, ...]


type RunEvent = bytes | RunExit


@dataclass
class Run:
    run_id: str
    command_line: str
    arguments: tuple[str, ...]
    working_directory: str
    interactive: bool
    started_at: float
    handle: PtyHandle
    scrollback: deque[bytes]
    scrollback_bytes: int
    subscribers: set[asyncio.Queue[RunEvent]]
    outcome: RunExit | None


@dataclass
class RunRegistry:
    stackops_executable: str
    runs: dict[str, Run]
    pump_threads: dict[str, threading.Thread]


class RunSummary(TypedDict):
    id: str
    command_line: str
    arguments: list[str]
    working_directory: str
    interactive: bool
    started_at: float
    finished_at: float | None
    exit_code: int | None
    reports: list[str]


def build_run_environment(interactive: bool) -> dict[str, str]:
    environment = dict(os.environ)
    environment["PATH"] = environment.pop(LAUNCH_PATH_VARIABLE)
    launch_virtual_env = environment.pop(LAUNCH_VIRTUAL_ENV_VARIABLE)
    if launch_virtual_env == "":
        environment.pop("VIRTUAL_ENV", None)
    else:
        environment["VIRTUAL_ENV"] = launch_virtual_env
    # A run talks to the browser terminal, so whether it may prompt is decided per run, not by how the server itself was launched.
    for name in (
        "UV_RUN_RECURSION_DEPTH", "OP_PROGRAM_PATH", "TERM_PROGRAM", "TERM_PROGRAM_VERSION", "STACKOPS_NON_INTERACTIVE", "GIT_TERMINAL_PROMPT", "GCM_INTERACTIVE",
    ):
        environment.pop(name, None)
    environment["TERM"] = "xterm-256color"
    environment["COLORTERM"] = "truecolor"
    if not interactive:
        environment["STACKOPS_NON_INTERACTIVE"] = "1"
    return environment


def start_run(registry: RunRegistry, arguments: tuple[str, ...], working_directory: str, rows: int, columns: int, interactive: bool) -> Run:
    loop = asyncio.get_running_loop()
    environment = build_run_environment(interactive=interactive)
    started_at = time.time()
    # Some commands finish by leaving a script for the shell wrapper to run once they exit (attach, end session, shell scripts), so a run goes
    # through that wrapper as it does in a terminal. Design choice: not on Windows, where the PowerShell wrapper does not pass the exit code back
    # and every run would report success; those commands still fail there.
    command = [registry.stackops_executable, *arguments]
    argv = command if platform.system() == "Windows" else ["bash", str(POSIX_SHELL_WRAPPER), *command]
    handle = spawn_pty(argv=argv, working_directory=working_directory, environment=environment, rows=rows, columns=columns)
    run_id = uuid4().hex[:12]
    run = Run(
        run_id=run_id,
        command_line=shlex.join(["stackops", *arguments]),
        arguments=arguments,
        working_directory=working_directory,
        interactive=interactive,
        started_at=started_at,
        handle=handle,
        scrollback=deque(),
        scrollback_bytes=0,
        subscribers=set(),
        outcome=None,
    )

    def publish(chunk: bytes) -> None:
        loop.call_soon_threadsafe(_publish_output, run, chunk)

    def pump() -> None:
        exit_code = handle.pump(publish)
        loop.call_soon_threadsafe(_finish_run, run, exit_code)

    _publish_output(run, f"""\x1b[2m$ {run.command_line}\x1b[0m\r\n""".encode())
    pump_thread = threading.Thread(target=pump, name=f"""stackops-serve-run-{run_id}""", daemon=True)
    finished_run_ids = [finished_id for finished_id, finished_run in registry.runs.items() if finished_run.outcome is not None]
    for finished_id in finished_run_ids[:-FINISHED_RUNS_KEPT]:
        del registry.runs[finished_id]
        del registry.pump_threads[finished_id]
    registry.runs[run_id] = run
    registry.pump_threads[run_id] = pump_thread
    pump_thread.start()
    return run


def subscribe(run: Run) -> tuple[bytes, asyncio.Queue[RunEvent]]:
    queue: asyncio.Queue[RunEvent] = asyncio.Queue()
    run.subscribers.add(queue)
    return b"".join(run.scrollback), queue


def stop_run(run: Run) -> None:
    if run.outcome is not None:
        return
    run.handle.stop(False)
    asyncio.get_running_loop().call_later(STOP_GRACE_SECONDS, _force_stop, run)


async def shutdown_runs(registry: RunRegistry) -> None:
    active_runs = [run for run in registry.runs.values() if run.outcome is None]
    for run in active_runs:
        run.handle.stop(True)
    for run in active_runs:
        await asyncio.to_thread(registry.pump_threads[run.run_id].join, SHUTDOWN_JOIN_SECONDS)
    await asyncio.sleep(0)


def describe_run(run: Run) -> RunSummary:
    return {
        "id": run.run_id,
        "command_line": run.command_line,
        "arguments": list(run.arguments),
        "working_directory": run.working_directory,
        "interactive": run.interactive,
        "started_at": run.started_at,
        "finished_at": None if run.outcome is None else run.outcome.finished_at,
        "exit_code": None if run.outcome is None else run.outcome.exit_code,
        "reports": [] if run.outcome is None else list(run.outcome.reports),
    }


def _publish_output(run: Run, chunk: bytes) -> None:
    run.scrollback.append(chunk)
    run.scrollback_bytes += len(chunk)
    while run.scrollback_bytes > SCROLLBACK_LIMIT_BYTES:
        run.scrollback_bytes -= len(run.scrollback.popleft())
    for queue in run.subscribers:
        queue.put_nowait(chunk)


def _finish_run(run: Run, exit_code: int) -> None:
    finished_at = time.time()
    report_times = [(path.stat().st_mtime, path.name) for path in HTML_REPORTS_ROOT.glob("*.html")]
    outcome = RunExit(exit_code=exit_code, finished_at=finished_at, reports=tuple(name for modified_at, name in sorted(report_times, reverse=True) if modified_at >= run.started_at))
    status = "done" if exit_code == 0 else f"""exit {exit_code}"""
    _publish_output(run, f"""{TERMINAL_RESTORE_SEQUENCE}\r\n\x1b[2m[{status} · {finished_at - run.started_at:.1f}s]\x1b[0m\r\n""".encode())
    run.handle.close()
    run.outcome = outcome
    for queue in run.subscribers:
        queue.put_nowait(outcome)


def _force_stop(run: Run) -> None:
    if run.outcome is None:
        run.handle.stop(True)
