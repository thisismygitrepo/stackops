import ipaddress
import json
from typing import cast

from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_models import SSHDebugCheck
from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_windows_utils import run_powershell


def _object_list(value: object) -> list[dict[str, object]] | None:
    if value is None:
        return []
    if isinstance(value, dict):
        return [cast(dict[str, object], value)]
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        return None
    return [cast(dict[str, object], item) for item in value]


def check_windows_listeners(ports: tuple[int, ...]) -> SSHDebugCheck:
    port_values = ", ".join(map(str, ports))
    script = f"""
$wantedPorts = @({port_values})
$service = Get-CimInstance -ClassName Win32_Service -Filter "Name='sshd'" -ErrorAction Stop
$serviceProcessId = if ($null -eq $service) {{ 0 }} else {{ [uint32]$service.ProcessId }}
$rows = @(Get-NetTCPConnection -State Listen -ErrorAction Stop |
    Where-Object {{ $wantedPorts -contains $_.LocalPort }} |
    ForEach-Object {{
        [PSCustomObject]@{{
            LocalAddress = $_.LocalAddress
            LocalPort = [int]$_.LocalPort
            OwningProcess = [uint32]$_.OwningProcess
            OwnedBySshd = $serviceProcessId -ne 0 -and $serviceProcessId -eq [uint32]$_.OwningProcess
        }}
    }})
ConvertTo-Json -InputObject @($rows) -Compress
"""
    completed = run_powershell(script)
    if completed.returncode != 0:
        detail = completed.stderr or completed.stdout or completed.failure or "unknown command failure"
        return SSHDebugCheck(
            identifier="ssh_listener",
            group="network",
            label="TCP listener",
            status="unknown",
            message=f"Get-NetTCPConnection failed: {detail}",
            command_suggestions=(),
            manual_advice=("Inspect exact listening TCP endpoints without using substring matches.",),
        )
    try:
        parsed: object = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return SSHDebugCheck(
            identifier="ssh_listener",
            group="network",
            label="TCP listener",
            status="unknown",
            message="Get-NetTCPConnection returned invalid JSON endpoint data",
            command_suggestions=(),
            manual_advice=("Inspect Get-NetTCPConnection output manually.",),
        )
    rows = _object_list(parsed)
    if rows is None:
        return SSHDebugCheck(
            identifier="ssh_listener",
            group="network",
            label="TCP listener",
            status="unknown",
            message="Get-NetTCPConnection returned malformed endpoint data",
            command_suggestions=(),
            manual_advice=("Inspect Get-NetTCPConnection output manually.",),
        )

    endpoints: dict[int, list[tuple[str, bool, int]]] = {port: [] for port in ports}
    for row in rows:
        address = row.get("LocalAddress")
        port = row.get("LocalPort")
        owning_process = row.get("OwningProcess")
        owned_by_sshd = row.get("OwnedBySshd")
        if (
            not isinstance(address, str)
            or not isinstance(port, int)
            or isinstance(port, bool)
            or not isinstance(owning_process, int)
            or isinstance(owning_process, bool)
            or not isinstance(owned_by_sshd, bool)
        ):
            return SSHDebugCheck(
                identifier="ssh_listener",
                group="network",
                label="TCP listener",
                status="unknown",
                message="Get-NetTCPConnection returned a malformed endpoint",
                command_suggestions=(),
                manual_advice=("Inspect Get-NetTCPConnection output manually.",),
            )
        if port in endpoints:
            endpoints[port].append((address, owned_by_sshd, owning_process))
    missing_ports = [port for port, records in endpoints.items() if not records]
    if missing_ports:
        return SSHDebugCheck(
            identifier="ssh_listener",
            group="network",
            label="TCP listener",
            status="error",
            message=f"No exact listening endpoint for TCP port(s) {', '.join(map(str, missing_ports))}",
            command_suggestions=(),
            manual_advice=("Review the sshd service and effective ListenAddress settings.",),
        )
    loopback_ports: list[int] = []
    invalid_addresses: list[int] = []
    wrong_owners: dict[int, tuple[int, ...]] = {}
    for port, records in endpoints.items():
        external_records: list[tuple[str, bool, int]] = []
        for record in records:
            address = record[0]
            if address in ("0.0.0.0", "::"):
                external_records.append(record)
                continue
            try:
                if not ipaddress.ip_address(address.split("%", maxsplit=1)[0]).is_loopback:
                    external_records.append(record)
            except ValueError:
                invalid_addresses.append(port)
        if not external_records and port not in invalid_addresses:
            loopback_ports.append(port)
            continue
        if external_records and not any(owned_by_sshd for _address, owned_by_sshd, _process_id in external_records):
            wrong_owners[port] = tuple(dict.fromkeys(process_id for _address, _owned_by_sshd, process_id in external_records))
    if loopback_ports:
        return SSHDebugCheck(
            identifier="ssh_listener",
            group="network",
            label="TCP listener",
            status="error",
            message=f"TCP port(s) {', '.join(map(str, loopback_ports))} listen only on loopback addresses",
            command_suggestions=(),
            manual_advice=("Review effective ListenAddress settings with sshd -T.",),
        )
    if invalid_addresses:
        return SSHDebugCheck(
            identifier="ssh_listener",
            group="network",
            label="TCP listener",
            status="unknown",
            message=f"Listener addresses could not be classified for port(s) {sorted(set(invalid_addresses))}",
            command_suggestions=(),
            manual_advice=("Inspect Get-NetTCPConnection output manually.",),
        )
    if wrong_owners:
        details = ", ".join(f"{port}: PID(s) {owners}" for port, owners in wrong_owners.items())
        return SSHDebugCheck(
            identifier="ssh_listener",
            group="network",
            label="TCP listener",
            status="error",
            message=f"Effective SSH port(s) are not owned by the registered sshd service ({details})",
            command_suggestions=(),
            manual_advice=("Stop or reconfigure the conflicting process before starting the sshd service.",),
        )
    return SSHDebugCheck(
        identifier="ssh_listener",
        group="network",
        label="TCP listener",
        status="ok",
        message=f"The registered sshd service owns exact non-loopback listener(s) for TCP port(s) {', '.join(map(str, ports))}",
        command_suggestions=(),
        manual_advice=(),
    )
