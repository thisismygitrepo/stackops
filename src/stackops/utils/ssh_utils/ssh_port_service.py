import os
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from stackops.utils.ssh_utils.ssh_port_commands import (
    PrivilegePrefix,
    require_trusted_system_command,
    resolve_trusted_system_command,
    run_command,
)


type InitSystem = Literal["openrc", "systemd", "sysv"]


@dataclass(frozen=True, slots=True)
class ServiceManager:
    init_system: InitSystem
    service_name: str
    socket_name: str | None
    service_was_active: bool


def _systemd_unit_properties(unit_name: str, privilege_prefix: PrivilegePrefix) -> dict[str, str]:
    systemctl_path = require_trusted_system_command(command_name="systemctl")
    result = run_command(
        (
            *privilege_prefix,
            systemctl_path,
            "show",
            unit_name,
            "--property=Id",
            "--property=LoadState",
            "--property=ActiveState",
            "--property=Triggers",
        )
    )
    if result.returncode != 0:
        return {}
    properties: dict[str, str] = {}
    for line in result.stdout.splitlines():
        key, separator, value = line.partition("=")
        if separator != "":
            properties[key] = value
    return properties


def _resolve_systemd_manager(privilege_prefix: PrivilegePrefix) -> ServiceManager | None:
    systemctl_path = resolve_trusted_system_command(command_name="systemctl")
    if systemctl_path is None:
        return None
    system_state = run_command((str(systemctl_path), "is-system-running"))
    if system_state.stdout.strip() not in {"running", "degraded"}:
        return None

    active_sockets: dict[str, dict[str, str]] = {}
    for candidate in ("ssh.socket", "sshd.socket"):
        properties = _systemd_unit_properties(unit_name=candidate, privilege_prefix=privilege_prefix)
        if properties.get("LoadState") == "loaded" and properties.get("ActiveState") == "active":
            active_sockets[properties["Id"]] = properties
    if len(active_sockets) > 1:
        names = ", ".join(sorted(active_sockets))
        raise RuntimeError(f"Multiple active SSH socket units are ambiguous ({names}); leave exactly one active, then retry.")

    loaded_services: dict[str, dict[str, str]] = {}
    for candidate in ("ssh.service", "sshd.service"):
        properties = _systemd_unit_properties(unit_name=candidate, privilege_prefix=privilege_prefix)
        if properties.get("LoadState") == "loaded":
            loaded_services[properties["Id"]] = properties

    if len(active_sockets) == 1:
        socket_name, socket_properties = next(iter(active_sockets.items()))
        triggered_services = tuple(
            trigger
            for trigger in socket_properties.get("Triggers", "").split()
            if trigger in loaded_services and trigger in {"ssh.service", "sshd.service"}
        )
        if len(triggered_services) != 1:
            raise RuntimeError(
                f"Active socket {socket_name} does not trigger exactly one loaded ssh/sshd service; correct the unit relationship, then retry."
            )
        unexpected_active_services = tuple(
            service_name
            for service_name, properties in loaded_services.items()
            if properties.get("ActiveState") == "active" and service_name != triggered_services[0]
        )
        if len(unexpected_active_services) > 0:
            names = ", ".join(sorted(unexpected_active_services))
            raise RuntimeError(
                f"Active socket {socket_name} is accompanied by another active SSH service ({names}); stop the unrelated service, then retry."
            )
        service_was_active = loaded_services[triggered_services[0]].get("ActiveState") == "active"
        return ServiceManager(
            init_system="systemd",
            service_name=triggered_services[0],
            socket_name=socket_name,
            service_was_active=service_was_active,
        )

    active_services = tuple(
        service_name for service_name, properties in loaded_services.items() if properties.get("ActiveState") == "active"
    )
    if len(active_services) != 1:
        detected = ", ".join(sorted(active_services)) or "none"
        raise RuntimeError(
            f"Expected exactly one active systemd SSH service named ssh or sshd; found {detected}. Start the intended service, then retry."
        )
    return ServiceManager(
        init_system="systemd",
        service_name=active_services[0],
        socket_name=None,
        service_was_active=True,
    )


def _resolve_openrc_manager(privilege_prefix: PrivilegePrefix) -> ServiceManager | None:
    rc_service_path = resolve_trusted_system_command(command_name="rc-service")
    if rc_service_path is None:
        return None
    active_services = tuple(
        service_name
        for service_name in ("ssh", "sshd")
        if run_command((*privilege_prefix, str(rc_service_path), service_name, "status")).returncode == 0
    )
    if len(active_services) != 1:
        detected = ", ".join(active_services) or "none"
        raise RuntimeError(
            f"Expected exactly one active OpenRC SSH service named ssh or sshd; found {detected}. Start the intended service, then retry."
        )
    return ServiceManager(
        init_system="openrc",
        service_name=active_services[0],
        socket_name=None,
        service_was_active=True,
    )


def _resolve_sysv_manager(privilege_prefix: PrivilegePrefix) -> ServiceManager | None:
    service_path = resolve_trusted_system_command(command_name="service")
    if service_path is None:
        return None
    installed_services = tuple(
        service_name for service_name in ("ssh", "sshd") if Path("/etc/init.d").joinpath(service_name).is_file()
    )
    if len(installed_services) == 0:
        return None
    active_services = tuple(
        service_name
        for service_name in installed_services
        if run_command((*privilege_prefix, str(service_path), service_name, "status")).returncode == 0
    )
    if len(active_services) != 1:
        detected = ", ".join(active_services) or "none"
        raise RuntimeError(
            f"Expected exactly one active SysV SSH service named ssh or sshd; found {detected}. Start the intended service, then retry."
        )
    return ServiceManager(
        init_system="sysv",
        service_name=active_services[0],
        socket_name=None,
        service_was_active=True,
    )


def resolve_service_manager(privilege_prefix: PrivilegePrefix) -> ServiceManager:
    systemd_manager = _resolve_systemd_manager(privilege_prefix=privilege_prefix)
    if systemd_manager is not None:
        return systemd_manager
    openrc_manager = _resolve_openrc_manager(privilege_prefix=privilege_prefix)
    if openrc_manager is not None:
        return openrc_manager
    sysv_manager = _resolve_sysv_manager(privilege_prefix=privilege_prefix)
    if sysv_manager is not None:
        return sysv_manager
    is_wsl = os.environ.get("WSL_DISTRO_NAME") is not None or "microsoft" in platform.release().lower()
    if is_wsl:
        raise RuntimeError(
            "WSL is running without systemd or OpenRC, so a supervised SSH restart cannot be verified. "
            "Enable systemd in WSL, start ssh.service, then retry."
        )
    raise RuntimeError("Unsupported init system; change-port requires an active ssh/sshd service managed by systemd, OpenRC, or SysV.")
