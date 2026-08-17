import re

from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_common import run_argv
from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_models import SSHDebugCheck


UFW_RULE_PATTERN = re.compile(
    r"^\[\s*(?P<number>\d+)\]\s+(?P<target>\S+)(?:\s+(?P<ipv6>\(v6\)))?\s+"
    r"(?P<action>ALLOW|DENY|REJECT)\s+IN\s+(?P<source>.+)$"
)


def _check_ufw(ports: tuple[int, ...]) -> SSHDebugCheck | None:
    completed = run_argv(("ufw", "status", "numbered"))
    if completed.returncode != 0:
        return None
    status_lines = [line.strip() for line in completed.stdout.splitlines() if line.strip().startswith("Status:")]
    if status_lines != ["Status: active"]:
        return None

    parsed_rules: list[tuple[int, str, str, str, str]] = []
    for line in completed.stdout.splitlines():
        match = UFW_RULE_PATTERN.fullmatch(line.strip())
        if match is not None:
            parsed_rules.append(
                (
                    int(match.group("number")),
                    match.group("target"),
                    match.group("action"),
                    match.group("source"),
                    "ipv6" if match.group("ipv6") is not None else "ipv4",
                )
            )
    unproved: list[str] = []
    for port in ports:
        for family in ("ipv4", "ipv6"):
            relevant: list[tuple[int, str, bool]] = []
            for number, target, action, source, rule_family in parsed_rules:
                if rule_family != family:
                    continue
                target_port, separator, protocol = target.partition("/")
                exact_target = (
                    separator == "/"
                    and protocol == "tcp"
                    and target_port.isdecimal()
                    and int(target_port) == port
                )
                if exact_target or target == "Anywhere":
                    relevant.append((number, action, source.removesuffix(" (v6)") == "Anywhere"))
            relevant.sort(key=lambda rule: rule[0])
            if relevant and not relevant[0][2]:
                unproved.append(f"{family}:{port}/tcp (first rule is source-scoped)")
                continue
            if relevant and relevant[0][1] in ("DENY", "REJECT"):
                return SSHDebugCheck(
                    identifier="firewall",
                    group="firewall",
                    label="Inbound firewall",
                    status="error",
                    message=f"The first matching {family} UFW rule explicitly blocks TCP port {port}",
                    command_suggestions=("sudo ufw status numbered",),
                    manual_advice=("Review UFW rule order before changing or deleting a blocking rule.",),
                )
            if not relevant or relevant[0][1] != "ALLOW":
                unproved.append(f"{family}:{port}/tcp")
    if unproved:
        return SSHDebugCheck(
            identifier="firewall",
            group="firewall",
            label="Inbound firewall",
            status="unknown",
            message=f"Active UFW has no provable first-match allow for {', '.join(unproved)}",
            command_suggestions=(),
            manual_advice=("Review existing numbered rules and source restrictions before adding rules.",),
        )
    return SSHDebugCheck(
        identifier="firewall",
        group="firewall",
        label="Inbound firewall",
        status="ok",
        message=f"Active UFW has first-match IPv4 and IPv6 TCP allow rules for port(s) {', '.join(map(str, ports))}",
        command_suggestions=(),
        manual_advice=(),
    )


def _check_firewalld(ports: tuple[int, ...]) -> SSHDebugCheck | None:
    state = run_argv(("firewall-cmd", "--state"))
    if state.returncode != 0 or state.stdout != "running":
        return None
    active_zones = run_argv(("firewall-cmd", "--get-active-zones"))
    if active_zones.returncode != 0:
        detail = active_zones.stderr or active_zones.stdout or active_zones.failure or "unknown command failure"
        return SSHDebugCheck(
            identifier="firewall",
            group="firewall",
            label="Inbound firewall",
            status="unknown",
            message=f"firewalld is running but active profiles could not be read: {detail}",
            command_suggestions=(),
            manual_advice=("Inspect every active firewalld zone.",),
        )
    zones = [line.split()[0] for line in active_zones.stdout.splitlines() if line and not line[0].isspace()]
    if not zones:
        return SSHDebugCheck(
            identifier="firewall",
            group="firewall",
            label="Inbound firewall",
            status="unknown",
            message="firewalld is running but reported no active zone",
            command_suggestions=(),
            manual_advice=("Determine which firewalld zone applies to the incoming interface.",),
        )

    direct_rules = run_argv(("firewall-cmd", "--direct", "--get-all-rules"))
    if direct_rules.returncode != 0 or direct_rules.stdout:
        return SSHDebugCheck(
            identifier="firewall",
            group="firewall",
            label="Inbound firewall",
            status="unknown",
            message="Direct firewalld rules are present or could not be inspected, so zone allows are not conclusive",
            command_suggestions=(),
            manual_advice=("Evaluate direct rules together with active-zone rules.",),
        )

    unproved: list[str] = []
    for zone in zones:
        rich_rules = run_argv(("firewall-cmd", f"--zone={zone}", "--list-rich-rules"))
        if rich_rules.returncode != 0:
            unproved.append(f"{zone}: rich rules unavailable")
            continue
        if rich_rules.stdout:
            return SSHDebugCheck(
                identifier="firewall",
                group="firewall",
                label="Inbound firewall",
                status="unknown",
                message=f"firewalld zone {zone} has rich rules whose source scopes and priorities require contextual evaluation",
                command_suggestions=(),
                manual_advice=("Evaluate the rich rules for the actual SSH client address.",),
            )
        for port in ports:
            query = run_argv(("firewall-cmd", f"--zone={zone}", f"--query-port={port}/tcp"))
            if query.returncode == 0 and query.stdout == "yes":
                continue
            service_permission = _firewalld_service_allows_port(zone=zone, port=port)
            if service_permission is True:
                continue
            if service_permission is None:
                unproved.append(f"{zone}:{port}/tcp (service rules unavailable)")
                continue
            target = run_argv(("firewall-cmd", f"--zone={zone}", "--get-target"))
            if target.returncode == 0 and target.stdout in ("DROP", "REJECT"):
                return SSHDebugCheck(
                    identifier="firewall",
                    group="firewall",
                    label="Inbound firewall",
                    status="error",
                    message=f"firewalld zone {zone} blocks by default and has no TCP port or service allow for port {port}",
                    command_suggestions=(f"sudo firewall-cmd --permanent --zone={zone} --add-port={port}/tcp",),
                    manual_advice=("Confirm the interface-to-zone assignment before adding a permanent rule.",),
                )
            unproved.append(f"{zone}:{port}/tcp")
    if unproved:
        return SSHDebugCheck(
            identifier="firewall",
            group="firewall",
            label="Inbound firewall",
            status="unknown",
            message=f"No exact enabled allow was proved for {', '.join(unproved)}",
            command_suggestions=(),
            manual_advice=("Add explicit TCP port rules only to the active zones that should accept SSH.",),
        )
    return SSHDebugCheck(
        identifier="firewall",
        group="firewall",
        label="Inbound firewall",
        status="ok",
        message=f"Every active firewalld zone explicitly allows TCP port(s) {', '.join(map(str, ports))}",
        command_suggestions=(),
        manual_advice=(),
    )


def _firewalld_service_allows_port(zone: str, port: int) -> bool | None:
    listed_services = run_argv(("firewall-cmd", f"--zone={zone}", "--list-services"))
    if listed_services.returncode != 0:
        return None
    for service_name in listed_services.stdout.split():
        service_details = run_argv(("firewall-cmd", f"--info-service={service_name}"))
        if service_details.returncode != 0:
            return None
        port_lines = [line.strip().removeprefix("ports:").strip() for line in service_details.stdout.splitlines() if line.strip().startswith("ports:")]
        if len(port_lines) != 1:
            return None
        for port_specification in port_lines[0].split():
            port_value, separator, protocol = port_specification.partition("/")
            if separator != "/" or protocol.casefold() != "tcp":
                continue
            if port_value.isdecimal() and int(port_value) == port:
                return True
            first_port, range_separator, last_port = port_value.partition("-")
            if range_separator == "-" and first_port.isdecimal() and last_port.isdecimal():
                if int(first_port) <= port <= int(last_port):
                    return True
    return False


def check_linux_firewall(ports: tuple[int, ...]) -> SSHDebugCheck:
    ufw_check = _check_ufw(ports)
    firewalld_check = _check_firewalld(ports)
    active_checks = [check for check in (ufw_check, firewalld_check) if check is not None]
    if len(active_checks) == 2:
        error = next((check for check in active_checks if check.status == "error"), None)
        if error is not None:
            return error
        unknown = next((check for check in active_checks if check.status == "unknown"), None)
        if unknown is not None:
            return unknown
        return SSHDebugCheck(
            identifier="firewall",
            group="firewall",
            label="Inbound firewall",
            status="ok",
            message=f"Both active UFW and firewalld policies allow TCP port(s) {', '.join(map(str, ports))}",
            command_suggestions=(),
            manual_advice=(),
        )
    if active_checks:
        return active_checks[0]
    return SSHDebugCheck(
        identifier="firewall",
        group="firewall",
        label="Inbound firewall",
        status="unknown",
        message="No active UFW or firewalld policy could be verified; unmanaged nftables/iptables policy is unknown",
        command_suggestions=(),
        manual_advice=("Inspect the host's actual packet-filter backend for an exact inbound TCP allow.",),
    )
