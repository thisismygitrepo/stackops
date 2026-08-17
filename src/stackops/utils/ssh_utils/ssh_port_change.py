import re
import tempfile
from pathlib import Path

from stackops.utils.ssh_utils.ssh_port_apply import apply_validated_port_change
from stackops.utils.ssh_utils.ssh_port_commands import read_privileged_text
from stackops.utils.ssh_utils.ssh_port_firewall import preflight_host_firewall
from stackops.utils.ssh_utils.ssh_port_preflight import (
    assert_target_port_available,
    inspect_effective_sshd_config,
    prepare_port_change,
)
from stackops.utils.ssh_utils.ssh_port_selinux import preflight_selinux
from stackops.utils.ssh_utils.ssh_port_wsl_firewall import preflight_wsl_windows_firewall


SSHD_CONFIG_PATH = Path("/etc/ssh/sshd_config")


def _build_candidate_config(current_content: str, target_port: int) -> str:
    lines = current_content.splitlines(keepends=True)
    port_pattern = re.compile(r"^(?P<indent>[ \t]*)Port\s+\S+(?P<tail>[ \t]*(?:#.*)?)$", flags=re.IGNORECASE)
    match_pattern = re.compile(r"^[ \t]*Match(?:[ \t]|$)", flags=re.IGNORECASE)
    global_scope = True
    replacement_count = 0
    candidate_lines: list[str] = []
    for line in lines:
        line_content = line.rstrip("\r\n")
        newline = line[len(line_content) :]
        if global_scope and match_pattern.match(line_content) is not None:
            global_scope = False
        port_match = port_pattern.match(line_content) if global_scope else None
        if port_match is None:
            candidate_lines.append(line)
            continue
        candidate_lines.append(f"{port_match.group('indent')}Port {target_port}{port_match.group('tail')}{newline}")
        replacement_count += 1
    if replacement_count > 0:
        return "".join(candidate_lines)
    newline = "\r\n" if "\r\n" in current_content else "\n"
    return f"Port {target_port}{newline}{''.join(candidate_lines)}"


def change_ssh_port_transaction(target_port: int) -> None:
    if isinstance(target_port, bool) or target_port < 1 or target_port > 65535:
        raise ValueError(f"Invalid port number: {target_port}")
    print(f"🔎 Preflighting SSH port change to {target_port}...")
    plan = prepare_port_change(config_path=SSHD_CONFIG_PATH)
    if plan.effective_config.port == target_port:
        print(f"✅ SSH already resolves to and listens on port {target_port}; no changes were made.")
        return
    assert_target_port_available(plan=plan, target_port=target_port)
    current_content = read_privileged_text(path=plan.config_path, privilege_prefix=plan.privilege_prefix)
    candidate_content = _build_candidate_config(current_content=current_content, target_port=target_port)
    with tempfile.TemporaryDirectory(prefix="stackops-sshd-") as temporary_directory:
        candidate_path = Path(temporary_directory) / "sshd_config"
        candidate_path.write_text(candidate_content, encoding="utf-8")
        candidate_path.chmod(0o600)
        candidate_config = inspect_effective_sshd_config(
            sshd_path=plan.sshd_path,
            config_path=candidate_path,
            privilege_prefix=plan.privilege_prefix,
            config_label="Candidate SSH configuration",
        )
    if candidate_config.port != target_port:
        raise RuntimeError(
            f"Candidate SSH configuration resolves to port {candidate_config.port}, not {target_port}. "
            f"Update conflicting Port or ListenAddress directives in files included by {plan.config_path}, then retry."
        )
    preflight_host_firewall(plan=plan, target_port=target_port)
    preflight_wsl_windows_firewall(target_port=target_port)
    preflight_selinux(plan=plan, target_port=target_port)
    print(f"📝 Applying validated SSH port {target_port}...")
    apply_validated_port_change(
        plan=plan,
        original_content=current_content,
        candidate_content=candidate_content,
        target_port=target_port,
    )
    print(f"✅ SSH is active and listening on port {target_port}.")
