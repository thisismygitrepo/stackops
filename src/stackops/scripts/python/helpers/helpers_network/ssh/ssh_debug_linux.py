import os
import socket
from pathlib import Path
from platform import system

from rich.console import Console

from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_common import assess_sshd_configuration
from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_keys import (
    assess_posix_authorized_keys,
    resolve_posix_authorized_key_paths,
)
from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_linux_firewall import check_linux_firewall
from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_linux_utils import (
    check_linux_listeners,
    check_linux_service,
    find_linux_sshd,
)
from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_models import (
    SSHDebugCheck,
    SSHDebugResult,
    build_debug_result,
    render_debug_result,
)


def ssh_debug_linux() -> SSHDebugResult:
    current_os = system()
    if current_os == "Darwin":
        from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_darwin import ssh_debug_darwin

        return ssh_debug_darwin()
    if current_os != "Linux":
        raise NotImplementedError(f"ssh_debug_linux is only supported on Linux and macOS, not {current_os}")

    import pwd

    checks: list[SSHDebugCheck] = []
    sshd_path = find_linux_sshd()
    if sshd_path is None:
        checks.append(
            SSHDebugCheck(
                identifier="installation",
                group="installation",
                label="OpenSSH server",
                status="error",
                message="No executable sshd binary was found in standard paths or PATH",
                command_suggestions=(),
                manual_advice=("Install the OpenSSH server package provided by this Linux distribution.",),
            )
        )
    else:
        checks.append(
            SSHDebugCheck(
                identifier="installation",
                group="installation",
                label="OpenSSH server",
                status="ok",
                message=f"Executable sshd found at {sshd_path}",
                command_suggestions=(),
                manual_advice=(),
            )
        )

    checks.append(check_linux_service())
    current_identity = pwd.getpwuid(os.getuid())
    home_directory = Path(current_identity.pw_dir)
    configuration = assess_sshd_configuration(
        sshd_path=sshd_path,
        config_path=None,
        user_name=current_identity.pw_name,
        host_name=socket.gethostname(),
    )
    checks.extend(configuration.checks)

    if configuration.settings is None:
        checks.append(
            SSHDebugCheck(
                identifier="authorized_keys",
                group="permissions",
                label="Authorized keys",
                status="unknown",
                message="Effective AuthorizedKeysFile paths are unavailable because sshd -T failed",
                command_suggestions=(),
                manual_advice=("Resolve the effective-configuration probe before inspecting key-file permissions.",),
            )
        )
    else:
        key_paths = resolve_posix_authorized_key_paths(
            settings=configuration.settings,
            home_directory=home_directory,
            user_name=current_identity.pw_name,
        )
        key_assessment = assess_posix_authorized_keys(
            paths=key_paths,
            home_directory=home_directory,
            user_id=os.getuid(),
            authorized_keys_command=configuration.settings.values.get("authorizedkeyscommand", ()),
        )
        checks.append(
            SSHDebugCheck(
                identifier="authorized_keys",
                group="permissions",
                label="Authorized keys",
                status=key_assessment.status,
                message=key_assessment.message,
                command_suggestions=(),
                manual_advice=(
                    "Ensure at least one effective key file is owned by the user or root, is not group/other-writable, and contains valid public keys.",
                )
                if key_assessment.status != "ok"
                else (),
            )
        )

    if configuration.ports is None:
        checks.extend(
            (
                SSHDebugCheck(
                    identifier="ssh_listener",
                    group="network",
                    label="TCP listener",
                    status="unknown",
                    message="The exact effective SSH port is unavailable",
                    command_suggestions=(),
                    manual_advice=("Resolve the sshd -T probe before inspecting listeners.",),
                ),
                SSHDebugCheck(
                    identifier="firewall",
                    group="firewall",
                    label="Inbound firewall",
                    status="unknown",
                    message="The exact effective SSH port is unavailable",
                    command_suggestions=(),
                    manual_advice=("Resolve the sshd -T probe before inspecting firewall policy.",),
                ),
            )
        )
    else:
        checks.append(check_linux_listeners(configuration.ports))
        checks.append(check_linux_firewall(configuration.ports))

    result = build_debug_result(checks)
    render_debug_result(result=result, console=Console())
    return result


if __name__ == "__main__":
    ssh_debug_linux()
