import ipaddress
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_common import ListenerAddressFamily, run_argv
from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_models import SSHDebugCheck


def find_linux_sshd() -> Path | None:
    candidates = (Path("/usr/sbin/sshd"), Path("/usr/bin/sshd"), Path("/sbin/sshd"))
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    discovered = shutil.which("sshd")
    if discovered is not None:
        path = Path(discovered)
        if path.is_file() and os.access(path, os.X_OK):
            return path
    return None


def check_linux_service() -> SSHDebugCheck:
    inactive_units: list[str] = []
    probe_failures: list[str] = []
    for unit in ("ssh.service", "sshd.service", "ssh.socket", "sshd.socket"):
        completed = run_argv(("systemctl", "show", unit, "--property=LoadState", "--property=ActiveState"))
        if completed.returncode is None:
            probe_failures.append(completed.failure or "systemctl could not be run")
            break
        if completed.returncode != 0:
            probe_failures.append(completed.stderr or completed.stdout or f"systemctl failed for {unit}")
            continue
        properties: dict[str, str] = {}
        for line in completed.stdout.splitlines():
            name, separator, value = line.partition("=")
            if separator:
                properties[name] = value
        load_state = properties.get("LoadState")
        active_state = properties.get("ActiveState")
        if load_state == "loaded" and active_state == "active":
            return SSHDebugCheck(
                identifier="ssh_service",
                group="service",
                label="SSH service",
                status="ok",
                message=f"{unit} is loaded and active",
                command_suggestions=(),
                manual_advice=(),
            )
        if load_state == "loaded":
            inactive_units.append(f"{unit} ({active_state or 'state unknown'})")
    if inactive_units:
        unit_name = inactive_units[0].split()[0]
        return SSHDebugCheck(
            identifier="ssh_service",
            group="service",
            label="SSH service",
            status="error",
            message=f"Loaded SSH service is not active: {', '.join(inactive_units)}",
            command_suggestions=(f"sudo systemctl start {unit_name}",),
            manual_advice=("Review the service journal before changing its startup configuration.",),
        )
    return SSHDebugCheck(
        identifier="ssh_service",
        group="service",
        label="SSH service",
        status="unknown",
        message="No loaded ssh/sshd systemd unit could be verified"
        + (f" ({'; '.join(probe_failures)})" if probe_failures else ""),
        command_suggestions=(),
        manual_advice=("Inspect the SSH service with the init system used by this host.",),
    )


def _parse_ss_endpoint(endpoint: str) -> tuple[str, int] | None:
    address, separator, port_text = endpoint.rpartition(":")
    if not separator or not port_text.isdecimal():
        return None
    normalized_address = address.removeprefix("[").removesuffix("]")
    return normalized_address, int(port_text)


def _is_external_address(address: str) -> bool | None:
    if address in ("*", "0.0.0.0", "::"):
        return True
    try:
        parsed = ipaddress.ip_address(address.split("%", maxsplit=1)[0])
    except ValueError:
        return None
    return not parsed.is_loopback


def _listener_owner(process_text: str) -> tuple[bool | None, tuple[str, ...]]:
    owner_names = tuple(re.findall(r'\("([^"]+)"', process_text))
    if not owner_names:
        return None, ()
    if "sshd" in owner_names:
        return True, owner_names
    if "systemd" in owner_names:
        return None, owner_names
    return False, owner_names


@dataclass(frozen=True, slots=True)
class LinuxListenerAssessment:
    check: SSHDebugCheck
    families_by_port: dict[int, frozenset[ListenerAddressFamily]] | None


def check_linux_listeners(ports: tuple[int, ...]) -> LinuxListenerAssessment:
    completed = run_argv(("ss", "-H", "-ltnp"))
    if completed.returncode != 0:
        detail = completed.stderr or completed.stdout or completed.failure or "unknown command failure"
        return LinuxListenerAssessment(
            check=SSHDebugCheck(
                identifier="ssh_listener",
                group="network",
                label="TCP listener",
                status="unknown",
                message=f"Could not inspect listening sockets with ss: {detail}",
                command_suggestions=(),
                manual_advice=("Inspect listening TCP endpoints and compare their exact ports with sshd -T.",),
            ),
            families_by_port=None,
        )

    endpoints: dict[int, list[tuple[str, bool | None, tuple[str, ...]]]] = {port: [] for port in ports}
    for line in completed.stdout.splitlines():
        fields = line.split()
        if len(fields) < 4 or fields[0] != "LISTEN":
            continue
        parsed_endpoint = _parse_ss_endpoint(fields[3])
        if parsed_endpoint is None:
            continue
        address, port = parsed_endpoint
        if port in endpoints:
            owned_by_ssh, owner_names = _listener_owner(" ".join(fields[5:]))
            endpoints[port].append((address, owned_by_ssh, owner_names))
    families_by_port: dict[int, frozenset[ListenerAddressFamily]] = {}
    listener_families_proved = True
    for port, records in endpoints.items():
        port_families: set[ListenerAddressFamily] = set()
        for address, owned_by_ssh, _owners in records:
            if owned_by_ssh is False:
                continue
            external_state = _is_external_address(address)
            if external_state is False:
                continue
            if external_state is None or address == "*":
                listener_families_proved = False
                continue
            try:
                parsed_address = ipaddress.ip_address(address.split("%", maxsplit=1)[0])
            except ValueError:
                listener_families_proved = False
            else:
                port_families.add("ipv4" if parsed_address.version == 4 else "ipv6")
        if not port_families:
            listener_families_proved = False
        families_by_port[port] = frozenset(port_families)
    proved_families = families_by_port if listener_families_proved else None
    missing_ports = [port for port, records in endpoints.items() if not records]
    if missing_ports:
        return LinuxListenerAssessment(
            check=SSHDebugCheck(
                identifier="ssh_listener",
                group="network",
                label="TCP listener",
                status="error",
                message=f"No exact listening endpoint for TCP port(s) {', '.join(map(str, missing_ports))}",
                command_suggestions=(),
                manual_advice=("Review the SSH service state and effective ListenAddress settings.",),
            ),
            families_by_port=proved_families,
        )
    uncertain_address_ports: list[int] = []
    uncertain_owner_ports: list[int] = []
    localhost_ports: list[int] = []
    wrong_owners: dict[int, tuple[str, ...]] = {}
    for port, records in endpoints.items():
        external_records = [record for record in records if _is_external_address(record[0]) is True]
        if not external_records:
            if any(_is_external_address(record[0]) is None for record in records):
                uncertain_address_ports.append(port)
            else:
                localhost_ports.append(port)
            continue
        owner_states = tuple(owned_by_ssh for _address, owned_by_ssh, _owners in external_records)
        if all(owned_by_ssh is True for owned_by_ssh in owner_states):
            continue
        if any(owned_by_ssh is None for owned_by_ssh in owner_states) or any(
            owned_by_ssh is True for owned_by_ssh in owner_states
        ):
            uncertain_owner_ports.append(port)
            continue
        wrong_owners[port] = tuple(
            dict.fromkeys(owner for _address, _owned_by_ssh, owners in external_records for owner in owners)
        )
    if localhost_ports:
        return LinuxListenerAssessment(
            check=SSHDebugCheck(
                identifier="ssh_listener",
                group="network",
                label="TCP listener",
                status="error",
                message=f"TCP port(s) {', '.join(map(str, localhost_ports))} listen only on loopback addresses",
                command_suggestions=(),
                manual_advice=("Review effective ListenAddress settings with sshd -T.",),
            ),
            families_by_port=proved_families,
        )
    if wrong_owners:
        details = ", ".join(f"{port}: {owners}" for port, owners in wrong_owners.items())
        return LinuxListenerAssessment(
            check=SSHDebugCheck(
                identifier="ssh_listener",
                group="network",
                label="TCP listener",
                status="error",
                message=f"Effective SSH port(s) are owned by non-SSH processes ({details})",
                command_suggestions=(),
                manual_advice=("Stop or reconfigure the conflicting process before starting sshd.",),
            ),
            families_by_port=proved_families,
        )
    if uncertain_address_ports or uncertain_owner_ports:
        return LinuxListenerAssessment(
            check=SSHDebugCheck(
                identifier="ssh_listener",
                group="network",
                label="TCP listener",
                status="unknown",
                message=(
                    f"Listener address unknown for port(s) {uncertain_address_ports}; "
                    f"sshd/systemd ownership unknown for port(s) {uncertain_owner_ports}"
                ),
                command_suggestions=(),
                manual_advice=("Inspect the raw ss -H -ltnp output and process ownership.",),
            ),
            families_by_port=proved_families,
        )
    return LinuxListenerAssessment(
        check=SSHDebugCheck(
            identifier="ssh_listener",
            group="network",
            label="TCP listener",
            status="ok",
            message=f"sshd/systemd owns exact non-loopback listener(s) for TCP port(s) {', '.join(map(str, ports))}",
            command_suggestions=(),
            manual_advice=(),
        ),
        families_by_port=proved_families,
    )
