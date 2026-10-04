from asyncio import Runner
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Queue
from threading import Event
from typing import TYPE_CHECKING, Literal, assert_never

from stackops.jobs.installer.checks.scan_outcomes import ScanCancelled, ScanFailure, ScanSuccess
from stackops.jobs.installer.checks.vt_account_stats import VirusTotalAccountStats
from stackops.jobs.installer.checks.vt_scanner import scan_file
from stackops.secrets.readers import VirusTotalApiKey

if TYPE_CHECKING:
    from stackops.jobs.installer.checks.vt_accounts import VtAccountPool
    from stackops.jobs.installer.checks.vt_requests import VtRequestClient


@dataclass(frozen=True)
class ScannedFile:
    index: int
    path: Path
    version: str | None
    outcome: ScanSuccess | ScanFailure


@dataclass(frozen=True)
class _PendingFile:
    index: int
    path: Path
    version: str | None


@dataclass(frozen=True)
class _WorkerFailure:
    stage: Literal["client creation", "file scan", "client closure"]
    error_type: str


@dataclass(frozen=True)
class _WorkerStopped:
    pass


type _WorkerMessage = ScannedFile | _WorkerFailure | _WorkerStopped


def _scan_worker(
    pool: "VtAccountPool",
    preferred_account_index: int,
    initial_file: _PendingFile,
    pending_files: Queue[_PendingFile],
    messages: Queue[_WorkerMessage],
    stop: Event,
) -> None:
    client: "VtRequestClient | None" = None
    runner = Runner()
    try:
        try:
            from stackops.jobs.installer.checks.vt_requests import VtRequestClient

            runner.get_loop()
            client = VtRequestClient(pool=pool, preferred_account_index=preferred_account_index, stop=stop)
        except BaseException as exc:
            stop.set()
            messages.put(_WorkerFailure(stage="client creation", error_type=type(exc).__name__))
            return

        pending_file = initial_file
        while not stop.is_set():
            try:
                outcome = scan_file(path=pending_file.path, client=client, stop=stop, request_lock=None)
            except BaseException as exc:
                stop.set()
                messages.put(_WorkerFailure(stage="file scan", error_type=type(exc).__name__))
                return
            match outcome:
                case ScanCancelled():
                    break
                case ScanSuccess() | ScanFailure():
                    messages.put(
                        ScannedFile(index=pending_file.index, path=pending_file.path, version=pending_file.version, outcome=outcome)
                    )
                case _:
                    assert_never(outcome)
            try:
                pending_file = pending_files.get_nowait()
            except Empty:
                break
    finally:
        if client is not None:
            try:
                client.close()
            except BaseException as exc:
                stop.set()
                messages.put(_WorkerFailure(stage="client closure", error_type=type(exc).__name__))
        try:
            runner.close()
        except BaseException as exc:
            stop.set()
            messages.put(_WorkerFailure(stage="client closure", error_type=type(exc).__name__))
        messages.put(_WorkerStopped())


def scan_files_with_vt(
    apps_to_scan: list[tuple[Path, str | None]],
    credentials: tuple[VirusTotalApiKey, ...],
    concurrency: int | None,
    stats: VirusTotalAccountStats,
) -> Generator[ScannedFile, None, None]:
    from stackops.jobs.installer.checks.vt_accounts import VtAccountPool

    if concurrency is not None and concurrency < 1:
        raise ValueError("VirusTotal scan concurrency must be at least one.")
    if not credentials:
        raise ValueError("At least one VirusTotal API key is required.")
    if not apps_to_scan:
        return

    indexed_files = [_PendingFile(index=index, path=path, version=version) for index, (path, version) in enumerate(apps_to_scan)]
    worker_count = min(len(credentials) if concurrency is None else concurrency, len(indexed_files))
    pool = VtAccountPool(credentials=credentials, stats=stats)
    pending_files: Queue[_PendingFile] = Queue()
    for pending_file in indexed_files[worker_count:]:
        pending_files.put(pending_file)
    messages: Queue[_WorkerMessage] = Queue()
    stop = Event()
    executor = ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="virustotal")
    completed = False
    try:
        for worker_index, initial_file in enumerate(indexed_files[:worker_count]):
            credential_index = worker_index % len(credentials)
            executor.submit(
                _scan_worker, pool, credential_index, initial_file, pending_files, messages, stop
            )
        stopped_workers = 0
        processed_files = 0
        while stopped_workers < worker_count:
            message = messages.get()
            match message:
                case ScannedFile():
                    processed_files += 1
                    yield message
                case _WorkerFailure():
                    raise RuntimeError(f"""VirusTotal {message.stage} failed ({message.error_type}).""") from None
                case _WorkerStopped():
                    stopped_workers += 1
                case _:
                    assert_never(message)
        if processed_files != len(indexed_files):
            raise RuntimeError("VirusTotal scanning stopped before all files were processed.")
        completed = True
    finally:
        stop.set()
        executor.shutdown(wait=completed, cancel_futures=True)
