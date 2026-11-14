import os
import pickle
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.live import Live

from stackops.utils.installer_utils import installer_bulk_worker
from stackops.utils.installer_utils.constants import BULK_INSTALL_PARALLEL_JOBS, BULK_INSTALL_POLL_SECONDS, BULK_INSTALL_SUDO_KEEPALIVE_SECONDS
from stackops.utils.installer_utils.installer_bulk_display import (
    print_finished_line,
    render_bulk_header,
    render_bulk_summary,
    render_live_view,
    render_nothing_to_install,
)
from stackops.utils.installer_utils.installer_bulk_models import BulkInstallJob, BulkInstallOutcome, FinishedInstall, PlannedInstall, RunningInstall
from stackops.utils.installer_utils.installer_bulk_plan import cache_sudo_credentials, plan_bulk_installs
from stackops.utils.schemas.installer.installer_types import (
    InstallRequest,
    InstallationResult,
    InstallationResultFailed,
    InstallationResultSkipped,
    InstallerData,
)
from stackops.utils.source_of_truth import INSTALL_LOGS_ROOT


def _launch_install(planned: PlannedInstall, install_request: InstallRequest, log_dir: Path, work_dir: Path, detached_from_terminal: bool) -> RunningInstall:
    job_path = work_dir.joinpath(f"""{planned.exe_name}.job.pickle""")
    job_path.write_bytes(pickle.dumps(BulkInstallJob(installer_data=planned.installer_data, install_request=install_request)))
    outcome_path = work_dir.joinpath(f"""{planned.exe_name}.outcome.pickle""")
    log_path = log_dir.joinpath(f"""{planned.exe_name}.log""")
    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = subprocess.CREATE_NO_WINDOW
    with log_path.open("wb") as log_file:
        process = subprocess.Popen(  # pylint: disable=consider-using-with
            [sys.executable, "-m", installer_bulk_worker.__name__, str(job_path), str(outcome_path)],
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            env={**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONUTF8": "1"},
            creationflags=creation_flags,
            start_new_session=detached_from_terminal,
        )
    return RunningInstall(planned=planned, process=process, started_at=time.monotonic(), log_path=log_path, outcome_path=outcome_path)


def _collect_install(running: RunningInstall, finished_at: float) -> FinishedInstall:
    result: InstallationResult
    if running.outcome_path.is_file():
        outcome = pickle.loads(running.outcome_path.read_bytes())
        if not isinstance(outcome, BulkInstallOutcome):
            raise TypeError(f"""Expected a BulkInstallOutcome in {running.outcome_path}, got {type(outcome).__name__}""")
        result = outcome.result
    else:
        result = InstallationResultFailed(
            kind="failed",
            appName=running.planned.installer_data["appName"],
            exeName=running.planned.exe_name,
            emoji="❌",
            error=f"""installer process exited with code {running.process.returncode} before reporting a result""",
        )
    return FinishedInstall(planned=running.planned, result=result, seconds=finished_at - running.started_at, log_path=running.log_path)


def _run_planned_installs(
    planned_installs: list[PlannedInstall], install_request: InstallRequest, log_dir: Path, sudo_credentials_cached: bool, name_width: int, console: Console
) -> list[FinishedInstall]:
    # sudo keys its cached credentials to the terminal, so installers only share the terminal when those credentials exist;
    # otherwise they get their own session, where nothing can prompt on top of the live view.
    detached_from_terminal = not sudo_credentials_cached
    pending = sorted(planned_installs, key=lambda planned: not planned.holds_system_installer_lock)
    running: list[RunningInstall] = []
    finished: list[FinishedInstall] = []
    started_at = time.monotonic()
    sudo_refreshed_at = started_at
    with tempfile.TemporaryDirectory(prefix="stackops_bulk_install_") as work_dir_name:
        with Live(console=console, auto_refresh=False, transient=True) as live:
            try:
                while len(pending) > 0 or len(running) > 0:
                    system_lock_busy = any(item.planned.holds_system_installer_lock for item in running)
                    for planned in list(pending):
                        if len(running) >= BULK_INSTALL_PARALLEL_JOBS:
                            break
                        if planned.holds_system_installer_lock and system_lock_busy:
                            continue
                        pending.remove(planned)
                        running.append(
                            _launch_install(
                                planned=planned,
                                install_request=install_request,
                                log_dir=log_dir,
                                work_dir=Path(work_dir_name),
                                detached_from_terminal=detached_from_terminal,
                            )
                        )
                        system_lock_busy = system_lock_busy or planned.holds_system_installer_lock
                    now = time.monotonic()
                    for item in [item for item in running if item.process.poll() is not None]:
                        running.remove(item)
                        finished_install = _collect_install(running=item, finished_at=now)
                        finished.append(finished_install)
                        print_finished_line(console=live.console, finished=finished_install, name_width=name_width)
                    if sudo_credentials_cached and now - sudo_refreshed_at >= BULK_INSTALL_SUDO_KEEPALIVE_SECONDS:
                        subprocess.run(["sudo", "-n", "-v"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                        sudo_refreshed_at = now
                    live.update(
                        render_live_view(running=running, finished=finished, queued_count=len(pending), started_at=started_at, now=now, name_width=name_width),
                        refresh=True,
                    )
                    time.sleep(BULK_INSTALL_POLL_SECONDS)
            finally:
                for item in running:
                    if detached_from_terminal and sys.platform != "win32":
                        os.killpg(item.process.pid, signal.SIGKILL)
                    else:
                        item.process.kill()
                    item.process.wait()
    return finished


def install_bulk(installers_data: list[InstallerData], install_request: InstallRequest, batch_label: str) -> None:
    console = Console()
    planned_installs = plan_bulk_installs(installers_data=installers_data, install_request=install_request)
    to_run = [planned for planned in planned_installs if not planned.skip]
    if len(to_run) == 0:
        render_nothing_to_install(console=console, batch_label=batch_label, planned_installs=planned_installs)
        return
    skipped = [
        FinishedInstall(
            planned=planned,
            result=InstallationResultSkipped(
                kind="skipped", appName=planned.installer_data["appName"], exeName=planned.exe_name, emoji="⏭️", detail="already installed, skipped"
            ),
            seconds=0.0,
            log_path=None,
        )
        for planned in planned_installs
        if planned.skip
    ]
    log_dir = INSTALL_LOGS_ROOT.joinpath(f"""{datetime.now().strftime("%y-%m-%d_%H-%M-%S")}_{batch_label}""")
    log_dir.mkdir(parents=True, exist_ok=False)
    render_bulk_header(console=console, batch_label=batch_label, planned_installs=planned_installs, parallel_jobs=BULK_INSTALL_PARALLEL_JOBS, log_dir=log_dir)
    sudo_credentials_cached = cache_sudo_credentials(planned_installs=to_run, console=console)
    started_at = time.monotonic()
    ran = _run_planned_installs(
        planned_installs=to_run,
        install_request=install_request,
        log_dir=log_dir,
        sudo_credentials_cached=sudo_credentials_cached,
        name_width=max(len(planned.exe_name) for planned in to_run),
        console=console,
    )
    render_bulk_summary(console=console, batch_label=batch_label, finished=[*ran, *skipped], wall_seconds=time.monotonic() - started_at, log_dir=log_dir)
