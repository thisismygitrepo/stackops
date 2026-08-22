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
if ($null -eq $serviceConfiguration -or $serviceConfiguration.StartMode -ne "Automatic") {
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
    -Protocol TCP `
    -LocalPort 22 | Out-Null

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

function Test-FirewallPortIncludes {
    param([object]$Ports, [int]$Port)
    foreach ($portExpression in @($Ports)) {
        $portText = [string]$portExpression
        if ($portText -eq "Any" -or $portText -eq [string]$Port) {
            return $true
        }
        if ($portText -match "^(\d+)-(\d+)$") {
            if ([int]$Matches[1] -le $Port -and $Port -le [int]$Matches[2]) {
                return $true
            }
        }
    }
    return $false
}

$effectiveProfiles = @(Get-NetFirewallProfile -PolicyStore ActiveStore -ErrorAction Stop)
$effectiveProfileNames = @($effectiveProfiles.Name | Sort-Object)
if (
    $effectiveProfiles.Count -ne 3 -or
    (ConvertTo-JoinedString $effectiveProfileNames) -ne "Domain,Private,Public"
) {
    throw "Effective firewall policy has $($effectiveProfiles.Count) profiles; expected Domain, Private, and Public."
}
$blockedProfiles = @(
    $effectiveProfiles | Where-Object {
        $_.Enabled.ToString() -ne "True" -or
        $_.AllowInboundRules.ToString() -ne "True" -or
        $_.AllowLocalFirewallRules.ToString() -ne "True"
    }
)
if ($blockedProfiles.Count -gt 0) {
    $blockedProfileStates = @(
        $blockedProfiles | ForEach-Object {
            "$($_.Name): Enabled=$($_.Enabled), AllowInboundRules=$($_.AllowInboundRules), AllowLocalFirewallRules=$($_.AllowLocalFirewallRules)"
        }
    )
    throw "Effective firewall profile policy suppresses the local inbound SSH rule: $($blockedProfileStates -join '; ')."
}

$effectiveRules = @(
    Get-NetFirewallRule -PolicyStore ActiveStore -Name $ruleName -TracePolicyStore -ErrorAction Stop
)
if ($effectiveRules.Count -ne 1) {
    throw "Effective firewall policy has $($effectiveRules.Count) rules named $ruleName; expected exactly one."
}
$effectiveRule = $effectiveRules[0]
$enforcementStatuses = @($effectiveRule.EnforcementStatus | ForEach-Object { [int]$_ })
$unexpectedEnforcementStatuses = @(
    $enforcementStatuses | Where-Object { $_ -ne 1 -and $_ -ne 5 }
)
if (
    $enforcementStatuses -notcontains 1 -or
    $unexpectedEnforcementStatuses.Count -gt 0
) {
    throw "Effective firewall rule $ruleName is not enforced: $($effectiveRule.EnforcementStatus -join ', ')."
}
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
    $effectiveRule.PolicyStoreSourceType.ToString() -eq "Local" -and
    $effectiveRule.PolicyStoreSource -eq "PersistentStore" -and
    [string]::IsNullOrEmpty([string]$effectiveRule.Owner) -and
    (ConvertTo-JoinedString $effectiveRule.Platform) -eq "" -and
    (ConvertTo-JoinedString $effectiveRule.RemoteDynamicKeywordAddresses) -eq "" -and
    [string]::IsNullOrEmpty([string]$effectiveRule.PolicyAppId)
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

$overlappingBlockRules = @(
    Get-NetFirewallRule -PolicyStore ActiveStore -ErrorAction Stop |
        Where-Object {
            $_.Enabled.ToString() -eq "True" -and
            $_.Direction.ToString() -eq "Inbound" -and
            $_.Action.ToString() -eq "Block"
        } |
        Where-Object {
            $blockPortFilters = @($_ | Get-NetFirewallPortFilter)
            if ($blockPortFilters.Count -ne 1) {
                throw "Effective block rule $($_.Name) has $($blockPortFilters.Count) port filters; expected exactly one."
            }
            $blockProtocol = $blockPortFilters[0].Protocol.ToString()
            ($blockProtocol -eq "Any" -or $blockProtocol -eq "TCP" -or $blockProtocol -eq "6") -and
            (Test-FirewallPortIncludes -Ports $blockPortFilters[0].LocalPort -Port 22)
        }
)
if ($overlappingBlockRules.Count -gt 0) {
    $blockRuleNames = @(
        $overlappingBlockRules | ForEach-Object { "$($_.DisplayName) [$($_.Name)]" }
    )
    throw "Effective firewall policy contains inbound block rules that override TCP port 22: $($blockRuleNames -join '; ')."
}

Write-Host "OpenSSH Server is installed, automatic, running, and allowed on TCP port 22." -ForegroundColor Green
"""
