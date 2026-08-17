import re

from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_common import run_argv
from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_models import SSHDebugCheck


UFW_RULE_PATTERN = re.compile(
    r"^\[\s*(?P<number>\d+)\]\s+(?P<target>\S+)(?:\s+\(v6\))?\s+"
    r"(?P<action>ALLOW|DENY|REJECT)\s+IN\s+(?P<source>.+)$"
)


def _check_ufw(ports: tuple[int, ...]) -> SSHDebugCheck | None:
    completed = run_argv(("ufw", "status", "numbered"))
    if completed.returncode != 0:
        return None
    status_lines = [line.strip() for line in completed.stdout.splitlines() if line.strip().startswith("Status:")]
    if status_lines != ["Status: active"]:
        return None

    parsed_rules: list[tuple[int, str, str, str]] = []
    for line in completed.stdout.splitlines():
        match = UFW_RULE_PATTERN.fullmatch(line.strip())
        if match is not None:
            parsed_rules.append(
                (int(match.group("number")), match.group("target"), match.group("action"), match.group("source"))
            )
    unproved_ports: list[int] = []
    for port in ports:
        relevant: list[tuple[int, str, bool]] = []
        for number, target, action, source in parsed_rules:
            target_port, separator, protocol = target.partition("/")
            exact_target = separator == "/" and protocol == "tcp" and target_port.isdecimal() and int(target_port) == port
            global_block = target == "Anywhere" and action in ("DENY", "REJECT")
            if source.startswith("Anywhere") and (exact_target or global_block):
                relevant.append((number, action, exact_target))
        relevant.sort(key=lambda rule: rule[0])
        if relevant and relevant[0][1] in ("DENY", "REJECT"):
            return SSHDebugCheck(
                identifier="firewall",
                group="firewall",
                label="Inbound firewall",
                status="error",
                message=f"The first matching UFW rule explicitly blocks TCP port {port}",
                command_suggestions=("sudo ufw status numbered",),
                manual_advice=("Review UFW rule order before changing or deleting a blocking rule.",),
            )
        if not relevant or relevant[0][1] != "ALLOW" or not relevant[0][2]:
            unproved_ports.append(port)
    if unproved_ports:
        return SSHDebugCheck(
            identifier="firewall",
            group="firewall",
            label="Inbound firewall",
            status="unknown",
            message=f"Active UFW has no provable first-match TCP allow for port(s) {', '.join(map(str, unproved_ports))}",
            command_suggestions=tuple(f"sudo ufw allow {port}/tcp" for port in unproved_ports),
            manual_advice=("Review existing numbered rules and source restrictions before adding rules.",),
        )
    return SSHDebugCheck(
        identifier="firewall",
        group="firewall",
        label="Inbound firewall",
        status="ok",
        message=f"Active UFW has first-match inbound TCP allow rules for port(s) {', '.join(map(str, ports))}",
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
        generic_blocks = [
            rule
            for rule in rich_rules.stdout.splitlines()
            if re.search(r"\b(drop|reject)\b", rule) is not None and " port " not in rule
        ]
        if generic_blocks:
            return SSHDebugCheck(
                identifier="firewall",
                group="firewall",
                label="Inbound firewall",
                status="unknown",
                message=f"firewalld zone {zone} has generic rich block rules whose SSH effect is not provable",
                command_suggestions=(),
                manual_advice=("Evaluate rich-rule source scopes and priorities for the effective SSH ports.",),
            )
        for port in ports:
            exact_port = re.compile(rf'port port="{port}" protocol="tcp"')
            blocking_rules = [
                rule
                for rule in rich_rules.stdout.splitlines()
                if exact_port.search(rule) is not None and re.search(r"\b(drop|reject)\b", rule) is not None
            ]
            if blocking_rules:
                return SSHDebugCheck(
                    identifier="firewall",
                    group="firewall",
                    label="Inbound firewall",
                    status="error",
                    message=f"firewalld zone {zone} explicitly blocks TCP port {port}",
                    command_suggestions=(),
                    manual_advice=("Review the matching rich rule and its priority.",),
                )
            query = run_argv(("firewall-cmd", f"--zone={zone}", f"--query-port={port}/tcp"))
            if query.returncode != 0 or query.stdout != "yes":
                target = run_argv(("firewall-cmd", f"--zone={zone}", "--get-target"))
                if target.returncode == 0 and target.stdout in ("DROP", "REJECT"):
                    return SSHDebugCheck(
                        identifier="firewall",
                        group="firewall",
                        label="Inbound firewall",
                        status="error",
                        message=f"firewalld zone {zone} blocks by default and has no exact TCP allow for port {port}",
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
