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
    script = r'''
$ErrorActionPreference = "Stop"
function Test-PortMatch {
    param([object[]]$Values, [int]$Port, [bool]$RequireAny)
    foreach ($rawValue in $Values) {
        foreach ($value in ([string]$rawValue -split "[, ]+")) {
            if ($value -in @("Any", "*")) { return $true }
            if ($RequireAny) { continue }
            if ($value -match "^(\d+)$" -and [int]$Matches[1] -eq $Port) { return $true }
            if ($value -match "^(\d+)-(\d+)$" -and [int]$Matches[1] -le $Port -and $Port -le [int]$Matches[2]) {
                return $true
            }
        }
    }
    return $false
}
function Test-AnyValue {
    param([object[]]$Values)
    $matchingValue = @($Values | ForEach-Object { [string]$_ }) |
        Where-Object { $_ -in @("Any", "All", "*") } |
        Select-Object -First 1
    return $null -ne $matchingValue
}
$targetPort = __TARGET_PORT__
$profileNames = @(Get-NetConnectionProfile | ForEach-Object {
    switch ([string]$_.NetworkCategory) {
        "DomainAuthenticated" { "Domain" }
        "Private" { "Private" }
        "Public" { "Public" }
    }
} | Sort-Object -Unique)
if ($profileNames.Count -eq 0) { exit 5 }
$activeProfiles = @(
    $profileNames |
        ForEach-Object { Get-NetFirewallProfile -PolicyStore ActiveStore -Name $_ } |
        Where-Object Enabled
)
if ($activeProfiles.Count -eq 0) { exit 0 }
$rules = @(Get-NetFirewallRule -PolicyStore ActiveStore -Enabled True -Direction Inbound)
foreach ($profile in $activeProfiles) {
    $defaultInboundAction = $profile.DefaultInboundAction.ToString()
    if ($defaultInboundAction -notin @("Allow", "Block")) { exit 5 }
    if ($profile.AllowInboundRules.ToString() -ne "True") {
        if ($defaultInboundAction -eq "Allow") { continue }
        exit 3
    }
    $allowProved = $defaultInboundAction -eq "Allow"
    $scopedRuleFound = $false
    foreach ($rule in $rules) {
        $ruleProfiles = @($rule.Profile.ToString() -split "," | ForEach-Object { $_.Trim() })
        if ($ruleProfiles -notcontains "Any" -and $ruleProfiles -notcontains $profile.Name) { continue }
        $portFilters = @($rule | Get-NetFirewallPortFilter)
        $applicationFilters = @($rule | Get-NetFirewallApplicationFilter)
        $serviceFilters = @($rule | Get-NetFirewallServiceFilter)
        $addressFilters = @($rule | Get-NetFirewallAddressFilter)
        $interfaceFilters = @($rule | Get-NetFirewallInterfaceFilter)
        $interfaceTypeFilters = @($rule | Get-NetFirewallInterfaceTypeFilter)
        $securityFilters = @($rule | Get-NetFirewallSecurityFilter)
        if (
            $portFilters.Count -ne 1 -or
            $applicationFilters.Count -ne 1 -or
            $serviceFilters.Count -ne 1 -or
            $addressFilters.Count -ne 1 -or
            $interfaceFilters.Count -ne 1 -or
            $interfaceTypeFilters.Count -ne 1 -or
            $securityFilters.Count -ne 1
        ) { exit 5 }
        $protocol = $portFilters[0].Protocol.ToString()
        if ($protocol -notin @("TCP", "6", "Any", "256")) { continue }
        if (-not (Test-PortMatch -Values @($portFilters[0].LocalPort) -Port $targetPort -RequireAny $false)) { continue }
        $enforcementStatuses = @($rule.EnforcementStatus | ForEach-Object { [int]$_ })
        $unexpectedEnforcementStatuses = @(
            $enforcementStatuses | Where-Object { $_ -ne 1 -and $_ -ne 5 }
        )
        $ruleIsEnforced = (
            $enforcementStatuses -contains 1 -and
            $unexpectedEnforcementStatuses.Count -eq 0
        )
        $isUnscoped = (
            $ruleIsEnforced -and
            (Test-PortMatch -Values @($portFilters[0].RemotePort) -Port $targetPort -RequireAny $true) -and
            (Test-AnyValue -Values @($applicationFilters[0].Program)) -and
            [string]::IsNullOrEmpty([string]$applicationFilters[0].Package) -and
            (Test-AnyValue -Values @($serviceFilters[0].Service)) -and
            (Test-AnyValue -Values @($addressFilters[0].LocalAddress)) -and
            (Test-AnyValue -Values @($addressFilters[0].RemoteAddress)) -and
            (Test-AnyValue -Values @($interfaceFilters[0].InterfaceAlias)) -and
            (Test-AnyValue -Values @($interfaceTypeFilters[0].InterfaceType)) -and
            $securityFilters[0].Authentication.ToString() -eq "NotRequired" -and
            $securityFilters[0].Encryption.ToString() -eq "NotRequired" -and
            $securityFilters[0].OverrideBlockRules -eq $false -and
            (Test-AnyValue -Values @($securityFilters[0].LocalUser)) -and
            (Test-AnyValue -Values @($securityFilters[0].RemoteUser)) -and
            (Test-AnyValue -Values @($securityFilters[0].RemoteMachine)) -and
            [string]::IsNullOrEmpty([string]$rule.Owner) -and
            [string]::IsNullOrEmpty([string]($rule.RemoteDynamicKeywordAddresses -join ",")) -and
            [string]::IsNullOrEmpty([string]$rule.PolicyAppId)
        )
        if (-not $isUnscoped) {
            if ($rule.Action.ToString() -eq "Block") { exit 5 }
            $scopedRuleFound = $true
            continue
        }
        if ($rule.Action.ToString() -eq "Block") { exit 4 }
        if ($rule.Action.ToString() -eq "Allow") { $allowProved = $true }
    }
    if (-not $allowProved) {
        if ($scopedRuleFound) { exit 5 }
        exit 3
    }
}
exit 0
'''.replace("__TARGET_PORT__", str(target_port))
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
    if result.returncode == 5:
        raise RuntimeError(
            f"Windows Firewall has scoped or structurally ambiguous rules covering TCP port {target_port}, so WSL ingress cannot be proven. "
            "Inspect the active profile, rule enforcement, ports, addresses, application, service, interface, and security filters, then retry."
        )
    error_output = result.stderr.strip() or result.stdout.strip()
    raise RuntimeError(
        f"Unable to verify Windows Firewall for WSL: {error_output}. Run the check from elevated PowerShell, then retry."
    )
