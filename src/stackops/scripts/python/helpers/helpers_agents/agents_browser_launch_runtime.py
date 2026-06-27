from collections.abc import Sequence
import socket
import subprocess
import sys

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import (
    REMOTE_DEBUGGING_LAN,
    REMOTE_DEBUGGING_LOCALHOST,
)


def start_browser_process(*, command: Sequence[str], system_name: str, process_label: str) -> subprocess.Popen[bytes]:
    return _start_background_process(command=command, system_name=system_name, failure_message=f"""Failed to launch {process_label}""")


def start_endpoint_relay(*, listen_port: int, target_port: int, system_name: str) -> subprocess.Popen[bytes]:
    command = build_relay_command(listen_port=listen_port, target_port=target_port)
    return _start_background_process(command=command, system_name=system_name, failure_message="Failed to launch browser endpoint LAN relay")


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


def _start_background_process(*, command: Sequence[str], system_name: str, failure_message: str) -> subprocess.Popen[bytes]:
    try:
        if system_name == "Windows":
            return subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError as error:
        raise RuntimeError(f"""{failure_message}: {error}""") from error
