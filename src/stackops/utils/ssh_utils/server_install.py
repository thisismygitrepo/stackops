import shlex

from stackops.utils.installer_utils.linux_package_manager import (
    LinuxDistribution,
    build_package_install_command,
    get_openssh_server_package,
    get_openssh_service_name,
)


def build_linux_ssh_server_install_script(distribution: LinuxDistribution) -> str:
    package_manager = distribution.package_manager
    openssh_package = get_openssh_server_package(package_manager)
    service_name = get_openssh_service_name(package_manager)
    install_command = shlex.join(build_package_install_command(package_manager, (openssh_package,)))
    activation_commands = (
        'if command -v systemctl >/dev/null 2>&1 && [ -d /run/systemd/system ]; then',
        f"    run_as_root systemctl enable --now {service_name}.service",
        f"    run_as_root systemctl is-enabled --quiet {service_name}.service",
        f"    run_as_root systemctl is-active --quiet {service_name}.service",
        'elif command -v rc-service >/dev/null 2>&1 && command -v rc-update >/dev/null 2>&1; then',
        f"    run_as_root rc-update add {service_name} default",
        f"    run_as_root rc-service {service_name} start",
        f"    run_as_root rc-service {service_name} status",
        'elif command -v service >/dev/null 2>&1 && command -v update-rc.d >/dev/null 2>&1; then',
        f"    run_as_root update-rc.d {service_name} defaults",
        f"    run_as_root update-rc.d {service_name} enable",
        f"    run_as_root service {service_name} start",
        f"    run_as_root service {service_name} status",
        'elif command -v service >/dev/null 2>&1 && command -v chkconfig >/dev/null 2>&1; then',
        f"    run_as_root chkconfig {service_name} on",
        f"    run_as_root service {service_name} start",
        f"    run_as_root service {service_name} status",
        "else",
        '    echo "No supported systemd, OpenRC, or SysV service manager is active." >&2',
        "    exit 1",
        "fi",
    )
    return "\n".join(
        (
            "#!/bin/sh",
            "set -eu",
            "run_as_root() {",
            '    if [ "$(id -u)" -eq 0 ]; then',
            '        "$@"',
            "    else",
            '        command -v sudo >/dev/null || { echo "Root privileges are required; install sudo or run as root." >&2; exit 1; }',
            '        sudo "$@"',
            "    fi",
            "}",
            f"run_as_root {install_command}",
            *activation_commands,
            f'echo "✅ OpenSSH server installed and {service_name} is active."',
            "",
        )
    )


def build_macos_ssh_server_install_script() -> str:
    return """#!/bin/sh
set -eu
LC_ALL=C
export LC_ALL
if ! /usr/bin/sudo /usr/sbin/systemsetup -getremotelogin | /usr/bin/grep -Fqx "Remote Login: On"; then
    if ! /usr/bin/sudo /usr/sbin/systemsetup -setremotelogin on; then
        echo "Grant Full Disk Access to the parent terminal or application, then retry." >&2
        exit 1
    fi
fi
/usr/bin/sudo /usr/sbin/systemsetup -getremotelogin | /usr/bin/grep -Fqx "Remote Login: On"
echo "✅ Remote Login is enabled."
"""
