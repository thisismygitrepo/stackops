import re
from pathlib import Path

from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_common import run_argv
from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_models import SSHDebugCheck


def check_packet_filter(ports: tuple[int, ...]) -> SSHDebugCheck:
    status = run_argv(("/sbin/pfctl", "-s", "info"))
    if status.returncode != 0:
        detail = status.stderr or status.stdout or status.failure or "unknown command failure"
        return SSHDebugCheck(
            identifier="packet_filter",
            group="firewall",
            label="Packet Filter",
            status="unknown",
            message=f"PF state could not be inspected without elevation: {detail}",
            command_suggestions=(),
            manual_advice=("Inspect PF rules separately from the macOS application firewall.",),
        )
    state_lines = [line.strip() for line in status.stdout.splitlines() if line.strip().startswith("Status:")]
    if len(state_lines) != 1:
        return SSHDebugCheck(
            identifier="packet_filter",
            group="firewall",
            label="Packet Filter",
            status="unknown",
            message="PF returned an unrecognized state",
            command_suggestions=(),
            manual_advice=("Inspect PF status and loaded anchors manually.",),
        )
    if state_lines[0].startswith("Status: Disabled"):
        return SSHDebugCheck(
            identifier="packet_filter",
            group="firewall",
            label="Packet Filter",
            status="ok",
            message="PF is disabled and cannot block the effective SSH ports",
            command_suggestions=(),
            manual_advice=(),
        )
    if not state_lines[0].startswith("Status: Enabled"):
        return SSHDebugCheck(
            identifier="packet_filter",
            group="firewall",
            label="Packet Filter",
            status="unknown",
            message=state_lines[0],
            command_suggestions=(),
            manual_advice=("Inspect PF status manually.",),
        )

    main_rules = run_argv(("/sbin/pfctl", "-s", "rules"))
    anchor_rules = run_argv(("/sbin/pfctl", "-a", "*", "-s", "rules"))
    if main_rules.returncode != 0 or anchor_rules.returncode != 0:
        failed = main_rules if main_rules.returncode != 0 else anchor_rules
        detail = failed.stderr or failed.stdout or failed.failure or "unknown command failure"
        return SSHDebugCheck(
            identifier="packet_filter",
            group="firewall",
            label="Packet Filter",
            status="unknown",
            message=f"PF is enabled but its rules could not be inspected: {detail}",
            command_suggestions=(),
            manual_advice=("Inspect the full PF ruleset including anchors.",),
        )
    active_rules = [
        line.strip()
        for output in (main_rules.stdout, anchor_rules.stdout)
        for line in output.splitlines()
        if line.strip()
    ]
    complex_rules = [
        rule
        for rule in active_rules
        if "anchor " in rule
        or "table " in rule
        or "<" in rule
        or any(token in rule for token in (" port {", " port >", " port <", " port !", " route-to ", " reply-to "))
        or (" port " in rule and re.search(r"\bport\s*=\s*\d+\b", rule) is None)
    ]
    if complex_rules:
        return SSHDebugCheck(
            identifier="packet_filter",
            group="firewall",
            label="Packet Filter",
            status="unknown",
            message="PF is enabled and uses anchors, tables, ranges, or other rules that cannot be proved safe for the SSH port",
            command_suggestions=(),
            manual_advice=("Evaluate the expanded PF ruleset and rule ordering manually.",),
        )
    for port in ports:
        exact_port = re.compile(rf"\bport\s*=\s*{port}(?:\s|$)")
        inbound_rules = [
            rule
            for rule in active_rules
            if not (re.search(r"\bout\b", rule) is not None and re.search(r"\bin\b", rule) is None)
        ]
        exact_passes = [
            rule
            for rule in inbound_rules
            if rule.startswith("pass ")
            and re.search(r"\bproto tcp\b", rule) is not None
            and exact_port.search(rule) is not None
            and re.search(r"\bfrom any\b", rule) is not None
            and rule.count(" port ") == 1
        ]
        exact_blocks = [
            rule
            for rule in inbound_rules
            if rule.startswith("block ")
            and (" proto " not in rule or re.search(r"\bproto tcp\b", rule) is not None)
            and exact_port.search(rule) is not None
        ]
        generic_blocks = [
            rule
            for rule in inbound_rules
            if rule.startswith("block ")
            and (" proto " not in rule or re.search(r"\bproto tcp\b", rule) is not None)
            and " port " not in rule
        ]
        if not exact_passes or exact_blocks or generic_blocks:
            return SSHDebugCheck(
                identifier="packet_filter",
                group="firewall",
                label="Packet Filter",
                status="unknown",
                message=f"PF is enabled and its rule ordering does not prove an unblocked exact pass for TCP port {port}",
                command_suggestions=(),
                manual_advice=("Evaluate PF anchors, quick rules, and ordering for the effective SSH port.",),
            )
    return SSHDebugCheck(
        identifier="packet_filter",
        group="firewall",
        label="Packet Filter",
        status="ok",
        message=f"PF has exact inbound TCP pass rules and no competing blocks for port(s) {', '.join(map(str, ports))}",
        command_suggestions=(),
        manual_advice=(),
    )


def check_application_firewall(ports: tuple[int, ...]) -> SSHDebugCheck:
    firewall_tool = "/usr/libexec/ApplicationFirewall/socketfilterfw"
    state = run_argv((firewall_tool, "--getglobalstate"))
    if state.returncode != 0:
        detail = state.stderr or state.stdout or state.failure or "unknown command failure"
        return SSHDebugCheck(
            identifier="application_firewall",
            group="firewall",
            label="Application firewall",
            status="unknown",
            message=f"Application firewall state could not be read: {detail}",
            command_suggestions=(),
            manual_advice=("Inspect the application firewall independently of PF.",),
        )
    state_match = re.search(r"\(State = (?P<state>[012])\)", state.stdout)
    if state_match is None:
        return SSHDebugCheck(
            identifier="application_firewall",
            group="firewall",
            label="Application firewall",
            status="unknown",
            message="Application firewall returned an unrecognized state",
            command_suggestions=(),
            manual_advice=("Inspect Firewall settings in System Settings.",),
        )
    if state_match.group("state") == "0":
        return SSHDebugCheck(
            identifier="application_firewall",
            group="firewall",
            label="Application firewall",
            status="ok",
            message="Application firewall is disabled",
            command_suggestions=(),
            manual_advice=(),
        )
    if state_match.group("state") == "2":
        return SSHDebugCheck(
            identifier="application_firewall",
            group="firewall",
            label="Application firewall",
            status="unknown",
            message="Application firewall is in block-all mode, where Remote Login admission cannot be proved",
            command_suggestions=(),
            manual_advice=("Inspect Block all incoming connections and the Remote Login system-service exemption.",),
        )
    firewall_subject = Path("/usr/libexec/sshd-keygen-wrapper")
    if not firewall_subject.is_file():
        return SSHDebugCheck(
            identifier="application_firewall",
            group="firewall",
            label="Application firewall",
            status="unknown",
            message=f"Remote Login firewall subject {firewall_subject} was not found",
            command_suggestions=(),
            manual_advice=("Inspect the ProgramArguments of the system SSH launch daemon.",),
        )
    blocked = run_argv((firewall_tool, "--getappblocked", str(firewall_subject)))
    if blocked.returncode != 0:
        detail = blocked.stderr or blocked.stdout or blocked.failure or "unknown command failure"
        return SSHDebugCheck(
            identifier="application_firewall",
            group="firewall",
            label="Application firewall",
            status="unknown",
            message=f"Remote Login application rule could not be read: {detail}",
            command_suggestions=(),
            manual_advice=("Inspect the sshd application rule in Firewall Options.",),
        )
    normalized = blocked.stdout.casefold()
    if "is not blocked" in normalized:
        return SSHDebugCheck(
            identifier="application_firewall",
            group="firewall",
            label="Application firewall",
            status="ok",
            message=f"Application firewall reports Remote Login unblocked for effective port(s) {', '.join(map(str, ports))}",
            command_suggestions=(),
            manual_advice=(),
        )
    if "is blocked" in normalized:
        return SSHDebugCheck(
            identifier="application_firewall",
            group="firewall",
            label="Application firewall",
            status="error",
            message="Application firewall reports Remote Login blocked",
            command_suggestions=(f"sudo {firewall_tool} --unblockapp {firewall_subject}",),
            manual_advice=("Confirm the intended application rule in Firewall Options before changing it.",),
        )
    return SSHDebugCheck(
        identifier="application_firewall",
        group="firewall",
        label="Application firewall",
        status="unknown",
        message=f"Application firewall did not provide conclusive Remote Login evidence: {blocked.stdout or 'empty output'}",
        command_suggestions=(),
        manual_advice=("Add or review sshd explicitly in Firewall Options.",),
    )
