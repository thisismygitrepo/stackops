from dataclasses import dataclass
from pathlib import Path

from stackops.utils.ssh_utils.ssh_port_activation import activate_ssh
from stackops.utils.ssh_utils.ssh_port_commands import (
    PrivilegePrefix,
    privileged_path_exists,
    read_privileged_text,
    require_trusted_system_command,
    run_checked_command,
    write_privileged_text,
)
from stackops.utils.ssh_utils.ssh_port_preflight import (
    PortChangePlan,
    active_socket_streams,
    assert_active_ssh_listener,
    assert_active_socket_port,
    assert_target_port_available,
    inspect_effective_sshd_config,
)


SOCKET_OVERRIDE_FILENAME = "99-stackops-port.conf"


@dataclass(frozen=True, slots=True)
class FileBackup:
    path: Path
    existed: bool
    content: str
    parent_existed: bool


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
        command=(
            *privilege_prefix,
            require_trusted_system_command(command_name="rm"),
            "-f",
            "--",
            str(backup.path),
        ),
        failure_message=f"Failed to remove newly created {backup.path}",
    )
    if not backup.parent_existed and privileged_path_exists(path=backup.path.parent, privilege_prefix=privilege_prefix):
        run_checked_command(
            command=(
                *privilege_prefix,
                require_trusted_system_command(command_name="rmdir"),
                "--",
                str(backup.path.parent),
            ),
            failure_message=f"Failed to remove newly created directory {backup.path.parent}",
        )


def _socket_override_path(plan: PortChangePlan) -> Path | None:
    socket_name = plan.service_manager.socket_name
    if socket_name is None:
        return None
    return Path("/etc/systemd/system") / f"{socket_name}.d" / SOCKET_OVERRIDE_FILENAME


def _replace_socket_stream_port(stream: str, target_port: int) -> str:
    if stream.isdecimal():
        return str(target_port)
    address, separator, current_port = stream.rpartition(":")
    if separator == ":" and address != "" and current_port.isdecimal():
        return f"{address}:{target_port}"
    raise RuntimeError(f"Cannot safely preserve systemd SSH socket endpoint {stream!r} while changing its port.")


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
        activate_ssh(plan=plan)
        assert_active_socket_port(plan=plan, expected_port=plan.effective_config.port)
        assert_active_ssh_listener(plan=plan, expected_port=plan.effective_config.port)
    except Exception as error:
        rollback_errors.append(str(error))
    return tuple(rollback_errors)


def apply_validated_port_change(
    plan: PortChangePlan,
    original_content: str,
    candidate_content: str,
    target_port: int,
) -> None:
    socket_override_path = _socket_override_path(plan=plan)
    preserved_socket_streams = active_socket_streams(plan=plan) if socket_override_path is not None else ()
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
                command=(
                    *plan.privilege_prefix,
                    require_trusted_system_command(command_name="mkdir"),
                    "-p",
                    str(socket_override_path.parent),
                ),
                failure_message=f"Failed to create {socket_override_path.parent}",
            )
            target_socket_streams = tuple(
                _replace_socket_stream_port(stream=stream, target_port=target_port)
                for stream in preserved_socket_streams
            )
            socket_override_content = "\n".join(
                ("[Socket]", "ListenStream=", *(f"ListenStream={stream}" for stream in target_socket_streams), "")
            )
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
        activate_ssh(plan=plan)
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
