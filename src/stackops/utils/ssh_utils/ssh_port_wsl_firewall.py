import os
import platform
import shutil

from stackops.utils.ssh_utils.ssh_port_commands import run_command


def preflight_wsl_windows_firewall(target_port: int) -> None:
    is_wsl = os.environ.get("WSL_DISTRO_NAME") is not None or "microsoft" in platform.release().lower()
    if not is_wsl:
        return
    powershell_path = shutil.which("powershell.exe")
    firewall_command = (
        f"New-NetFirewallRule -DisplayName 'StackOps SSH {target_port}' -Direction Inbound "
        f"-Protocol TCP -LocalPort {target_port} -Action Allow"
    )
    if powershell_path is None:
        raise RuntimeError(
            "WSL cannot verify Windows Firewall because powershell.exe is unavailable. "
            f"From elevated PowerShell run `{firewall_command}`, then retry."
        )
    script = rf'''
$ErrorActionPreference = "Stop"
$activeProfiles = @(Get-NetFirewallProfile | Where-Object Enabled)
if ($activeProfiles.Count -eq 0) {{ exit 0 }}
$blockingFilters = @(
    Get-NetFirewallRule -PolicyStore ActiveStore -Enabled True -Direction Inbound -Action Block |
        Get-NetFirewallPortFilter |
        Where-Object {{
            $_.Protocol.ToString() -eq "TCP" -and
            ((@($_.LocalPort) -contains "{target_port}") -or (@($_.LocalPort) -contains "Any"))
        }}
)
if ($blockingFilters.Count -gt 0) {{ exit 4 }}
$matchingFilters = @(
    Get-NetFirewallRule -PolicyStore ActiveStore -Enabled True -Direction Inbound -Action Allow |
        Get-NetFirewallPortFilter |
        Where-Object {{
            $_.Protocol.ToString() -eq "TCP" -and
            ((@($_.LocalPort) -contains "{target_port}") -or (@($_.LocalPort) -contains "Any"))
        }}
)
if ($matchingFilters.Count -gt 0) {{ exit 0 }}
exit 3
'''
    result = run_command((powershell_path, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", script))
    if result.returncode == 0:
        return
    if result.returncode == 3:
        raise RuntimeError(
            f"Active Windows Firewall does not explicitly allow inbound TCP port {target_port} for WSL. "
            f"From elevated PowerShell run `{firewall_command}`, then retry."
        )
    if result.returncode == 4:
        raise RuntimeError(
            f"Active Windows Firewall has an inbound block rule covering TCP port {target_port}. "
            "From elevated PowerShell inspect `Get-NetFirewallRule -Enabled True -Direction Inbound -Action Block`, "
            "remove or narrow the applicable block rule, then retry."
        )
    error_output = result.stderr.strip() or result.stdout.strip()
    raise RuntimeError(
        f"Unable to verify Windows Firewall for WSL: {error_output}. Run the check from elevated PowerShell, then retry."
    )
