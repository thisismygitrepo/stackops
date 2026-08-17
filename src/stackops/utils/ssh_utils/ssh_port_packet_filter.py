import re

from stackops.utils.ssh_utils.ssh_port_commands import resolve_trusted_system_command, run_command
from stackops.utils.ssh_utils.ssh_port_preflight import PortChangePlan


def assert_nftables_permission(plan: PortChangePlan, target_port: int) -> None:
    nft_path = resolve_trusted_system_command(command_name="nft")
    if nft_path is None:
        return
    result = run_command((*plan.privilege_prefix, str(nft_path), "list", "ruleset"))
    if result.returncode != 0:
        error_output = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Unable to inspect nftables rules: {error_output}")
    input_chains = tuple(
        match.group(1)
        for match in re.finditer(
            r"chain\s+\S+\s*\{([^}]*(?:hook\s+input)[^}]*)\}",
            result.stdout,
            flags=re.DOTALL,
        )
    )
    if any(re.search(r"\b(?:jump|goto)\b", chain, flags=re.IGNORECASE) is not None for chain in input_chains):
        raise RuntimeError(
            f"Active nftables input filtering uses indirect chains, so TCP port {target_port} cannot be proven safe. "
            f"Add a direct `tcp dport {target_port} accept` rule before the jump in each applicable input chain, then retry."
        )
    if not any(re.search(r"\b(?:drop|reject)\b", chain, flags=re.IGNORECASE) is not None for chain in input_chains):
        return
    raise RuntimeError(
        f"Active nftables input filtering contains drop/reject policy whose ordering and ingress applicability cannot be proven safely. "
        f"Verify and persist an applicable `tcp dport {target_port} accept` rule before all terminal blocks, then retry."
    )


def assert_iptables_permission(plan: PortChangePlan, command_name: str, target_port: int) -> None:
    command_path = resolve_trusted_system_command(command_name=command_name)
    if command_path is None:
        return
    result = run_command((*plan.privilege_prefix, str(command_path), "-S", "INPUT"))
    if result.returncode != 0:
        error_output = result.stderr.strip() or result.stdout.strip()
        unsupported_ipv6 = command_name == "ip6tables" and (
            "table does not exist" in error_output.lower() or "protocol not supported" in error_output.lower()
        )
        if unsupported_ipv6:
            return
        raise RuntimeError(f"Unable to inspect {command_name} input filtering: {error_output}")
    lines = tuple(line.strip() for line in result.stdout.splitlines())
    input_is_unrestricted = lines == ("-P INPUT ACCEPT",) or (
        len(lines) > 0
        and lines[0] == "-P INPUT ACCEPT"
        and all(" -j ACCEPT" in line for line in lines[1:])
    )
    if input_is_unrestricted:
        return
    raise RuntimeError(
        f"Active {command_name} input filtering has ordering, jumps, or terminal policy whose applicability to TCP port "
        f"{target_port} cannot be proven safely. Add an applicable allow before terminal rules, persist it, then retry."
    )
