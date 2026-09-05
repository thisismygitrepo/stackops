from dataclasses import dataclass
from pathlib import Path
import platform
from typing import assert_never

import psutil

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BROWSER_PROCESS_TERMINATION_TIMEOUT_SECONDS, BrowserName
from stackops.scripts.python.helpers.helpers_agents.browser_launchers.registry import get_browser_launcher


@dataclass(frozen=True)
class RunningBrowserProcess:
    process_id: int
    browser_port: int


def process_created_at(*, process_id: int, process_label: str) -> float:
    try:
        return psutil.Process(process_id).create_time()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as error:
        raise RuntimeError(f"{process_label} process {process_id} exited before its detached launch could be recorded") from error


def find_browser_process_id(
    *, browser: BrowserName, browser_port: int, profile_path: Path | None, process_id: int, process_created_at: float
) -> int | None:
    try:
        process = psutil.Process(process_id)
        if _browser_process_matches(
            process=process, browser=browser, browser_port=browser_port, profile_path=profile_path, expected_created_at=process_created_at
        ):
            return process_id
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        pass
    for process in psutil.process_iter():
        try:
            if _browser_process_matches(
                process=process, browser=browser, browser_port=browser_port, profile_path=profile_path, expected_created_at=None
            ):
                return process.pid
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return None


def find_running_browser_processes(*, browser: BrowserName, profile_path: Path) -> tuple[RunningBrowserProcess, ...]:
    running_processes: list[RunningBrowserProcess] = []
    for process in psutil.process_iter():
        try:
            command = tuple(process.cmdline())
            if not _browser_process_matches_profile(process=process, browser=browser, profile_path=profile_path, command=command):
                continue
            option_name = "--remote-debugging-port" if browser != "safari" else "--port"
            port_value = _option_value(command=command, name=option_name)
            if port_value is not None:
                running_processes.append(RunningBrowserProcess(process_id=process.pid, browser_port=int(port_value)))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, ValueError):
            continue
    return tuple(running_processes)


def find_browser_process_ids(*, browser: BrowserName) -> tuple[int, ...]:
    launcher = get_browser_launcher(browser=browser)
    executable_names = {_normalize_executable_name(executable_name=path.name) for path in launcher.known_paths(system_name=platform.system())}
    executable_names.update(_normalize_executable_name(executable_name=command_name) for command_name in launcher.command_names)
    process_ids: list[int] = []
    for process in psutil.process_iter():
        try:
            process_name = _normalize_executable_name(executable_name=process.name())
            if _matches_browser_executable_name(process_name=process_name, executable_names=executable_names):
                process_ids.append(process.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return tuple(sorted(process_ids))


def find_browser_profile_process_ids(*, browser: BrowserName, profile_path: Path) -> tuple[int, ...]:
    process_ids: list[int] = []
    for process in psutil.process_iter():
        try:
            command = tuple(process.cmdline())
            if _browser_process_matches_profile(process=process, browser=browser, profile_path=profile_path, command=command):
                process_ids.append(process.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return tuple(sorted(process_ids))


def _normalize_executable_name(*, executable_name: str) -> str:
    return Path(executable_name).name.casefold().removesuffix(".exe")


def _matches_browser_executable_name(*, process_name: str, executable_names: set[str]) -> bool:
    return process_name in executable_names or any(process_name.startswith(f"{executable_name} helper") for executable_name in executable_names)


def registered_process_is_running(*, process_id: int, process_created_at: float) -> bool:
    try:
        process = psutil.Process(process_id)
        return process.create_time() == process_created_at and process.is_running() and process.status() != psutil.STATUS_ZOMBIE
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return False


def terminate_registered_process(*, process_id: int, process_created_at: float, process_label: str) -> None:
    try:
        process = psutil.Process(process_id)
        if process.create_time() != process_created_at:
            return
        process.terminate()
        process.wait(timeout=BROWSER_PROCESS_TERMINATION_TIMEOUT_SECONDS)
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return
    except psutil.AccessDenied as error:
        raise RuntimeError(f"Could not terminate stale {process_label} process {process_id}: {error}") from error
    except psutil.TimeoutExpired as error:
        raise RuntimeError(f"Stale {process_label} process {process_id} did not stop after termination") from error


def terminate_browser_launch_process(
    *, browser: BrowserName, browser_port: int, profile_path: Path | None, process_id: int, process_created_at: float, process_label: str
) -> None:
    """Terminate the recorded browser or its exact profile-and-port handoff."""
    resolved_process_id = find_browser_process_id(
        browser=browser, browser_port=browser_port, profile_path=profile_path, process_id=process_id, process_created_at=process_created_at
    )
    if resolved_process_id is None:
        return
    if resolved_process_id == process_id:
        terminate_registered_process(process_id=process_id, process_created_at=process_created_at, process_label=process_label)
        return

    try:
        process = psutil.Process(resolved_process_id)
        resolved_created_at = process.create_time()
        if not _browser_process_matches(
            process=process, browser=browser, browser_port=browser_port, profile_path=profile_path, expected_created_at=resolved_created_at
        ):
            return
        process.terminate()
        process.wait(timeout=BROWSER_PROCESS_TERMINATION_TIMEOUT_SECONDS)
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return
    except psutil.AccessDenied as error:
        raise RuntimeError(f"Could not terminate tracked {process_label} process {resolved_process_id}: {error}") from error
    except psutil.TimeoutExpired as error:
        raise RuntimeError(f"Tracked {process_label} process {resolved_process_id} did not stop after termination") from error


def _browser_process_matches(
    *, process: psutil.Process, browser: BrowserName, browser_port: int, profile_path: Path | None, expected_created_at: float | None
) -> bool:
    if expected_created_at is not None and process.create_time() != expected_created_at:
        return False
    if not process.is_running() or process.status() == psutil.STATUS_ZOMBIE:
        return False
    command = tuple(process.cmdline())
    if not _browser_process_matches_profile(process=process, browser=browser, profile_path=profile_path, command=command):
        return False
    option_name = "--port" if browser == "safari" else "--remote-debugging-port"
    return _has_option(command=command, name=option_name, value=str(browser_port))


def _browser_process_matches_profile(*, process: psutil.Process, browser: BrowserName, profile_path: Path | None, command: tuple[str, ...]) -> bool:
    if not process.is_running() or process.status() == psutil.STATUS_ZOMBIE:
        return False
    launcher = get_browser_launcher(browser=browser)
    executable_names = {_normalize_executable_name(executable_name=path.name) for path in launcher.known_paths(system_name=platform.system())}
    executable_names.update(_normalize_executable_name(executable_name=command_name) for command_name in launcher.command_names)
    if not command or _normalize_executable_name(executable_name=command[0]) not in executable_names:
        return False
    if any(argument.startswith("--type=") for argument in command):
        return False
    match browser:
        case "chrome" | "brave" | "edge":
            if profile_path is None:
                return False
            return _profile_option_matches(command=command, name="--user-data-dir", profile_path=profile_path)
        case "firefox":
            if profile_path is None:
                return False
            return _profile_option_matches(command=command, name="--profile", profile_path=profile_path)
        case "safari":
            return profile_path is None
        case _:
            assert_never(browser)


def _has_option(*, command: tuple[str, ...], name: str, value: str) -> bool:
    if f"{name}={value}" in command:
        return True
    return any(argument == name and index + 1 < len(command) and command[index + 1] == value for index, argument in enumerate(command))


def _option_value(*, command: tuple[str, ...], name: str) -> str | None:
    option_prefix = f"{name}="
    for index, argument in enumerate(command):
        if argument.startswith(option_prefix):
            return argument.removeprefix(option_prefix)
        if argument == name and index + 1 < len(command):
            return command[index + 1]
    return None


def _profile_option_matches(*, command: tuple[str, ...], name: str, profile_path: Path) -> bool:
    option_value = _option_value(command=command, name=name)
    if option_value is None:
        return False
    try:
        return Path(option_value).samefile(profile_path)
    except OSError:
        return False
