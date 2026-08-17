import json
import re
from pathlib import Path
from typing import cast

from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_models import SSHDebugCheck
from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_windows_utils import run_powershell


def _json_object(output: str) -> dict[str, object] | None:
    try:
        parsed: object = json.loads(output)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    return cast(dict[str, object], parsed)


def _object_list(value: object) -> list[dict[str, object]] | None:
    if value is None:
        return []
    if isinstance(value, dict):
        return [cast(dict[str, object], value)]
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        return None
    return [cast(dict[str, object], item) for item in value]


def _string_list(value: object) -> list[str] | None:
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return cast(list[str], value)


def _port_filter_matches(local_port: str, port: int) -> bool:
    for token in re.split(r"[,\s]+", local_port):
        if token in ("Any", "*"):
            return True
        if token.isdecimal() and int(token) == port:
            return True
        first, separator, last = token.partition("-")
        if separator and first.isdecimal() and last.isdecimal() and int(first) <= port <= int(last):
            return True
    return False


def _rule_applies_to_sshd(rule: dict[str, object], sshd_path: Path) -> bool | None:
    programs = _string_list(rule.get("Programs"))
    services = _string_list(rule.get("Services"))
    if programs is None or services is None:
        return None
    normalized_path = str(sshd_path).casefold()
    program_matches = any(program in ("Any", "*") or program.casefold() == normalized_path for program in programs)
    service_matches = any(service in ("Any", "*", "sshd") for service in services)
    return program_matches and service_matches


def _rule_is_unscoped(rule: dict[str, object]) -> bool | None:
    remote_ports = _string_list(rule.get("RemotePort"))
    local_addresses = _string_list(rule.get("LocalAddresses"))
    remote_addresses = _string_list(rule.get("RemoteAddresses"))
    interface_types = _string_list(rule.get("InterfaceTypes"))
    interface_aliases = _string_list(rule.get("InterfaceAliases"))
    if (
        remote_ports is None
        or local_addresses is None
        or remote_addresses is None
        or interface_types is None
        or interface_aliases is None
    ):
        return None
    remote_port_any = any(remote_port in ("Any", "*") for remote_port in remote_ports)
    local_any = any(address in ("Any", "*") for address in local_addresses)
    remote_any = any(address in ("Any", "*") for address in remote_addresses)
    interface_type_any = any(interface_type in ("Any", "All", "*") for interface_type in interface_types)
    interface_alias_any = any(interface_alias in ("Any", "All", "*") for interface_alias in interface_aliases)
    return remote_port_any and local_any and remote_any and interface_type_any and interface_alias_any


def check_windows_firewall(ports: tuple[int, ...], sshd_path: Path) -> SSHDebugCheck:
    script = """
$ErrorActionPreference = 'Stop'
$profileBits = @{ DomainAuthenticated = 1; Private = 2; Public = 4 }
$activeBits = @(Get-NetConnectionProfile | ForEach-Object {
    $category = [string]$_.NetworkCategory
    $profileBits[$category]
} |
    Where-Object { $null -ne $_ } | Sort-Object -Unique)
$profiles = @(foreach ($bit in $activeBits) {
    $name = switch ($bit) { 1 { 'Domain' } 2 { 'Private' } 4 { 'Public' } }
    $profile = Get-NetFirewallProfile -PolicyStore ActiveStore -Name $name
    [PSCustomObject]@{
        Bit = [int]$bit
        Name = $name
        Enabled = [string]$profile.Enabled
        DefaultInboundAction = [string]$profile.DefaultInboundAction
    }
})
$rules = @(Get-NetFirewallRule -PolicyStore ActiveStore -Direction Inbound -Enabled True | ForEach-Object {
    $rule = $_
    $portFilters = @(Get-NetFirewallPortFilter -AssociatedNetFirewallRule $rule)
    $applicationFilters = @(Get-NetFirewallApplicationFilter -AssociatedNetFirewallRule $rule)
    $serviceFilters = @(Get-NetFirewallServiceFilter -AssociatedNetFirewallRule $rule)
    $addressFilters = @(Get-NetFirewallAddressFilter -AssociatedNetFirewallRule $rule)
    $interfaceTypeFilters = @(Get-NetFirewallInterfaceTypeFilter -AssociatedNetFirewallRule $rule)
    $interfaceFilters = @(Get-NetFirewallInterfaceFilter -AssociatedNetFirewallRule $rule)
    foreach ($portFilter in $portFilters) {
        [PSCustomObject]@{
            Name = $rule.Name
            Action = [string]$rule.Action
            Profile = [string]$rule.Profile
            Protocol = [string]$portFilter.Protocol
            LocalPort = [string]$portFilter.LocalPort
            RemotePort = @(@($portFilter.RemotePort) | ForEach-Object { [string]$_ })
            Programs = @($applicationFilters | ForEach-Object { [Environment]::ExpandEnvironmentVariables([string]$_.Program) })
            Services = @($serviceFilters | ForEach-Object { [string]$_.Service })
            LocalAddresses = @($addressFilters | ForEach-Object { @($_.LocalAddress) } | ForEach-Object { [string]$_ })
            RemoteAddresses = @($addressFilters | ForEach-Object { @($_.RemoteAddress) } | ForEach-Object { [string]$_ })
            InterfaceTypes = @($interfaceTypeFilters | ForEach-Object { @($_.InterfaceType) } | ForEach-Object { [string]$_ })
            InterfaceAliases = @($interfaceFilters | ForEach-Object { @($_.InterfaceAlias) } | ForEach-Object { [string]$_ })
        }
    }
})
[PSCustomObject]@{ Profiles = @($profiles); Rules = @($rules) } | ConvertTo-Json -Depth 7 -Compress
"""
    completed = run_powershell(script)
    parsed = _json_object(completed.stdout) if completed.returncode == 0 else None
    if parsed is None:
        detail = completed.stderr or completed.stdout or completed.failure or "invalid firewall output"
        return SSHDebugCheck(
            identifier="firewall",
            group="firewall",
            label="Windows Firewall",
            status="unknown",
            message=f"Firewall profiles and rules could not be inspected: {detail}",
            command_suggestions=(),
            manual_advice=("Inspect active firewall profiles and exact TCP port filters without relying on rule display names.",),
        )
    if "Profiles" not in parsed or "Rules" not in parsed:
        return SSHDebugCheck(
            identifier="firewall",
            group="firewall",
            label="Windows Firewall",
            status="unknown",
            message="Windows firewall output omitted required profile or rule evidence",
            command_suggestions=(),
            manual_advice=("Inspect active profiles and enabled inbound rules manually.",),
        )
    profiles = _object_list(parsed["Profiles"])
    rules = _object_list(parsed["Rules"])
    if profiles is None or rules is None or not profiles:
        return SSHDebugCheck(
            identifier="firewall",
            group="firewall",
            label="Windows Firewall",
            status="unknown",
            message="No well-formed active firewall profile evidence was returned",
            command_suggestions=(),
            manual_advice=("Determine the active network profiles before evaluating SSH rules.",),
        )

    unproved: list[str] = []
    for profile in profiles:
        bit = profile.get("Bit")
        name = profile.get("Name")
        enabled_value = profile.get("Enabled")
        default_action = profile.get("DefaultInboundAction")
        if (
            not isinstance(bit, int)
            or isinstance(bit, bool)
            or not isinstance(name, str)
            or not isinstance(enabled_value, str)
            or enabled_value not in ("True", "False")
        ):
            return SSHDebugCheck(
                identifier="firewall",
                group="firewall",
                label="Windows Firewall",
                status="unknown",
                message="Windows returned malformed firewall profile evidence",
                command_suggestions=(),
                manual_advice=("Inspect each active firewall profile manually.",),
            )
        if enabled_value == "False":
            continue
        for port in ports:
            exact_allows = 0
            scoped_allow_found = False
            for rule in rules:
                action = rule.get("Action")
                rule_profile = rule.get("Profile")
                protocol = rule.get("Protocol")
                local_port = rule.get("LocalPort")
                if (
                    not isinstance(action, str)
                    or not isinstance(rule_profile, str)
                    or not isinstance(protocol, str)
                    or not isinstance(local_port, str)
                ):
                    return SSHDebugCheck(
                        identifier="firewall",
                        group="firewall",
                        label="Windows Firewall",
                        status="unknown",
                        message="Windows returned a malformed firewall rule",
                        command_suggestions=(),
                        manual_advice=("Inspect enabled inbound rules and their associated filters.",),
                    )
                rule_profiles = {part.strip() for part in rule_profile.split(",")}
                profile_matches = "Any" in rule_profiles or name in rule_profiles
                if (
                    not profile_matches
                    or protocol.casefold() not in ("tcp", "6", "any", "256")
                    or not _port_filter_matches(local_port, port)
                ):
                    continue
                application_match = _rule_applies_to_sshd(rule, sshd_path)
                if application_match is None:
                    return SSHDebugCheck(
                        identifier="firewall",
                        group="firewall",
                        label="Windows Firewall",
                        status="unknown",
                        message="A matching firewall rule had malformed application or service filters",
                        command_suggestions=(),
                        manual_advice=("Inspect the associated application and service filters.",),
                    )
                if not application_match:
                    continue
                if action == "Block":
                    unscoped = _rule_is_unscoped(rule)
                    if unscoped is None:
                        return SSHDebugCheck(
                            identifier="firewall",
                            group="firewall",
                            label="Windows Firewall",
                            status="unknown",
                            message="A matching block rule had malformed remote-port, address, or interface filters",
                            command_suggestions=(),
                            manual_advice=("Inspect the associated port, address, and interface filters.",),
                        )
                    if not unscoped:
                        return SSHDebugCheck(
                            identifier="firewall",
                            group="firewall",
                            label="Windows Firewall",
                            status="unknown",
                            message=f"A scoped inbound block matches sshd TCP port {port} in the {name} profile",
                            command_suggestions=(),
                            manual_advice=("Determine whether the block's remote-port, address, and interface scopes apply to the client.",),
                        )
                    return SSHDebugCheck(
                        identifier="firewall",
                        group="firewall",
                        label="Windows Firewall",
                        status="error",
                        message=f"An enabled inbound block applies to sshd TCP port {port} in the {name} profile",
                        command_suggestions=(),
                        manual_advice=("Review the explicit block rule and its profile scope before changing it.",),
                    )
                if action == "Allow":
                    unscoped = _rule_is_unscoped(rule)
                    if unscoped is None:
                        return SSHDebugCheck(
                            identifier="firewall",
                            group="firewall",
                            label="Windows Firewall",
                            status="unknown",
                            message="A matching allow rule had malformed remote-port, address, or interface filters",
                            command_suggestions=(),
                            manual_advice=("Inspect remote-port, address, and interface scopes on the matching rule.",),
                        )
                    if unscoped:
                        exact_allows += 1
                    else:
                        scoped_allow_found = True
            if not exact_allows:
                if scoped_allow_found:
                    unproved.append(f"{name}:{port}/tcp (scoped allow)")
                    continue
                if default_action == "Block":
                    return SSHDebugCheck(
                        identifier="firewall",
                        group="firewall",
                        label="Windows Firewall",
                        status="error",
                        message=f"The {name} profile blocks inbound by default and has no unscoped TCP allow for port {port}",
                        command_suggestions=(
                            f'New-NetFirewallRule -Name "OpenSSH-{port}" -Direction Inbound -Protocol TCP -LocalPort {port} -Action Allow',
                        ),
                        manual_advice=("Choose the intended profiles and remote-address scope before creating a rule.",),
                    )
                unproved.append(f"{name}:{port}/tcp")
    if unproved:
        return SSHDebugCheck(
            identifier="firewall",
            group="firewall",
            label="Windows Firewall",
            status="unknown",
            message=f"No enabled unscoped inbound allow was proved for {', '.join(unproved)}",
            command_suggestions=(),
            manual_advice=("Create or adjust an exact TCP rule only after selecting the intended active profiles.",),
        )
    return SSHDebugCheck(
        identifier="firewall",
        group="firewall",
        label="Windows Firewall",
        status="ok",
        message=f"Every enabled active profile has an inbound allow and no matching block for TCP port(s) {', '.join(map(str, ports))}",
        command_suggestions=(),
        manual_advice=(),
    )
