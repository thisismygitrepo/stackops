from stackops.utils.ssh_utils.ssh_port_commands import require_trusted_system_command, run_checked_command
from stackops.utils.ssh_utils.ssh_port_preflight import PortChangePlan


def activate_ssh(plan: PortChangePlan) -> None:
    manager = plan.service_manager
    if manager.init_system in {"openrc", "sysv"}:
        service_command = require_trusted_system_command(
            command_name="rc-service" if manager.init_system == "openrc" else "service"
        )
        run_checked_command(
            command=(*plan.privilege_prefix, service_command, manager.service_name, "restart"),
            failure_message=f"Failed to restart {manager.init_system} service {manager.service_name}",
        )
        run_checked_command(
            command=(*plan.privilege_prefix, service_command, manager.service_name, "status"),
            failure_message=f"{manager.init_system} service {manager.service_name} is not active after restart",
        )
        return

    systemctl_path = require_trusted_system_command(command_name="systemctl")
    if manager.socket_name is not None:
        run_checked_command(
            command=(*plan.privilege_prefix, systemctl_path, "daemon-reload"),
            failure_message="Failed to reload systemd after updating the SSH socket",
        )
        restart_units = (
            (manager.socket_name, manager.service_name)
            if manager.service_was_active
            else (manager.socket_name,)
        )
        run_checked_command(
            command=(*plan.privilege_prefix, systemctl_path, "restart", *restart_units),
            failure_message=f"Failed to restart {' and '.join(restart_units)}",
        )
        run_checked_command(
            command=(*plan.privilege_prefix, systemctl_path, "is-active", "--quiet", manager.socket_name),
            failure_message=f"Socket {manager.socket_name} is not active after restart",
        )
        if manager.service_was_active:
            run_checked_command(
                command=(*plan.privilege_prefix, systemctl_path, "is-active", "--quiet", manager.service_name),
                failure_message=f"Service {manager.service_name} is not active after socket restart",
            )
        return

    run_checked_command(
        command=(*plan.privilege_prefix, systemctl_path, "restart", manager.service_name),
        failure_message=f"Failed to restart {manager.service_name}",
    )
    run_checked_command(
        command=(*plan.privilege_prefix, systemctl_path, "is-active", "--quiet", manager.service_name),
        failure_message=f"Service {manager.service_name} is not active after restart",
    )
