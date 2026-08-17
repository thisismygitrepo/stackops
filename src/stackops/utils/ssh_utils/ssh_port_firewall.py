import ipaddress
import os
import re

from stackops.utils.ssh_utils.ssh_port_commands import (
    capture_checked_command,
    resolve_trusted_system_command,
    run_command,
)
from stackops.utils.ssh_utils.ssh_port_packet_filter import (
    assert_iptables_permission,
    assert_nftables_permission,
)
from stackops.utils.ssh_utils.ssh_port_preflight import PortChangePlan


def _ufw_status(plan: PortChangePlan) -> tuple[bool, str]:
    ufw_path = resolve_trusted_system_command(command_name="ufw")
    if ufw_path is None:
        return False, ""
    result = run_command((*plan.privilege_prefix, str(ufw_path), "status", "numbered"))
    if result.returncode != 0:
        error_output = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Unable to inspect UFW status: {error_output}")
    is_active = any(line.strip().lower() == "status: active" for line in result.stdout.splitlines())
    return is_active, result.stdout


def _firewalld_is_active(plan: PortChangePlan) -> bool:
    firewall_path = resolve_trusted_system_command(command_name="firewall-cmd")
    if firewall_path is None:
        return False
    result = run_command((*plan.privilege_prefix, str(firewall_path), "--state"))
    state_output = result.stdout.strip() or result.stderr.strip()
    if result.returncode == 0 and state_output == "running":
        return True
    if "not running" in state_output.lower():
        return False
    raise RuntimeError(f"Unable to inspect firewalld state: {state_output}")


def _assert_ufw_permission(status_output: str, target_port: int) -> None:
    ssh_connection = os.environ.get("SSH_CONNECTION", "").split()
    client_address: ipaddress.IPv4Address | ipaddress.IPv6Address | None = None
    if len(ssh_connection) == 4:
        try:
            client_address = ipaddress.ip_address(ssh_connection[0])
        except ValueError:
            client_address = None

    for raw_line in status_output.splitlines():
        line = re.sub(r"^\[\s*\d+\]\s*", "", raw_line.strip())
        fields = re.split(r"\s{2,}", line)
        if len(fields) != 3:
            continue
        target, action, source = fields
        is_ipv6_rule = "(v6)" in target or "(v6)" in source
        if client_address is not None and (client_address.version == 6) != is_ipv6_rule:
            continue
        normalized_target = target.replace("(v6)", "").strip()
        normalized_source = source.replace("(v6)", "").strip()
        exact_target = normalized_target.casefold() == f"{target_port}/tcp"
        global_target = normalized_target.casefold() == "anywhere"
        normalized_action = action.casefold()
        is_block = normalized_action.startswith("deny") or normalized_action.startswith("reject")
        is_allow = normalized_action.startswith("allow")
        if not exact_target and not global_target:
            if is_block:
                raise RuntimeError(
                    "Active UFW contains a named or otherwise unresolved blocking rule, so safe ingress cannot be proven. "
                    "Review `sudo ufw status numbered`, then retry."
                )
            continue
        if normalized_source.casefold() == "anywhere":
            source_applies: bool | None = True
        elif client_address is None:
            source_applies = None
        else:
            try:
                source_applies = client_address in ipaddress.ip_network(normalized_source, strict=False)
            except ValueError:
                source_applies = None
        if source_applies is False:
            continue
        if source_applies is None:
            raise RuntimeError(
                f"Active UFW has a scoped rule affecting TCP port {target_port}, but its applicability cannot be proven. "
                "Review `sudo ufw status numbered`, then retry."
            )
        if is_block:
            raise RuntimeError(
                f"The first applicable UFW rule blocks TCP port {target_port}. Run `sudo ufw status numbered`, "
                "delete or narrow the blocking rule, then retry."
            )
        if is_allow:
            return
        raise RuntimeError(
            f"Active UFW returned an unsupported action for TCP port {target_port}: {action!r}. Review the rule, then retry."
        )
    raise RuntimeError(
        f"Active UFW has no provably applicable inbound allow for TCP port {target_port}. "
        f"Run `sudo ufw allow {target_port}/tcp`, then retry."
    )


def _active_firewalld_zones(plan: PortChangePlan, target_port: int) -> tuple[str, ...]:
    firewall_path = resolve_trusted_system_command(command_name="firewall-cmd")
    if firewall_path is None:
        raise RuntimeError("firewalld became unavailable during SSH port preflight.")
    output = capture_checked_command(
        command=(*plan.privilege_prefix, str(firewall_path), "--get-active-zones"),
        failure_message="Unable to inspect active firewalld zones",
    )
    zones = tuple(line.strip() for line in output.splitlines() if line != "" and not line[0].isspace())
    if len(zones) == 1:
        return zones
    ssh_connection = os.environ.get("SSH_CONNECTION", "").split()
    ip_path = resolve_trusted_system_command(command_name="ip")
    if len(zones) > 1 and len(ssh_connection) == 4 and ip_path is not None:
        route = run_command((str(ip_path), "route", "get", ssh_connection[0]))
        route_fields = route.stdout.split()
        if route.returncode == 0 and "dev" in route_fields:
            interface_index = route_fields.index("dev") + 1
            if interface_index < len(route_fields):
                zone_result = run_command(
                    (
                        *plan.privilege_prefix,
                        str(firewall_path),
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
        command=(*plan.privilege_prefix, str(firewall_path), "--get-default-zone"),
        failure_message="Unable to inspect the default firewalld zone",
    ).strip()
    if default_zone == "":
        raise RuntimeError("firewalld is active but has no active or default zone; configure a zone, then retry.")
    return (default_zone,)


def _assert_firewalld_permission(plan: PortChangePlan, target_port: int) -> None:
    firewall_path = resolve_trusted_system_command(command_name="firewall-cmd")
    if firewall_path is None:
        raise RuntimeError("firewalld became unavailable during SSH port preflight.")
    for permanence in ((), ("--permanent",)):
        policies = run_command(
            (*plan.privilege_prefix, str(firewall_path), *permanence, "--get-policies")
        )
        if policies.returncode != 0:
            raise RuntimeError(
                f"Unable to inspect {'permanent ' if permanence else ''}firewalld policy objects."
            )
        if policies.stdout.strip() != "":
            raise RuntimeError(
                f"firewalld has {'permanent ' if permanence else ''}policy objects, so TCP port {target_port} "
                "cannot be proven safe without evaluating policy ingress, egress, scopes, and priorities."
            )
    missing_zones: list[str] = []
    for zone in _active_firewalld_zones(plan=plan, target_port=target_port):
        for permanence in ((), ("--permanent",)):
            rich_rules = run_command(
                (*plan.privilege_prefix, str(firewall_path), *permanence, f"--zone={zone}", "--list-rich-rules")
            )
            direct_rules = run_command(
                (*plan.privilege_prefix, str(firewall_path), *permanence, "--direct", "--get-all-rules")
            )
            if rich_rules.returncode != 0 or direct_rules.returncode != 0:
                raise RuntimeError(f"Unable to inspect all {'permanent ' if permanence else ''}firewalld rules for zone {zone}.")
            if rich_rules.stdout.strip() != "" or direct_rules.stdout.strip() != "":
                raise RuntimeError(
                    f"firewalld has {'permanent ' if permanence else ''}rich or direct rules, so TCP port {target_port} "
                    "cannot be proven safe without evaluating rule scopes and priorities."
                )
        runtime_result = run_command(
            (*plan.privilege_prefix, str(firewall_path), f"--zone={zone}", f"--query-port={target_port}/tcp")
        )
        permanent_result = run_command(
            (
                *plan.privilege_prefix,
                str(firewall_path),
                "--permanent",
                f"--zone={zone}",
                f"--query-port={target_port}/tcp",
            )
        )
        runtime_allowed = runtime_result.returncode == 0 and runtime_result.stdout.strip() == "yes"
        permanent_allowed = permanent_result.returncode == 0 and permanent_result.stdout.strip() == "yes"
        if runtime_allowed and permanent_allowed:
            continue
        if runtime_result.returncode not in {0, 1}:
            error_output = runtime_result.stderr.strip() or runtime_result.stdout.strip()
            raise RuntimeError(f"Unable to inspect firewalld zone {zone}: {error_output}")
        if permanent_result.returncode not in {0, 1}:
            error_output = permanent_result.stderr.strip() or permanent_result.stdout.strip()
            raise RuntimeError(f"Unable to inspect permanent firewalld zone {zone}: {error_output}")
        missing_zones.append(zone)
    if len(missing_zones) == 0:
        return
    zone_commands = " && ".join(
        f"sudo firewall-cmd --permanent --zone={zone} --add-port={target_port}/tcp" for zone in missing_zones
    )
    displayed_zones = ", ".join(missing_zones)
    raise RuntimeError(
        f"Active and permanent firewalld policy do not both allow TCP port {target_port} in zone(s) {displayed_zones}. "
        f"Run `{zone_commands} && sudo firewall-cmd --reload`, then retry."
    )


def preflight_host_firewall(plan: PortChangePlan, target_port: int) -> None:
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
    assert_nftables_permission(plan=plan, target_port=target_port)
    assert_iptables_permission(plan=plan, command_name="iptables", target_port=target_port)
    assert_iptables_permission(plan=plan, command_name="ip6tables", target_port=target_port)
