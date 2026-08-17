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
sudo systemsetup -setremotelogin on
sudo systemsetup -getremotelogin | grep -q "Remote Login: On"
echo "✅ Remote Login is enabled."
"""


def build_windows_ssh_server_install_script() -> str:
    return r'''$ErrorActionPreference = "Stop"
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Administrator privileges are required. Reopen PowerShell as Administrator and retry."
}

$capabilityName = "OpenSSH.Server~~~~0.0.1.0"
$capability = Get-WindowsCapability -Online -Name $capabilityName
if ($capability.State -ne "Installed") {
    Write-Host "Installing the Windows OpenSSH Server capability..." -ForegroundColor Cyan
    Add-WindowsCapability -Online -Name $capabilityName | Out-Null
}
$capability = Get-WindowsCapability -Online -Name $capabilityName
if ($capability.State -ne "Installed") {
    throw "Windows did not report $capabilityName as Installed; reboot if requested, then retry."
}

$service = Get-Service -Name "sshd" -ErrorAction Stop
Set-Service -Name "sshd" -StartupType Automatic
if ($service.Status -ne "Running") {
    Start-Service -Name "sshd"
}
$service = Get-Service -Name "sshd"
if ($service.Status -ne "Running") {
    throw "The sshd service did not reach the Running state."
}
$serviceConfiguration = Get-CimInstance -ClassName Win32_Service -Filter "Name='sshd'"
if ($null -eq $serviceConfiguration -or $serviceConfiguration.StartMode -ne "Auto") {
    throw "The sshd service startup mode is not Automatic."
}

$ruleName = "OpenSSH-Server-In-TCP"
$rules = @(Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue)
if ($rules.Count -eq 0) {
    New-NetFirewallRule `
        -Name $ruleName `
        -DisplayName "OpenSSH Server (sshd)" `
        -Enabled True `
        -Direction Inbound `
        -Protocol TCP `
        -Action Allow `
        -LocalPort 22 | Out-Null
} elseif ($rules.Count -eq 1) {
    $rule = $rules[0]
    Set-NetFirewallRule `
        -Name $ruleName `
        -Enabled True `
        -Direction Inbound `
        -Action Allow `
        -Profile Any | Out-Null
    $portFilters = @($rule | Get-NetFirewallPortFilter)
    if ($portFilters.Count -ne 1) {
        throw "Firewall rule $ruleName has an ambiguous port filter; remove it and retry."
    }
    $portFilters[0] | Set-NetFirewallPortFilter -Protocol TCP -LocalPort 22 -RemotePort Any | Out-Null
    $applicationFilters = @($rule | Get-NetFirewallApplicationFilter)
    if ($applicationFilters.Count -ne 1) {
        throw "Firewall rule $ruleName has an ambiguous application filter; remove it and retry."
    }
    $applicationFilters[0] | Set-NetFirewallApplicationFilter -Program Any | Out-Null
    $serviceFilters = @($rule | Get-NetFirewallServiceFilter)
    if ($serviceFilters.Count -ne 1) {
        throw "Firewall rule $ruleName has an ambiguous service filter; remove it and retry."
    }
    $serviceFilters[0] | Set-NetFirewallServiceFilter -Service Any | Out-Null
    $addressFilters = @($rule | Get-NetFirewallAddressFilter)
    if ($addressFilters.Count -ne 1) {
        throw "Firewall rule $ruleName has an ambiguous address filter; remove it and retry."
    }
    $addressFilters[0] | Set-NetFirewallAddressFilter -LocalAddress Any -RemoteAddress Any | Out-Null
    $interfaceFilters = @($rule | Get-NetFirewallInterfaceFilter)
    if ($interfaceFilters.Count -ne 1) {
        throw "Firewall rule $ruleName has an ambiguous interface filter; remove it and retry."
    }
    $interfaceFilters[0] | Set-NetFirewallInterfaceFilter -InterfaceAlias Any | Out-Null
    $interfaceTypeFilters = @($rule | Get-NetFirewallInterfaceTypeFilter)
    if ($interfaceTypeFilters.Count -ne 1) {
        throw "Firewall rule $ruleName has an ambiguous interface-type filter; remove it and retry."
    }
    $interfaceTypeFilters[0] | Set-NetFirewallInterfaceTypeFilter -InterfaceType Any | Out-Null
} else {
    throw "Multiple firewall rules named $ruleName exist; remove the duplicates and retry."
}

$verifiedRules = @(Get-NetFirewallRule -Name $ruleName -ErrorAction Stop)
$verifiedRule = if ($verifiedRules.Count -eq 1) { $verifiedRules[0] } else { $null }
$verifiedFilters = if ($null -ne $verifiedRule) { @($verifiedRule | Get-NetFirewallPortFilter) } else { @() }
$verifiedApplications = if ($null -ne $verifiedRule) { @($verifiedRule | Get-NetFirewallApplicationFilter) } else { @() }
$verifiedServices = if ($null -ne $verifiedRule) { @($verifiedRule | Get-NetFirewallServiceFilter) } else { @() }
$verifiedAddresses = if ($null -ne $verifiedRule) { @($verifiedRule | Get-NetFirewallAddressFilter) } else { @() }
$verifiedInterfaces = if ($null -ne $verifiedRule) { @($verifiedRule | Get-NetFirewallInterfaceFilter) } else { @() }
$verifiedInterfaceTypes = if ($null -ne $verifiedRule) { @($verifiedRule | Get-NetFirewallInterfaceTypeFilter) } else { @() }
$verifiedPorts = if ($verifiedFilters.Count -eq 1) { [string]::Join(",", @($verifiedFilters[0].LocalPort)) } else { "" }
$verifiedRemotePorts = if ($verifiedFilters.Count -eq 1) { [string]::Join(",", @($verifiedFilters[0].RemotePort)) } else { "" }
$verifiedLocalAddresses = if ($verifiedAddresses.Count -eq 1) { [string]::Join(",", @($verifiedAddresses[0].LocalAddress)) } else { "" }
$verifiedRemoteAddresses = if ($verifiedAddresses.Count -eq 1) { [string]::Join(",", @($verifiedAddresses[0].RemoteAddress)) } else { "" }
$verifiedInterfaceAliases = if ($verifiedInterfaces.Count -eq 1) { [string]::Join(",", @($verifiedInterfaces[0].InterfaceAlias)) } else { "" }
$verifiedInterfaceTypeValues = if ($verifiedInterfaceTypes.Count -eq 1) { [string]::Join(",", @($verifiedInterfaceTypes[0].InterfaceType)) } else { "" }
$ruleShapeIsExact = (
    $null -ne $verifiedRule -and
    $verifiedRule.Enabled.ToString() -eq "True" -and
    $verifiedRule.Direction.ToString() -eq "Inbound" -and
    $verifiedRule.Action.ToString() -eq "Allow" -and
    $verifiedRule.Profile.ToString() -eq "Any"
)
$portFilterIsExact = (
    $verifiedFilters.Count -eq 1 -and
    $verifiedFilters[0].Protocol.ToString() -eq "TCP" -and
    $verifiedPorts -eq "22" -and
    $verifiedRemotePorts -eq "Any"
)
$applicationFilterIsExact = (
    $verifiedApplications.Count -eq 1 -and
    $verifiedApplications[0].Program -eq "Any"
)
$serviceFilterIsExact = (
    $verifiedServices.Count -eq 1 -and
    $verifiedServices[0].Service -eq "Any"
)
$addressFilterIsExact = (
    $verifiedAddresses.Count -eq 1 -and
    $verifiedLocalAddresses -eq "Any" -and
    $verifiedRemoteAddresses -eq "Any"
)
$interfaceFiltersAreExact = (
    $verifiedInterfaces.Count -eq 1 -and
    $verifiedInterfaceAliases -eq "Any" -and
    $verifiedInterfaceTypes.Count -eq 1 -and
    $verifiedInterfaceTypeValues -eq "Any"
)
if (-not ($ruleShapeIsExact -and $portFilterIsExact -and $applicationFilterIsExact -and $serviceFilterIsExact -and $addressFilterIsExact -and $interfaceFiltersAreExact)) {
    throw "Firewall rule $ruleName is not an enabled inbound TCP allow rule for exactly local port 22."
}

Write-Host "OpenSSH Server is installed, automatic, running, and allowed on TCP port 22." -ForegroundColor Green
'''
