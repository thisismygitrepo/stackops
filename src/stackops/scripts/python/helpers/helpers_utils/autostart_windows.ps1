$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
$entries = [System.Collections.Generic.List[object]]::new()
$versionKey = 'Software\Microsoft\Windows\CurrentVersion'
$nativeView = if ([Environment]::Is64BitOperatingSystem) { 'Registry64' } else { 'Registry32' }

function Test-StartupEnabled {
    param(
        [Microsoft.Win32.RegistryKey] $Base,
        [string] $Kind,
        [string] $Name
    )
    $approved = $Base.OpenSubKey("$versionKey\Explorer\StartupApproved\$Kind")
    if ($null -eq $approved) {
        return $true
    }
    try {
        $state = $approved.GetValue($Name)
        return -not ($state -is [byte[]] -and $state.Length -gt 0 -and $state[0] -in @(3, 7))
    } finally {
        $approved.Dispose()
    }
}

try {
    $systemDirectory = [regex]::Escape([Environment]::GetFolderPath('System') + '\')
    foreach ($service in Get-CimInstance -ClassName Win32_Service -Filter "StartMode = 'Auto'") {
        $entries.Add([ordered]@{
            name = [string] $service.Name
            description = [string] $service.DisplayName
            scope = 'boot'
            source = 'Windows service'
            stock = [bool] ($service.PathName -match ('^\s*"?' + $systemDirectory))
        })
    }

    foreach ($hive in @('CurrentUser', 'LocalMachine')) {
        $nativeBase = [Microsoft.Win32.RegistryKey]::OpenBaseKey($hive, $nativeView)
        try {
            $views = @($nativeView)
            if ($hive -eq 'LocalMachine' -and [Environment]::Is64BitOperatingSystem) {
                $views += 'Registry32'
            }
            $label = if ($hive -eq 'CurrentUser') { 'HKCU' } else { 'HKLM' }
            foreach ($view in $views) {
                $base = [Microsoft.Win32.RegistryKey]::OpenBaseKey($hive, $view)
                try {
                    foreach ($kind in @('Run', 'RunOnce')) {
                        $key = $base.OpenSubKey("$versionKey\$kind")
                        if ($null -eq $key) { continue }
                        try {
                            foreach ($name in $key.GetValueNames()) {
                                if ($key.GetValueKind($name) -notin @('String', 'ExpandString')) { continue }
                                $approvalKind = if ($view -ne $nativeView) { 'Run32' } else { 'Run' }
                                if ($kind -eq 'Run' -and -not (Test-StartupEnabled $nativeBase $approvalKind $name)) {
                                    continue
                                }
                                $description = if ($kind -eq 'RunOnce') { 'Runs once at login' } else { 'Runs at login' }
                                if ($kind -eq 'RunOnce' -and $hive -eq 'LocalMachine') {
                                    $description = 'Runs once at administrator login'
                                }
                                $architecture = if ($view -ne $nativeView) { ' (32-bit)' } else { '' }
                                $entries.Add([ordered]@{
                                    name = if ($name) { $name } else { '(Default)' }
                                    description = $description
                                    scope = 'login'
                                    source = "$label $kind$architecture"
                                    stock = $false
                                })
                            }
                        } finally {
                            $key.Dispose()
                        }
                    }
                } finally {
                    $base.Dispose()
                }
            }

            $folderName = if ($hive -eq 'CurrentUser') { 'Startup' } else { 'CommonStartup' }
            $folder = [Environment]::GetFolderPath($folderName)
            if ($folder -and (Test-Path -LiteralPath $folder -PathType Container)) {
                foreach ($item in Get-ChildItem -LiteralPath $folder -File -Force) {
                    if ($item.Name -eq 'desktop.ini' -or -not (Test-StartupEnabled $nativeBase 'StartupFolder' $item.Name)) {
                        continue
                    }
                    $entries.Add([ordered]@{
                        name = $item.BaseName
                        description = $item.Name
                        scope = 'login'
                        source = if ($hive -eq 'CurrentUser') { 'Startup folder (user)' } else { 'Startup folder (all users)' }
                        stock = $false
                    })
                }
            }
        } finally {
            $nativeBase.Dispose()
        }
    }

    foreach ($task in Get-ScheduledTask -TaskPath '*') {
        if (-not $task.Settings.Enabled) { continue }
        $scopes = [System.Collections.Generic.HashSet[string]]::new()
        foreach ($trigger in $task.Triggers) {
            if (-not $trigger.Enabled) { continue }
            if ($trigger.EndBoundary -and [datetime] $trigger.EndBoundary -le [datetime]::Now) { continue }
            switch ($trigger.CimClass.CimClassName) {
                'MSFT_TaskBootTrigger' { [void] $scopes.Add('boot') }
                'MSFT_TaskLogonTrigger' { [void] $scopes.Add('login') }
            }
        }
        foreach ($scope in $scopes) {
            $entries.Add([ordered]@{
                name = [string] $task.TaskName
                description = if ($scope -eq 'boot') { 'Scheduled boot task' } else { 'Scheduled logon task' }
                scope = $scope
                source = "Task Scheduler: $($task.TaskPath)"
                stock = $task.TaskPath.StartsWith('\Microsoft\Windows\', [StringComparison]::OrdinalIgnoreCase)
            })
        }
    }
    ConvertTo-Json -InputObject $entries.ToArray() -Depth 3 -Compress
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
}
