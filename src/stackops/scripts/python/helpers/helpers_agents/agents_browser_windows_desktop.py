import ctypes
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from xml.sax.saxutils import escape

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import (
    REMOTE_DEBUGGING_LOCALHOST,
    WINDOWS_DESKTOP_TASK_PREFIX,
    WINDOWS_DESKTOP_TASK_PRIORITY,
    WINDOWS_SERVICES_SESSION_ID,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_detached_processes import process_created_at, scan_browser_process_id
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_identity import browser_launch_id
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_models import BrowserLaunchDetails
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_runtime import verify_cdp_endpoint, wait_for_tcp_endpoint
from stackops.scripts.python.helpers.helpers_agents.browser_launchers.registry import get_browser_launcher


def runs_in_windows_services_session() -> bool:
    if sys.platform != "win32":
        return False
    session_id = ctypes.c_ulong()
    if not ctypes.windll.kernel32.ProcessIdToSessionId(os.getpid(), ctypes.byref(session_id)):
        raise RuntimeError(f"""Could not read the Windows session of this process: {ctypes.WinError()}""")
    return session_id.value == WINDOWS_SERVICES_SESSION_ID


def start_browser_on_interactive_desktop(*, details: BrowserLaunchDetails) -> tuple[int, float]:
    launch_id = browser_launch_id(browser=details.browser, profile_path=details.profile_path, port=details.port)
    task_name = f"""{WINDOWS_DESKTOP_TASK_PREFIX}{launch_id}"""
    _register_desktop_task(task_name=task_name, command=details.command)
    try:
        _run_schtasks(arguments=("/run", "/tn", task_name))
        wait_for_tcp_endpoint(host=REMOTE_DEBUGGING_LOCALHOST, port=details.browser_port, process=None, process_label=details.process_label)
        if get_browser_launcher(browser=details.browser).endpoint_protocol == "cdp":
            verify_cdp_endpoint(port=details.browser_port)
        process_id = scan_browser_process_id(browser=details.browser, browser_port=details.browser_port, profile_path=details.profile_path)
        if process_id is None:
            raise RuntimeError(f"""{details.process_label} answered on port {details.browser_port}, but its process could not be found""")
        return process_id, process_created_at(process_id=process_id, process_label=details.process_label)
    except RuntimeError as error:
        error.add_note(
            f"""This process runs in Windows session 0 (services, SSH), whose desktop nobody sees, so {details.process_label} was started """
            f"""on the logged-on user's desktop through scheduled task {task_name}. That needs this Windows user logged on to the desktop."""
        )
        _run_schtasks(arguments=("/end", "/tn", task_name))
        raise
    finally:
        _run_schtasks(arguments=("/delete", "/tn", task_name, "/f"))


def _register_desktop_task(*, task_name: str, command: tuple[str, ...]) -> None:
    definition = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
    </Principal>
  </Principals>
  <Settings>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>{WINDOWS_DESKTOP_TASK_PRIORITY}</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{escape(command[0])}</Command>
      <Arguments>{escape(subprocess.list2cmdline(command[1:]))}</Arguments>
    </Exec>
  </Actions>
</Task>
"""
    with TemporaryDirectory() as directory:
        definition_path = Path(directory).joinpath("task.xml")
        definition_path.write_text(definition, encoding="utf-16")
        _run_schtasks(arguments=("/create", "/tn", task_name, "/xml", str(definition_path), "/f"))


def _run_schtasks(*, arguments: tuple[str, ...]) -> None:
    try:
        completed = subprocess.run(("schtasks", *arguments), capture_output=True, encoding="oem", errors="replace", check=False)
    except OSError as error:
        raise RuntimeError(f"""Failed to execute schtasks {" ".join(arguments)}: {error}""") from error
    if completed.returncode != 0:
        output = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"""schtasks {" ".join(arguments)} failed with exit code {completed.returncode}: {output}""")
