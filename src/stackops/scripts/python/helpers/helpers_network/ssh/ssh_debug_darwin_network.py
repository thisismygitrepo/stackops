import ipaddress

from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_common import run_argv
from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_models import SSHDebugCheck


def _parse_netstat_endpoint(endpoint: str) -> tuple[str, int] | None:
    address, separator, port_text = endpoint.rpartition(".")
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


def _lsof_listener_records(ports: tuple[int, ...]) -> dict[int, list[tuple[str, str | None]]] | None:
    completed = run_argv(("/usr/sbin/lsof", "-nP", "-a", "-iTCP", "-sTCP:LISTEN", "-Fpcn"))
    if completed.returncode != 0:
        return None
    records: dict[int, list[tuple[str, str | None]]] = {port: [] for port in ports}
    current_command: str | None = None
    for field in completed.stdout.splitlines():
        if not field:
            continue
        field_type = field[0]
        value = field[1:]
        if field_type == "p":
            current_command = None
            continue
        if field_type == "c":
            current_command = value
            continue
        if field_type != "n":
            continue
        address, separator, port_text = value.rpartition(":")
        if not separator or not port_text.isdecimal():
            continue
        port = int(port_text)
        if port in records:
            normalized_address = address.removeprefix("[").removesuffix("]")
            records[port].append((normalized_address, current_command))
    return records


def check_darwin_listeners(ports: tuple[int, ...]) -> SSHDebugCheck:
    completed = run_argv(("/usr/sbin/netstat", "-anv", "-p", "tcp"))
    if completed.returncode != 0:
        detail = completed.stderr or completed.stdout or completed.failure or "unknown command failure"
        return SSHDebugCheck(
            identifier="ssh_listener",
            group="network",
            label="TCP listener",
            status="unknown",
            message=f"Could not inspect TCP listeners: {detail}",
            command_suggestions=(),
            manual_advice=("Inspect exact listening endpoints with netstat or lsof.",),
        )

    endpoints: dict[int, list[str]] = {port: [] for port in ports}
    unparsed_listener = False
    for line in completed.stdout.splitlines():
        fields = line.split()
        if not fields or not fields[0].startswith("tcp") or "LISTEN" not in fields:
            continue
        if len(fields) < 4:
            unparsed_listener = True
            continue
        parsed_endpoint = _parse_netstat_endpoint(fields[3])
        if parsed_endpoint is None:
            unparsed_listener = True
            continue
        address, port = parsed_endpoint
        if port in endpoints:
            endpoints[port].append(address)
    missing_ports = [port for port, addresses in endpoints.items() if not addresses]
    if missing_ports and unparsed_listener:
        return SSHDebugCheck(
            identifier="ssh_listener",
            group="network",
            label="TCP listener",
            status="unknown",
            message=f"netstat output could not conclusively identify exact endpoint(s) for port(s) {missing_ports}",
            command_suggestions=(),
            manual_advice=("Inspect raw netstat output for the effective SSH ports.",),
        )
    if missing_ports:
        return SSHDebugCheck(
            identifier="ssh_listener",
            group="network",
            label="TCP listener",
            status="error",
            message=f"No exact listening endpoint for TCP port(s) {', '.join(map(str, missing_ports))}",
            command_suggestions=(),
            manual_advice=("Review Remote Login and effective ListenAddress settings.",),
        )
    unknown_addresses: list[int] = []
    loopback_ports: list[int] = []
    for port, addresses in endpoints.items():
        states = [_is_external_address(address) for address in addresses]
        if any(state is True for state in states):
            continue
        if any(state is None for state in states):
            unknown_addresses.append(port)
        else:
            loopback_ports.append(port)
    if loopback_ports:
        return SSHDebugCheck(
            identifier="ssh_listener",
            group="network",
            label="TCP listener",
            status="error",
            message=f"TCP port(s) {', '.join(map(str, loopback_ports))} listen only on loopback addresses",
            command_suggestions=(),
            manual_advice=("Review the effective ListenAddress values with sshd -T.",),
        )
    if unknown_addresses:
        return SSHDebugCheck(
            identifier="ssh_listener",
            group="network",
            label="TCP listener",
            status="unknown",
            message=f"Listener addresses could not be classified for port(s) {unknown_addresses}",
            command_suggestions=(),
            manual_advice=("Inspect raw netstat output.",),
        )

    owner_records = _lsof_listener_records(ports)
    if owner_records is None:
        return SSHDebugCheck(
            identifier="ssh_listener",
            group="network",
            label="TCP listener",
            status="unknown",
            message="Exact non-loopback listeners exist, but lsof could not prove their owning processes",
            command_suggestions=(),
            manual_advice=("Inspect listener ownership without requesting elevation from this diagnostic.",),
        )
    unknown_owner_ports: list[int] = []
    wrong_owners: dict[int, tuple[str, ...]] = {}
    for port, records in owner_records.items():
        external_records = [record for record in records if _is_external_address(record[0]) is True]
        if any(command in ("sshd", "launchd") for _address, command in external_records):
            continue
        if not external_records or any(command is None for _address, command in external_records):
            unknown_owner_ports.append(port)
            continue
        wrong_owners[port] = tuple(dict.fromkeys(command for _address, command in external_records if command is not None))
    if wrong_owners:
        details = ", ".join(f"{port}: {owners}" for port, owners in wrong_owners.items())
        return SSHDebugCheck(
            identifier="ssh_listener",
            group="network",
            label="TCP listener",
            status="error",
            message=f"Effective SSH port(s) are owned by non-SSH processes ({details})",
            command_suggestions=(),
            manual_advice=("Stop or reconfigure the conflicting process before enabling Remote Login.",),
        )
    if unknown_owner_ports:
        return SSHDebugCheck(
            identifier="ssh_listener",
            group="network",
            label="TCP listener",
            status="unknown",
            message=f"sshd/launchd ownership could not be proved for TCP port(s) {unknown_owner_ports}",
            command_suggestions=(),
            manual_advice=("Inspect lsof process ownership for the effective SSH ports.",),
        )
    return SSHDebugCheck(
        identifier="ssh_listener",
        group="network",
        label="TCP listener",
        status="ok",
        message=f"sshd/launchd owns exact non-loopback listener(s) for TCP port(s) {', '.join(map(str, ports))}",
        command_suggestions=(),
        manual_advice=(),
    )
