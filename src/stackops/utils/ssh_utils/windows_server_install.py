def build_windows_ssh_server_install_script() -> str:
    return r"""$ErrorActionPreference = "Stop"
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Administrator privileges are required. Reopen PowerShell as Administrator and retry."
}

$capabilityName = "OpenSSH.Server~~~~0.0.1.0"
$capability = Get-WindowsCapability -Online -Name $capabilityName
if ($capability.State -ne "Installed") {
    Write-Host "Installing the Windows OpenSSH Server capability..." -ForegroundColor Cyan
    $capabilityInstall = Add-WindowsCapability -Online -Name $capabilityName
    if ($capabilityInstall.RestartNeeded) {
        throw "Windows installed $capabilityName and requires a reboot; reboot, then retry."
    }
}
$capability = Get-WindowsCapability -Online -Name $capabilityName
if ($capability.State -ne "Installed") {
    throw "Windows did not report $capabilityName as Installed; reboot if requested, then retry."
}

$service = Get-Service -Name "sshd" -ErrorAction Stop
Set-Service -Name "sshd" -StartupType Automatic
if ($service.Status -eq "Stopped") {
    Start-Service -InputObject $service
}
if ($service.Status -ne "Running") {
    $service.WaitForStatus(
        [System.ServiceProcess.ServiceControllerStatus]::Running,
        [TimeSpan]::FromSeconds(30)
    )
}
$service.Refresh()
if ($service.Status -ne "Running") {
    throw "The sshd service did not reach the Running state."
}
$serviceConfiguration = Get-CimInstance -ClassName Win32_Service -Filter "Name='sshd'"
if ($null -eq $serviceConfiguration -or $serviceConfiguration.StartMode -ne "Auto") {
    throw "The sshd service startup mode is not Automatic."
}

$ruleName = "OpenSSH-Server-In-TCP"
$persistentRules = @(
    Get-NetFirewallRule -PolicyStore PersistentStore -Name $ruleName -ErrorAction SilentlyContinue
)
if ($persistentRules.Count -gt 1) {
    throw "Multiple persistent firewall rules named $ruleName exist; remove the duplicates and retry."
}
if ($persistentRules.Count -eq 1) {
    $persistentRules[0] | Remove-NetFirewallRule
}
New-NetFirewallRule `
    -PolicyStore PersistentStore `
    -Name $ruleName `
    -DisplayName "OpenSSH Server (sshd)" `
    -Enabled True `
    -Profile Any `
    -Direction Inbound `
    -Action Allow `
    -EdgeTraversalPolicy Block `
    -LooseSourceMapping $false `
    -LocalOnlyMapping $false `
    -LocalAddress Any `
    -RemoteAddress Any `
    -Protocol TCP `
    -LocalPort 22 `
    -RemotePort Any `
    -IcmpType Any `
    -DynamicTarget Any `
    -Program Any `
    -Service Any `
    -InterfaceAlias Any `
    -InterfaceType Any `
    -Authentication NotRequired `
    -Encryption NotRequired `
    -OverrideBlockRules $false | Out-Null

function Get-SingleFirewallFilter {
    param([object[]]$Filters, [string]$Label)
    if ($Filters.Count -ne 1) {
        throw "Effective firewall rule $ruleName has $($Filters.Count) $Label filters; expected exactly one."
    }
    return $Filters[0]
}

function ConvertTo-JoinedString {
    param([object]$Value)
    return [string]::Join(",", @($Value))
}

$effectiveRules = @(
    Get-NetFirewallRule -PolicyStore ActiveStore -Name $ruleName -ErrorAction Stop
)
if ($effectiveRules.Count -ne 1) {
    throw "Effective firewall policy has $($effectiveRules.Count) rules named $ruleName; expected exactly one."
}
$effectiveRule = $effectiveRules[0]
$portFilter = Get-SingleFirewallFilter -Filters @($effectiveRule | Get-NetFirewallPortFilter) -Label "port"
$applicationFilter = Get-SingleFirewallFilter -Filters @($effectiveRule | Get-NetFirewallApplicationFilter) -Label "application"
$serviceFilter = Get-SingleFirewallFilter -Filters @($effectiveRule | Get-NetFirewallServiceFilter) -Label "service"
$addressFilter = Get-SingleFirewallFilter -Filters @($effectiveRule | Get-NetFirewallAddressFilter) -Label "address"
$interfaceFilter = Get-SingleFirewallFilter -Filters @($effectiveRule | Get-NetFirewallInterfaceFilter) -Label "interface"
$interfaceTypeFilter = Get-SingleFirewallFilter -Filters @($effectiveRule | Get-NetFirewallInterfaceTypeFilter) -Label "interface-type"
$securityFilter = Get-SingleFirewallFilter -Filters @($effectiveRule | Get-NetFirewallSecurityFilter) -Label "security"

$ruleIsExact = (
    $effectiveRule.Enabled.ToString() -eq "True" -and
    $effectiveRule.Profile.ToString() -eq "Any" -and
    $effectiveRule.Direction.ToString() -eq "Inbound" -and
    $effectiveRule.Action.ToString() -eq "Allow" -and
    $effectiveRule.EdgeTraversalPolicy.ToString() -eq "Block" -and
    $effectiveRule.LooseSourceMapping -eq $false -and
    $effectiveRule.LocalOnlyMapping -eq $false -and
    [string]::IsNullOrEmpty([string]$effectiveRule.Owner) -and
    (ConvertTo-JoinedString $effectiveRule.Platform) -eq "" -and
    (ConvertTo-JoinedString $effectiveRule.RemoteDynamicKeywordAddresses) -eq ""
)
$portFilterIsExact = (
    $portFilter.Protocol.ToString() -eq "TCP" -and
    (ConvertTo-JoinedString $portFilter.LocalPort) -eq "22" -and
    (ConvertTo-JoinedString $portFilter.RemotePort) -eq "Any" -and
    (ConvertTo-JoinedString $portFilter.IcmpType) -eq "Any" -and
    $portFilter.DynamicTarget.ToString() -eq "Any"
)
$applicationFilterIsExact = (
    $applicationFilter.Program -eq "Any" -and
    [string]::IsNullOrEmpty([string]$applicationFilter.Package)
)
$serviceFilterIsExact = $serviceFilter.Service -eq "Any"
$addressFilterIsExact = (
    (ConvertTo-JoinedString $addressFilter.LocalAddress) -eq "Any" -and
    (ConvertTo-JoinedString $addressFilter.RemoteAddress) -eq "Any"
)
$interfaceFiltersAreExact = (
    (ConvertTo-JoinedString $interfaceFilter.InterfaceAlias) -eq "Any" -and
    (ConvertTo-JoinedString $interfaceTypeFilter.InterfaceType) -eq "Any"
)
$securityFilterIsExact = (
    $securityFilter.Authentication.ToString() -eq "NotRequired" -and
    $securityFilter.Encryption.ToString() -eq "NotRequired" -and
    $securityFilter.OverrideBlockRules -eq $false -and
    (ConvertTo-JoinedString $securityFilter.LocalUser) -eq "Any" -and
    (ConvertTo-JoinedString $securityFilter.RemoteUser) -eq "Any" -and
    (ConvertTo-JoinedString $securityFilter.RemoteMachine) -eq "Any"
)
if (-not (
    $ruleIsExact -and
    $portFilterIsExact -and
    $applicationFilterIsExact -and
    $serviceFilterIsExact -and
    $addressFilterIsExact -and
    $interfaceFiltersAreExact -and
    $securityFilterIsExact
)) {
    throw "Effective firewall rule $ruleName is not the exact unrestricted inbound TCP port 22 rule."
}

Write-Host "OpenSSH Server is installed, automatic, running, and allowed on TCP port 22." -ForegroundColor Green
"""
