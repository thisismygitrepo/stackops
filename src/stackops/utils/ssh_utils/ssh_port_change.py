import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from stackops.utils.ssh_utils.ssh_port_commands import (
    PrivilegePrefix,
    privileged_path_exists,
    read_privileged_text,
    run_checked_command,
    write_privileged_text,
)
from stackops.utils.ssh_utils.ssh_port_preflight import (
    PortChangePlan,
    assert_active_ssh_listener,
    assert_active_socket_port,
    assert_target_port_available,
    inspect_effective_sshd_config,
    prepare_port_change,
)
from stackops.utils.ssh_utils.ssh_port_security import preflight_host_security


SSHD_CONFIG_PATH = Path("/etc/ssh/sshd_config")
SOCKET_OVERRIDE_FILENAME = "99-stackops-port.conf"


@dataclass(frozen=True, slots=True)
class FileBackup:
    path: Path
    existed: bool
    content: str
    parent_existed: bool


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


def _snapshot_file(path: Path, privilege_prefix: PrivilegePrefix) -> FileBackup:
    existed = privileged_path_exists(path=path, privilege_prefix=privilege_prefix)
    content = read_privileged_text(path=path, privilege_prefix=privilege_prefix) if existed else ""
    parent_existed = privileged_path_exists(path=path.parent, privilege_prefix=privilege_prefix)
    return FileBackup(path=path, existed=existed, content=content, parent_existed=parent_existed)


def _restore_file(backup: FileBackup, privilege_prefix: PrivilegePrefix) -> None:
    if backup.existed:
        write_privileged_text(path=backup.path, content=backup.content, privilege_prefix=privilege_prefix)
        return
    run_checked_command(
        command=(*privilege_prefix, "rm", "-f", "--", str(backup.path)),
        failure_message=f"Failed to remove newly created {backup.path}",
    )
    if not backup.parent_existed and privileged_path_exists(path=backup.path.parent, privilege_prefix=privilege_prefix):
        run_checked_command(
            command=(*privilege_prefix, "rmdir", "--", str(backup.path.parent)),
            failure_message=f"Failed to remove newly created directory {backup.path.parent}",
        )


def _socket_override_path(plan: PortChangePlan) -> Path | None:
    socket_name = plan.service_manager.socket_name
    if socket_name is None:
        return None
    return Path("/etc/systemd/system") / f"{socket_name}.d" / SOCKET_OVERRIDE_FILENAME


def _activate_ssh(plan: PortChangePlan) -> None:
    manager = plan.service_manager
    if manager.init_system in {"openrc", "sysv"}:
        service_command = "rc-service" if manager.init_system == "openrc" else "service"
        run_checked_command(
            command=(*plan.privilege_prefix, service_command, manager.service_name, "restart"),
            failure_message=f"Failed to restart {manager.init_system} service {manager.service_name}",
        )
        run_checked_command(
            command=(*plan.privilege_prefix, service_command, manager.service_name, "status"),
            failure_message=f"{manager.init_system} service {manager.service_name} is not active after restart",
        )
        return
    if manager.socket_name is not None:
        run_checked_command(
            command=(*plan.privilege_prefix, "systemctl", "daemon-reload"),
            failure_message="Failed to reload systemd after updating the SSH socket",
        )
        restart_units = (
            (manager.socket_name, manager.service_name)
            if manager.service_was_active
            else (manager.socket_name,)
        )
        run_checked_command(
            command=(*plan.privilege_prefix, "systemctl", "restart", *restart_units),
            failure_message=f"Failed to restart {' and '.join(restart_units)}",
        )
        run_checked_command(
            command=(*plan.privilege_prefix, "systemctl", "is-active", "--quiet", manager.socket_name),
            failure_message=f"Socket {manager.socket_name} is not active after restart",
        )
        if manager.service_was_active:
            run_checked_command(
                command=(*plan.privilege_prefix, "systemctl", "is-active", "--quiet", manager.service_name),
                failure_message=f"Service {manager.service_name} is not active after socket restart",
            )
        return
    run_checked_command(
        command=(*plan.privilege_prefix, "systemctl", "restart", manager.service_name),
        failure_message=f"Failed to restart {manager.service_name}",
    )
    run_checked_command(
        command=(*plan.privilege_prefix, "systemctl", "is-active", "--quiet", manager.service_name),
        failure_message=f"Service {manager.service_name} is not active after restart",
    )


def _rollback(
    plan: PortChangePlan,
    config_backup: FileBackup,
    socket_backup: FileBackup | None,
) -> tuple[str, ...]:
    rollback_errors: list[str] = []
    try:
        _restore_file(backup=config_backup, privilege_prefix=plan.privilege_prefix)
    except Exception as error:
        rollback_errors.append(str(error))
    if socket_backup is not None:
        try:
            _restore_file(backup=socket_backup, privilege_prefix=plan.privilege_prefix)
        except Exception as error:
            rollback_errors.append(str(error))
    try:
        _activate_ssh(plan=plan)
        assert_active_socket_port(plan=plan, expected_port=plan.effective_config.port)
        assert_active_ssh_listener(plan=plan, expected_port=plan.effective_config.port)
    except Exception as error:
        rollback_errors.append(str(error))
    return tuple(rollback_errors)


def _apply_candidate(
    plan: PortChangePlan,
    original_content: str,
    candidate_content: str,
    target_port: int,
) -> None:
    socket_override_path = _socket_override_path(plan=plan)
    config_backup = _snapshot_file(path=plan.config_path, privilege_prefix=plan.privilege_prefix)
    socket_backup = (
        _snapshot_file(path=socket_override_path, privilege_prefix=plan.privilege_prefix)
        if socket_override_path is not None
        else None
    )
    if config_backup.content != original_content:
        raise RuntimeError(f"{plan.config_path} changed during preflight; no files were modified. Review the new configuration, then retry.")
    assert_target_port_available(plan=plan, target_port=target_port)
    try:
        write_privileged_text(path=plan.config_path, content=candidate_content, privilege_prefix=plan.privilege_prefix)
        if socket_override_path is not None:
            run_checked_command(
                command=(*plan.privilege_prefix, "mkdir", "-p", str(socket_override_path.parent)),
                failure_message=f"Failed to create {socket_override_path.parent}",
            )
            socket_override_content = f"""[Socket]
ListenStream=
ListenStream={target_port}
"""
            write_privileged_text(
                path=socket_override_path,
                content=socket_override_content,
                privilege_prefix=plan.privilege_prefix,
            )
        live_config = inspect_effective_sshd_config(
            sshd_path=plan.sshd_path,
            config_path=plan.config_path,
            privilege_prefix=plan.privilege_prefix,
            config_label="Applied SSH configuration",
        )
        if live_config.port != target_port:
            raise RuntimeError(f"Applied SSH configuration resolves to port {live_config.port}, not requested port {target_port}.")
        _activate_ssh(plan=plan)
        assert_active_socket_port(plan=plan, expected_port=target_port)
        assert_active_ssh_listener(plan=plan, expected_port=target_port)
    except BaseException as error:
        rollback_errors = _rollback(plan=plan, config_backup=config_backup, socket_backup=socket_backup)
        if len(rollback_errors) > 0:
            rollback_detail = "; ".join(rollback_errors)
            raise RuntimeError(
                f"SSH port change failed ({error}), and rollback was incomplete: {rollback_detail}"
            ) from error
        if isinstance(error, Exception):
            raise RuntimeError(f"SSH port change failed; the previous configuration was restored: {error}") from error
        raise


def change_ssh_port_transaction(target_port: int) -> None:
    if target_port < 1 or target_port > 65535:
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
    preflight_host_security(plan=plan, target_port=target_port)
    print(f"📝 Applying validated SSH port {target_port}...")
    _apply_candidate(
        plan=plan,
        original_content=current_content,
        candidate_content=candidate_content,
        target_port=target_port,
    )
    print(f"✅ SSH is active and listening on port {target_port}.")
