import os
from pathlib import Path
from platform import system

from rich.console import Console

from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_common import (
    SSHDConnectionContext,
    assess_sshd_configuration,
)
from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_keys import KeyFileAssessment, assess_public_key_contents
from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_models import (
    SSHDebugCheck,
    SSHDebugResult,
    build_debug_result,
    render_debug_result,
)
from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_windows_acl import check_windows_key_acl
from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_windows_firewall import check_windows_firewall
from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_windows_network import check_windows_listeners
from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_windows_utils import (
    assess_windows_identity,
    check_windows_service,
    find_windows_sshd,
    resolve_windows_authorized_key_path,
    windows_sshd_config_path,
)


def ssh_debug_windows(connection_context: SSHDConnectionContext | None) -> SSHDebugResult:
    if system() != "Windows":
        raise NotImplementedError("ssh_debug_windows is only supported on Windows")

    checks: list[SSHDebugCheck] = []
    sshd_path = find_windows_sshd()
    if sshd_path is None:
        checks.append(
            SSHDebugCheck(
                identifier="installation",
                group="installation",
                label="OpenSSH server",
                status="error",
                message="No sshd.exe was found in the Windows OpenSSH locations or PATH",
                command_suggestions=(),
                manual_advice=("Install the Windows OpenSSH Server capability or a supported OpenSSH distribution.",),
            )
        )
    else:
        checks.append(
            SSHDebugCheck(
                identifier="installation",
                group="installation",
                label="OpenSSH server",
                status="ok",
                message=f"sshd.exe found at {sshd_path}",
                command_suggestions=(),
                manual_advice=(),
            )
        )

    checks.append(check_windows_service())
    identity_assessment = assess_windows_identity()
    current_name = identity_assessment.identity.name if identity_assessment.identity is not None else os.environ.get("USERNAME", "unknown")
    verified_connection_context = connection_context if identity_assessment.identity is not None else None
    configuration = assess_sshd_configuration(
        sshd_path=sshd_path,
        config_path=windows_sshd_config_path(),
        user_name=current_name,
        connection_context=verified_connection_context,
    )
    checks.extend(configuration.checks)
    checks.append(identity_assessment.check)
    authorized_keys_command_active = (
        configuration.connection_context_applied
        and configuration.settings is not None
        and any(
            command != "none"
            for command in configuration.settings.values.get("authorizedkeyscommand", ())
        )
    )

    key_path: Path | None = None
    if identity_assessment.identity is not None and configuration.connection_context_applied:
        key_path = resolve_windows_authorized_key_path(
            settings=configuration.settings,
            identity=identity_assessment.identity,
            home_directory=Path.home(),
        )
    if key_path is None:
        checks.extend(
            (
                SSHDebugCheck(
                    identifier="authorized_keys",
                    group="permissions",
                    label="Authorized keys",
                    status="unknown",
                    message="The effective authorized-keys file could not be selected",
                    command_suggestions=(),
                    manual_advice=("Resolve identity membership and effective AuthorizedKeysFile settings.",),
                ),
                SSHDebugCheck(
                    identifier="authorized_keys_acl",
                    group="permissions",
                    label="Authorized-keys ACL",
                    status="unknown",
                    message="No effective authorized-keys path is available for ACL inspection",
                    command_suggestions=(),
                    manual_advice=("Resolve the effective key path before inspecting its owner and DACL by SID.",),
                ),
            )
        )
    else:
        key_contents = assess_public_key_contents(key_path)
        if key_contents.status == "error" and authorized_keys_command_active:
            key_contents = KeyFileAssessment(
                status="unknown",
                message=f"{key_contents.message}; AuthorizedKeysCommand may supply keys independently",
            )
        checks.append(
            SSHDebugCheck(
                identifier="authorized_keys",
                group="permissions",
                label="Authorized keys",
                status=key_contents.status,
                message=key_contents.message,
                command_suggestions=(),
                manual_advice=("Add only valid OpenSSH public-key records to the effective file.",)
                if key_contents.status != "ok"
                else (),
            )
        )
        if identity_assessment.identity is None:
            checks.append(
                SSHDebugCheck(
                    identifier="authorized_keys_acl",
                    group="permissions",
                    label="Authorized-keys ACL",
                    status="unknown",
                    message="Current user SID evidence is unavailable",
                    command_suggestions=(),
                    manual_advice=("Resolve the current identity before interpreting ACL entries.",),
                )
            )
        elif not key_path.is_file():
            checks.append(
                SSHDebugCheck(
                    identifier="authorized_keys_acl",
                    group="permissions",
                    label="Authorized-keys ACL",
                    status="unknown" if authorized_keys_command_active else "error",
                    message=(
                        f"{key_path} does not exist as a regular file; AuthorizedKeysCommand may supply keys"
                        if authorized_keys_command_active
                        else f"{key_path} does not exist as a regular file"
                    ),
                    command_suggestions=(),
                    manual_advice=("Create the corresponding key file and then restrict its ACL by SID.",),
                )
            )
        else:
            checks.append(check_windows_key_acl(path=key_path, identity=identity_assessment.identity))

    if configuration.ports is None or sshd_path is None:
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
                    label="Windows Firewall",
                    status="unknown",
                    message="The exact effective SSH port or sshd executable path is unavailable",
                    command_suggestions=(),
                    manual_advice=("Resolve the sshd -T probe before evaluating firewall rules.",),
                ),
            )
        )
    else:
        checks.append(check_windows_listeners(configuration.ports))
        checks.append(check_windows_firewall(ports=configuration.ports, sshd_path=sshd_path))

    result = build_debug_result(checks)
    render_debug_result(result=result, console=Console())
    return result


if __name__ == "__main__":
    direct_result = ssh_debug_windows(connection_context=None)
    raise SystemExit(0 if direct_result.summary.ready else 1)
