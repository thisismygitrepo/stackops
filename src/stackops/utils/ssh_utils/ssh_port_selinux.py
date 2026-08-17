from pathlib import Path

from stackops.utils.ssh_utils.ssh_port_commands import (
    capture_checked_command,
    resolve_trusted_system_command,
    run_command,
)
from stackops.utils.ssh_utils.ssh_port_preflight import PortChangePlan


def _matching_port_spec(port_specification: str, target_port: int) -> str | None:
    for raw_range in port_specification.replace(",", " ").split():
        if "-" not in raw_range and raw_range.isdecimal() and int(raw_range) == target_port:
            return raw_range
        lower_text, separator, upper_text = raw_range.partition("-")
        if separator != "" and lower_text.isdecimal() and upper_text.isdecimal():
            if int(lower_text) <= target_port <= int(upper_text):
                return raw_range
    return None


def preflight_selinux(plan: PortChangePlan, target_port: int) -> None:
    getenforce_path = resolve_trusted_system_command(command_name="getenforce")
    if getenforce_path is None:
        if Path("/sys/fs/selinux/enforce").exists():
            raise RuntimeError("SELinux is present, but a trusted `getenforce` command is unavailable.")
        return
    enforcement = run_command((str(getenforce_path),))
    if enforcement.returncode != 0:
        error_output = enforcement.stderr.strip() or enforcement.stdout.strip()
        raise RuntimeError(f"Unable to inspect SELinux enforcement state: {error_output}")
    enforcement_state = enforcement.stdout.strip()
    if enforcement_state in {"Permissive", "Disabled"}:
        return
    if enforcement_state != "Enforcing":
        raise RuntimeError(f"SELinux returned an unrecognized enforcement state: {enforcement_state!r}")
    semanage_path = resolve_trusted_system_command(command_name="semanage")
    if semanage_path is None:
        raise RuntimeError(
            "SELinux is enforcing, but `semanage` is unavailable. Install policycoreutils-python-utils, "
            "then retry so the required port-label command can be determined."
        )
    port_listing = capture_checked_command(
        command=(*plan.privilege_prefix, str(semanage_path), "port", "-l"),
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
