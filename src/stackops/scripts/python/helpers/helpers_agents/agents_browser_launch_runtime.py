from collections.abc import Mapping, Sequence
import json
import socket
import subprocess
import sys
import time
from typing import cast
from urllib.parse import quote
from urllib.request import Request, urlopen

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import (
    BROWSER_CDP_REQUEST_TIMEOUT_SECONDS,
    BROWSER_ENDPOINT_PROBE_INTERVAL_SECONDS,
    BROWSER_ENDPOINT_STARTUP_TIMEOUT_SECONDS,
    BROWSER_PROCESS_TERMINATION_TIMEOUT_SECONDS,
    REMOTE_DEBUGGING_LAN,
    REMOTE_DEBUGGING_LOCALHOST,
)


def start_browser_process(
    *,
    command: Sequence[str],
    system_name: str,
    process_label: str,
    environment: Mapping[str, str],
) -> subprocess.Popen[bytes]:
    return _start_background_process(
        command=command,
        system_name=system_name,
        failure_message=f"""Failed to launch {process_label}""",
        environment=environment,
    )


def start_endpoint_relay(*, listen_port: int, target_port: int, system_name: str) -> subprocess.Popen[bytes]:
    command = build_relay_command(listen_port=listen_port, target_port=target_port)
    return _start_background_process(
        command=command,
        system_name=system_name,
        failure_message="Failed to launch browser endpoint LAN relay",
        environment=None,
    )


def resolve_browser_endpoint_port(*, exposed_port: int, lan: bool) -> int:
    if lan:
        assert_tcp_port_available(host=REMOTE_DEBUGGING_LAN, port=exposed_port)
        return find_available_localhost_port(excluded_port=exposed_port)
    assert_tcp_port_available(host=REMOTE_DEBUGGING_LOCALHOST, port=exposed_port)
    return exposed_port


def assert_tcp_port_available(*, host: str, port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe_socket:
        probe_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe_socket.bind((host, port))
        except OSError as error:
            raise RuntimeError(f"""TCP port {host}:{port} is not available: {error}""") from error


def find_available_localhost_port(*, excluded_port: int) -> int:
    for _attempt in range(100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe_socket:
            probe_socket.bind((REMOTE_DEBUGGING_LOCALHOST, 0))
            chosen_port = int(probe_socket.getsockname()[1])
        if chosen_port != excluded_port:
            return chosen_port
    raise RuntimeError("Could not find an internal localhost browser endpoint port")


def tcp_port_is_open(*, host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe_socket:
        probe_socket.settimeout(BROWSER_ENDPOINT_PROBE_INTERVAL_SECONDS)
        return probe_socket.connect_ex((host, port)) == 0


def ensure_cdp_page_target(*, port: int) -> bool:
    targets_url = f"http://{REMOTE_DEBUGGING_LOCALHOST}:{port}/json/list"
    try:
        with urlopen(targets_url, timeout=BROWSER_CDP_REQUEST_TIMEOUT_SECONDS) as response:
            targets = cast(list[dict[str, object]], json.loads(response.read()))
        if any(target.get("type") == "page" for target in targets):
            return False
        target_url = quote("about:blank", safe="")
        request = Request(
            f"http://{REMOTE_DEBUGGING_LOCALHOST}:{port}/json/new?{target_url}",
            method="PUT",
        )
        with urlopen(request, timeout=BROWSER_CDP_REQUEST_TIMEOUT_SECONDS):
            return True
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Existing CDP endpoint on port {port} could not open a browser page: {error}") from error


def verify_cdp_endpoint(*, port: int) -> None:
    version_url = f"http://{REMOTE_DEBUGGING_LOCALHOST}:{port}/json/version"
    try:
        with urlopen(version_url, timeout=BROWSER_CDP_REQUEST_TIMEOUT_SECONDS) as response:
            version = cast(dict[str, object], json.loads(response.read()))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Endpoint on port {port} is not a valid Chrome DevTools Protocol endpoint: {error}") from error
    web_socket_url = version.get("webSocketDebuggerUrl")
    if not isinstance(web_socket_url, str) or not web_socket_url.startswith("ws://"):
        raise RuntimeError(f"Endpoint on port {port} did not provide a Chrome DevTools Protocol WebSocket URL")


def wait_for_tcp_endpoint(
    *,
    host: str,
    port: int,
    process: subprocess.Popen[bytes] | None,
    process_label: str,
) -> None:
    deadline = time.monotonic() + BROWSER_ENDPOINT_STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if process is not None:
            return_code = process.poll()
            if return_code is not None:
                raise RuntimeError(f"{process_label} exited before endpoint {host}:{port} became ready (exit code {return_code})")
        if tcp_port_is_open(host=host, port=port):
            if process is not None:
                time.sleep(BROWSER_ENDPOINT_PROBE_INTERVAL_SECONDS)
                return_code = process.poll()
                if return_code is not None:
                    raise RuntimeError(
                        f"{process_label} exited while endpoint {host}:{port} became ready (exit code {return_code})"
                    )
            return
        time.sleep(BROWSER_ENDPOINT_PROBE_INTERVAL_SECONDS)
    raise RuntimeError(f"{process_label} did not open endpoint {host}:{port} within {BROWSER_ENDPOINT_STARTUP_TIMEOUT_SECONDS:g} seconds")


def terminate_background_process(*, process: subprocess.Popen[bytes], process_label: str) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=BROWSER_PROCESS_TERMINATION_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"{process_label} process {process.pid} did not stop after termination") from error


def build_relay_command(*, listen_port: int, target_port: int) -> tuple[str, ...]:
    return (
        sys.executable,
        "-m",
        "stackops.scripts.python.helpers.helpers_agents.browser_cdp_relay",
        "--listen-host",
        REMOTE_DEBUGGING_LAN,
        "--listen-port",
        str(listen_port),
        "--target-host",
        REMOTE_DEBUGGING_LOCALHOST,
        "--target-port",
        str(target_port),
    )


def _start_background_process(
    *,
    command: Sequence[str],
    system_name: str,
    failure_message: str,
    environment: Mapping[str, str] | None,
) -> subprocess.Popen[bytes]:
    try:
        if system_name == "Windows":
            return subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=environment)
        return subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=environment,
        )
    except OSError as error:
        raise RuntimeError(f"""{failure_message}: {error}""") from error
