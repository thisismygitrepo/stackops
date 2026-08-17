import os
import re
import shutil
from pathlib import Path

from stackops.utils.ssh_utils.ssh_port_commands import capture_checked_command, run_command
from stackops.utils.ssh_utils.ssh_port_preflight import PortChangePlan
from stackops.utils.ssh_utils.ssh_port_wsl_firewall import preflight_wsl_windows_firewall


def _ufw_status(plan: PortChangePlan) -> tuple[bool, str]:
    if shutil.which("ufw") is None:
        return False, ""
    result = run_command((*plan.privilege_prefix, "ufw", "status"))
    if result.returncode != 0:
        error_output = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Unable to inspect UFW status: {error_output}")
    is_active = any(line.strip().lower() == "status: active" for line in result.stdout.splitlines())
    return is_active, result.stdout


def _firewalld_is_active(plan: PortChangePlan) -> bool:
    if shutil.which("firewall-cmd") is None:
        return False
    result = run_command((*plan.privilege_prefix, "firewall-cmd", "--state"))
    state_output = result.stdout.strip() or result.stderr.strip()
    if result.returncode == 0 and state_output == "running":
        return True
    if "not running" in state_output.lower():
        return False
    raise RuntimeError(f"Unable to inspect firewalld state: {state_output}")


def _assert_ufw_permission(status_output: str, target_port: int) -> None:
    blocking_rule = any(
        re.match(rf"^\s*{target_port}/tcp(?:\s+\(v6\))?\s+(?:DENY|REJECT)\b", line, flags=re.IGNORECASE)
        is not None
        for line in status_output.splitlines()
    )
    if blocking_rule:
        raise RuntimeError(
            f"Active UFW has a blocking rule for TCP port {target_port}. Run `sudo ufw status numbered`, "
            "delete or narrow the blocking rule, then retry."
        )
    allowed = any(
        re.match(rf"^\s*{target_port}/tcp(?:\s+\(v6\))?\s+ALLOW(?:\s+IN)?\b", line, flags=re.IGNORECASE)
        is not None
        for line in status_output.splitlines()
    )
    if not allowed:
        raise RuntimeError(
            f"Active UFW does not explicitly allow inbound TCP port {target_port}. Run `sudo ufw allow {target_port}/tcp`, then retry."
        )


def _active_firewalld_zones(plan: PortChangePlan, target_port: int) -> tuple[str, ...]:
    output = capture_checked_command(
        command=(*plan.privilege_prefix, "firewall-cmd", "--get-active-zones"),
        failure_message="Unable to inspect active firewalld zones",
    )
    zones = tuple(line.strip() for line in output.splitlines() if line != "" and not line[0].isspace())
    if len(zones) == 1:
        return zones
    ssh_connection = os.environ.get("SSH_CONNECTION", "").split()
    ip_path = shutil.which("ip")
    if len(zones) > 1 and len(ssh_connection) == 4 and ip_path is not None:
        route = run_command((ip_path, "route", "get", ssh_connection[0]))
        route_fields = route.stdout.split()
        if route.returncode == 0 and "dev" in route_fields:
            interface_index = route_fields.index("dev") + 1
            if interface_index < len(route_fields):
                zone_result = run_command(
                    (
                        *plan.privilege_prefix,
                        "firewall-cmd",
                        f"--get-zone-of-interface={route_fields[interface_index]}",
                    )
                )
                ingress_zone = zone_result.stdout.strip()
                if zone_result.returncode == 0 and ingress_zone in zones:
                    return (ingress_zone,)
    if len(zones) > 1:
        displayed_zones = ", ".join(zones)
        raise RuntimeError(
            f"Multiple firewalld zones are active ({displayed_zones}), and the SSH ingress zone cannot be determined. "
            f"Run `sudo firewall-cmd --permanent --zone=<ingress-zone> --add-port={target_port}/tcp && "
            "sudo firewall-cmd --reload`, then retry."
        )
    default_zone = capture_checked_command(
        command=(*plan.privilege_prefix, "firewall-cmd", "--get-default-zone"),
        failure_message="Unable to inspect the default firewalld zone",
    ).strip()
    if default_zone == "":
        raise RuntimeError("firewalld is active but has no active or default zone; configure a zone, then retry.")
    return (default_zone,)


def _assert_firewalld_permission(plan: PortChangePlan, target_port: int) -> None:
    missing_zones: list[str] = []
    for zone in _active_firewalld_zones(plan=plan, target_port=target_port):
        result = run_command(
            (*plan.privilege_prefix, "firewall-cmd", f"--zone={zone}", f"--query-port={target_port}/tcp")
        )
        if result.returncode == 0 and result.stdout.strip() == "yes":
            continue
        if result.returncode not in {0, 1}:
            error_output = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(f"Unable to inspect firewalld zone {zone}: {error_output}")
        missing_zones.append(zone)
    if len(missing_zones) == 0:
        return
    zone_commands = " && ".join(
        f"sudo firewall-cmd --permanent --zone={zone} --add-port={target_port}/tcp" for zone in missing_zones
    )
    displayed_zones = ", ".join(missing_zones)
    raise RuntimeError(
        f"Active firewalld does not allow TCP port {target_port} in zone(s) {displayed_zones}. "
        f"Run `{zone_commands} && sudo firewall-cmd --reload`, then retry."
    )


def _nft_input_chains(ruleset: str) -> tuple[str, ...]:
    return tuple(
        match.group(1)
        for match in re.finditer(r"chain\s+\S+\s*\{([^}]*(?:hook\s+input)[^}]*)\}", ruleset, flags=re.DOTALL)
    )


def _assert_nftables_permission(plan: PortChangePlan, target_port: int) -> bool:
    if shutil.which("nft") is None:
        return False
    result = run_command((*plan.privilege_prefix, "nft", "list", "ruleset"))
    if result.returncode != 0:
        error_output = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Unable to inspect nftables rules: {error_output}")
    input_chains = _nft_input_chains(result.stdout)
    if any(re.search(r"\b(?:jump|goto)\b", chain, flags=re.IGNORECASE) is not None for chain in input_chains):
        raise RuntimeError(
            f"Active nftables input filtering uses indirect chains, so TCP port {target_port} cannot be proven safe. "
            f"Add a direct `tcp dport {target_port} accept` rule before the jump in each applicable input chain, then retry."
        )
    restrictive_chains = tuple(
        chain
        for chain in input_chains
        if re.search(r"\b(?:drop|reject)\b", chain, flags=re.IGNORECASE) is not None
    )
    if len(restrictive_chains) == 0:
        return False
    explicit_allow = all(
        re.search(rf"\btcp\s+dport\s+{target_port}\b[^;\n]*\baccept\b", chain, flags=re.IGNORECASE) is not None
        for chain in restrictive_chains
    )
    if not explicit_allow:
        raise RuntimeError(
            f"Active nftables input filtering does not explicitly accept TCP port {target_port}. "
            f"Add `tcp dport {target_port} accept` to the applicable input chain and persist the rule, then retry."
        )
    return True


def _assert_iptables_permission(plan: PortChangePlan, command_name: str, target_port: int) -> None:
    command_path = shutil.which(command_name)
    if command_path is None:
        return
    result = run_command((*plan.privilege_prefix, command_path, "-S", "INPUT"))
    if result.returncode != 0:
        error_output = result.stderr.strip() or result.stdout.strip()
        unsupported_ipv6 = command_name == "ip6tables" and (
            "table does not exist" in error_output.lower() or "protocol not supported" in error_output.lower()
        )
        if unsupported_ipv6:
            return
        raise RuntimeError(f"Unable to inspect {command_name} input filtering: {error_output}")
    lines = tuple(line.strip() for line in result.stdout.splitlines())
    restrictive = any(
        line == "-P INPUT DROP" or " -j DROP" in line or " -j REJECT" in line
        for line in lines
    )
    if not restrictive:
        return
    explicit_allow = any(
        "-p tcp" in line and f"--dport {target_port}" in line and "-j ACCEPT" in line
        for line in lines
    )
    if explicit_allow:
        return
    raise RuntimeError(
        f"Active {command_name} input filtering does not explicitly accept TCP port {target_port}. "
        f"Run `sudo {command_name} -I INPUT -p tcp --dport {target_port} -j ACCEPT`, persist the rule with "
        "your firewall tooling, then retry."
    )


def _assert_firewall_permission(plan: PortChangePlan, target_port: int) -> None:
    ufw_active, ufw_output = _ufw_status(plan=plan)
    firewalld_active = _firewalld_is_active(plan=plan)
    if ufw_active and firewalld_active:
        raise RuntimeError("UFW and firewalld are both active; leave one firewall manager active and prepare the target port, then retry.")
    if ufw_active:
        _assert_ufw_permission(status_output=ufw_output, target_port=target_port)
        return
    if firewalld_active:
        _assert_firewalld_permission(plan=plan, target_port=target_port)
        return
    if _assert_nftables_permission(plan=plan, target_port=target_port):
        return
    _assert_iptables_permission(plan=plan, command_name="iptables", target_port=target_port)
    _assert_iptables_permission(plan=plan, command_name="ip6tables", target_port=target_port)


def _matching_port_spec(port_specification: str, target_port: int) -> str | None:
    for raw_range in port_specification.replace(",", " ").split():
        if "-" not in raw_range and raw_range.isdecimal() and int(raw_range) == target_port:
            return raw_range
        lower_text, separator, upper_text = raw_range.partition("-")
        if separator != "" and lower_text.isdecimal() and upper_text.isdecimal():
            if int(lower_text) <= target_port <= int(upper_text):
                return raw_range
    return None


def _assert_selinux_permission(plan: PortChangePlan, target_port: int) -> None:
    discovered_getenforce = shutil.which("getenforce")
    getenforce_path = discovered_getenforce or (
        "/usr/sbin/getenforce" if Path("/usr/sbin/getenforce").is_file() else None
    )
    if getenforce_path is None:
        return
    enforcement = run_command((getenforce_path,))
    if enforcement.returncode != 0 or enforcement.stdout.strip() != "Enforcing":
        return
    discovered_semanage = shutil.which("semanage")
    semanage_path = discovered_semanage or (
        "/usr/sbin/semanage" if Path("/usr/sbin/semanage").is_file() else None
    )
    if semanage_path is None:
        raise RuntimeError(
            "SELinux is enforcing, but `semanage` is unavailable. Install policycoreutils-python-utils, "
            "then retry so the required port-label command can be determined."
        )
    port_listing = capture_checked_command(
        command=(*plan.privilege_prefix, semanage_path, "port", "-l"),
        failure_message="Unable to inspect SELinux port labels",
    )
    assigned_type: str | None = None
    assigned_specification: str | None = None
    for line in port_listing.splitlines():
        fields = line.split(maxsplit=2)
        if len(fields) != 3 or fields[1] != "tcp":
            continue
        matching_specification = _matching_port_spec(port_specification=fields[2], target_port=target_port)
        if matching_specification is None:
            continue
        assigned_type = fields[0]
        assigned_specification = matching_specification
        break
    if assigned_type == "ssh_port_t":
        return
    if assigned_specification is not None and "-" in assigned_specification:
        raise RuntimeError(
            f"SELinux is enforcing and TCP port {target_port} is inside range {assigned_specification}, labeled {assigned_type}. "
            "Choose a target port outside that range or split and relabel the range with semanage, then retry."
        )
    operation = "-a" if assigned_type is None else "-m"
    detail = "is not labeled" if assigned_type is None else f"is labeled {assigned_type} instead of"
    raise RuntimeError(
        f"SELinux is enforcing and TCP port {target_port} {detail} ssh_port_t. "
        f"Run `sudo semanage port {operation} -t ssh_port_t -p tcp {target_port}`, then retry."
    )


def preflight_host_security(plan: PortChangePlan, target_port: int) -> None:
    _assert_firewall_permission(plan=plan, target_port=target_port)
    preflight_wsl_windows_firewall(target_port=target_port)
    _assert_selinux_permission(plan=plan, target_port=target_port)
