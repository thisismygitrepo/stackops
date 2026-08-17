import os
from pathlib import Path
from platform import system

from rich.console import Console

from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_common import (
    SSHDConnectionContext,
    assess_sshd_configuration,
)
from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_darwin_firewall import (
    check_application_firewall,
    check_packet_filter,
)
from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_darwin_network import check_darwin_listeners
from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_darwin_utils import (
    check_remote_login_service,
    find_darwin_sshd,
)
from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_keys import (
    assess_posix_authorized_keys,
    resolve_posix_authorized_key_paths,
)
from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_models import (
    SSHDebugCheck,
    SSHDebugResult,
    build_debug_result,
    render_debug_result,
)


def ssh_debug_darwin(connection_context: SSHDConnectionContext | None) -> SSHDebugResult:
    if system() != "Darwin":
        raise NotImplementedError("ssh_debug_darwin is only supported on macOS")

    import pwd

    checks: list[SSHDebugCheck] = []
    sshd_path = find_darwin_sshd()
    if sshd_path is None:
        checks.append(
            SSHDebugCheck(
                identifier="installation",
                group="installation",
                label="OpenSSH server",
                status="error",
                message="No executable sshd binary was found in standard paths or PATH",
                command_suggestions=(),
                manual_advice=("Restore or install an OpenSSH server before enabling Remote Login.",),
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

    checks.append(check_remote_login_service())
    current_identity = pwd.getpwuid(os.getuid())
    home_directory = Path(current_identity.pw_dir)
    configuration = assess_sshd_configuration(
        sshd_path=sshd_path,
        config_path=None,
        user_name=current_identity.pw_name,
        connection_context=connection_context,
    )
    checks.extend(configuration.checks)

    if not configuration.connection_context_applied or configuration.settings is None:
        context_detail = (
            "No explicit connection context was supplied"
            if connection_context is None
            else "The supplied connection context could not be applied by sshd -T"
        )
        checks.append(
            SSHDebugCheck(
                identifier="authorized_keys",
                group="permissions",
                label="Authorized keys",
                status="unknown",
                message=f"{context_detail}; Match-dependent AuthorizedKeysFile paths were not inspected",
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
                    "Ensure an effective key file is owned by the user or root, is not group/other-writable, and contains valid public keys.",
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
                    identifier="packet_filter",
                    group="firewall",
                    label="Packet Filter",
                    status="unknown",
                    message="The exact effective SSH port is unavailable",
                    command_suggestions=(),
                    manual_advice=("Resolve the sshd -T probe before evaluating PF rules.",),
                ),
                SSHDebugCheck(
                    identifier="application_firewall",
                    group="firewall",
                    label="Application firewall",
                    status="unknown",
                    message="The exact effective SSH port is unavailable",
                    command_suggestions=(),
                    manual_advice=("Resolve the sshd -T probe before evaluating sshd firewall access.",),
                ),
            )
        )
    else:
        checks.append(check_darwin_listeners(configuration.ports))
        checks.append(check_packet_filter(configuration.ports))
        checks.append(check_application_firewall(ports=configuration.ports))

    result = build_debug_result(checks)
    render_debug_result(result=result, console=Console())
    return result


if __name__ == "__main__":
    direct_result = ssh_debug_darwin(connection_context=None)
    raise SystemExit(0 if direct_result.summary.ready else 1)
