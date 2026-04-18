from platform import system


def ssh_debug() -> dict[str, dict[str, str | bool]]:
    current_os = system()
    if current_os == "Linux":
        from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_linux import ssh_debug_linux

        return ssh_debug_linux()
    if current_os == "Darwin":
        from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_darwin import ssh_debug_darwin

        return ssh_debug_darwin()
    if current_os == "Windows":
        from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_windows import ssh_debug_windows

        return ssh_debug_windows()
    raise NotImplementedError(f"ssh_debug is not supported on {current_os}")


__all__ = ["ssh_debug"]
