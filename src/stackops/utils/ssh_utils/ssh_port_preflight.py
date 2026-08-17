import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from stackops.utils.ssh_utils.ssh_port_commands import (
    PrivilegePrefix,
    authorize_privileged_commands,
    capture_checked_command,
    run_command,
)
from stackops.utils.ssh_utils.ssh_port_service import ServiceManager, resolve_service_manager


@dataclass(frozen=True, slots=True)
class EffectiveSshdConfig:
    port: int
    listen_addresses: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PortChangePlan:
    config_path: Path
    sshd_path: Path
    privilege_prefix: PrivilegePrefix
    service_manager: ServiceManager
    effective_config: EffectiveSshdConfig


def _resolve_sshd_path() -> Path:
    discovered_path = shutil.which("sshd")
    candidates = tuple(
        Path(candidate)
        for candidate in (discovered_path, "/usr/sbin/sshd", "/usr/local/sbin/sshd")
        if candidate is not None
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise RuntimeError("OpenSSH server is not installed; run `ssh install-server`, then retry.")


def _endpoint_port(endpoint: str) -> int:
    if endpoint.isdecimal():
        return int(endpoint)
    port_text = endpoint.rsplit(":", maxsplit=1)[-1]
    if not port_text.isdecimal():
        raise RuntimeError(f"Unable to determine the port from SSH listen address {endpoint!r}.")
    return int(port_text)


def inspect_effective_sshd_config(
    sshd_path: Path,
    config_path: Path,
    privilege_prefix: PrivilegePrefix,
    config_label: str,
) -> EffectiveSshdConfig:
    capture_checked_command(
        command=(*privilege_prefix, str(sshd_path), "-t", "-f", str(config_path)),
        failure_message=f"{config_label} failed `sshd -t` validation",
    )
    effective_output = capture_checked_command(
        command=(*privilege_prefix, str(sshd_path), "-T", "-f", str(config_path)),
        failure_message=f"Unable to inspect {config_label} with `sshd -T`",
    )
    ports = tuple(int(line.split(maxsplit=1)[1]) for line in effective_output.splitlines() if line.startswith("port "))
    if len(ports) != 1:
        displayed_ports = ", ".join(str(port) for port in ports) or "none"
        raise RuntimeError(
            f"{config_label} resolves an ambiguous set of Port directives ({displayed_ports}). "
            f"Consolidate Port directives in {config_path} and its Include files, then retry."
        )
    listen_addresses = tuple(
        line.split(maxsplit=1)[1] for line in effective_output.splitlines() if line.startswith("listenaddress ")
    )
    if len(listen_addresses) == 0:
        raise RuntimeError(f"{config_label} has no effective ListenAddress; correct {config_path}, then retry.")
    listen_ports = {_endpoint_port(address) for address in listen_addresses}
    if listen_ports != {ports[0]}:
        displayed_addresses = ", ".join(listen_addresses)
        raise RuntimeError(
            f"{config_label} has ListenAddress values that do not resolve exclusively to Port {ports[0]} "
            f"({displayed_addresses}). Correct explicit ListenAddress ports in {config_path} or its Include files, then retry."
        )
    return EffectiveSshdConfig(port=ports[0], listen_addresses=listen_addresses)


def _listening_socket_lines(privilege_prefix: PrivilegePrefix) -> tuple[str, ...]:
    ss_path = shutil.which("ss")
    if ss_path is None:
        raise RuntimeError("The `ss` command is required to verify SSH listeners; install iproute2, then retry.")
    output = capture_checked_command(
        command=(*privilege_prefix, ss_path, "-H", "-ltnp"),
        failure_message="Unable to inspect active TCP listeners",
    )
    return tuple(line for line in output.splitlines() if line.strip() != "")


def _listener_line_port(line: str) -> int | None:
    fields = line.split(maxsplit=5)
    if len(fields) < 4:
        return None
    try:
        return _endpoint_port(fields[3])
    except RuntimeError:
        return None


def assert_target_port_available(plan: PortChangePlan, target_port: int) -> None:
    if target_port == plan.effective_config.port:
        return
    occupied_lines = tuple(
        line for line in _listening_socket_lines(plan.privilege_prefix) if _listener_line_port(line) == target_port
    )
    if len(occupied_lines) > 0:
        raise RuntimeError(f"TCP port {target_port} is already listening. Stop the owning service or choose another port, then retry.")


def assert_active_ssh_listener(plan: PortChangePlan, expected_port: int) -> None:
    listener_lines = _listening_socket_lines(plan.privilege_prefix)
    if plan.service_manager.socket_name is None:
        ssh_listener_ports = {
            listener_port
            for line in listener_lines
            if '"sshd"' in line.lower()
            if (listener_port := _listener_line_port(line)) is not None
        }
        if ssh_listener_ports != {expected_port}:
            displayed_ports = ", ".join(str(port) for port in sorted(ssh_listener_ports)) or "none"
            raise RuntimeError(f"The active sshd service listens on {displayed_ports}, not exclusively on TCP port {expected_port}.")
        return
    matching_lines = tuple(
        line
        for line in listener_lines
        if _listener_line_port(line) == expected_port
    )
    if len(matching_lines) == 0:
        raise RuntimeError(f"The active SSH socket is not listening on TCP port {expected_port}.")


def assert_active_socket_port(plan: PortChangePlan, expected_port: int) -> None:
    socket_name = plan.service_manager.socket_name
    if socket_name is None:
        return
    output = capture_checked_command(
        command=(*plan.privilege_prefix, "systemctl", "show", socket_name, "--property=Listen", "--value"),
        failure_message=f"Unable to inspect active socket {socket_name}",
    )
    socket_ports = {_endpoint_port(match.group(1)) for match in re.finditer(r"(\S+)\s+\(Stream\)", output)}
    if socket_ports != {expected_port}:
        displayed_ports = ", ".join(str(port) for port in sorted(socket_ports)) or "none"
        raise RuntimeError(
            f"Active socket {socket_name} listens on {displayed_ports}, not exclusively on TCP port {expected_port}. "
            "Correct its ListenStream configuration, then retry."
        )


def prepare_port_change(config_path: Path) -> PortChangePlan:
    privilege_prefix = authorize_privileged_commands()
    if run_command((*privilege_prefix, "test", "-f", str(config_path))).returncode != 0:
        raise FileNotFoundError(f"SSH config file not found: {config_path}")
    sshd_path = _resolve_sshd_path()
    service_manager = resolve_service_manager(privilege_prefix=privilege_prefix)
    effective_config = inspect_effective_sshd_config(
        sshd_path=sshd_path,
        config_path=config_path,
        privilege_prefix=privilege_prefix,
        config_label="Current SSH configuration",
    )
    plan = PortChangePlan(
        config_path=config_path,
        sshd_path=sshd_path,
        privilege_prefix=privilege_prefix,
        service_manager=service_manager,
        effective_config=effective_config,
    )
    assert_active_socket_port(plan=plan, expected_port=effective_config.port)
    assert_active_ssh_listener(plan=plan, expected_port=effective_config.port)
    return plan
