import os
from pathlib import Path
from typing import assert_never

import psutil

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import DETACHED_BROWSER_LAUNCH_ID_ENV, BrowserName


def process_created_at(*, process_id: int, process_label: str) -> float:
    try:
        return psutil.Process(process_id).create_time()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as error:
        raise RuntimeError(f"{process_label} process {process_id} exited before its detached launch could be recorded") from error


def find_browser_process_id(
    *,
    launch_id: str,
    browser: BrowserName,
    browser_path: Path,
    browser_port: int,
    profile_path: Path | None,
    process_id: int,
    process_created_at: float,
) -> int | None:
    try:
        process = psutil.Process(process_id)
        if _browser_process_matches(
            process=process,
            launch_id=launch_id,
            browser=browser,
            browser_path=browser_path,
            browser_port=browser_port,
            profile_path=profile_path,
            expected_created_at=process_created_at,
        ):
            return process_id
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        pass
    for process in psutil.process_iter():
        try:
            if _browser_process_matches(
                process=process,
                launch_id=launch_id,
                browser=browser,
                browser_path=browser_path,
                browser_port=browser_port,
                profile_path=profile_path,
                expected_created_at=None,
            ):
                return process.pid
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return None


def registered_process_is_running(*, process_id: int, process_created_at: float) -> bool:
    try:
        process = psutil.Process(process_id)
        return process.create_time() == process_created_at and process.is_running() and process.status() != psutil.STATUS_ZOMBIE
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return False


def _browser_process_matches(
    *,
    process: psutil.Process,
    launch_id: str,
    browser: BrowserName,
    browser_path: Path,
    browser_port: int,
    profile_path: Path | None,
    expected_created_at: float | None,
) -> bool:
    if expected_created_at is not None and process.create_time() != expected_created_at:
        return False
    if not process.is_running() or process.status() == psutil.STATUS_ZOMBIE:
        return False
    process_path = os.path.normcase(os.path.realpath(process.exe()))
    expected_path = os.path.normcase(os.path.realpath(browser_path))
    if process_path != expected_path:
        return False
    if process.environ().get(DETACHED_BROWSER_LAUNCH_ID_ENV) != launch_id:
        return False
    command = tuple(process.cmdline())
    if any(argument.startswith("--type=") for argument in command):
        return False
    match browser:
        case "chrome" | "brave" | "edge":
            if profile_path is None:
                return False
            return _has_option(command=command, name="--remote-debugging-port", value=str(browser_port)) and _has_option(
                command=command, name="--user-data-dir", value=str(profile_path)
            )
        case "firefox":
            if profile_path is None:
                return False
            return _has_option(command=command, name="--remote-debugging-port", value=str(browser_port)) and _has_option(
                command=command, name="--profile", value=str(profile_path)
            )
        case "safari":
            return _has_option(command=command, name="--port", value=str(browser_port))
        case _:
            assert_never(browser)


def _has_option(*, command: tuple[str, ...], name: str, value: str) -> bool:
    if f"{name}={value}" in command:
        return True
    return any(argument == name and index + 1 < len(command) and command[index + 1] == value for index, argument in enumerate(command))
