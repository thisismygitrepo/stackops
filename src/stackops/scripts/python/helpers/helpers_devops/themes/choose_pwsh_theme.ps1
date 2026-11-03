param([string]$Theme, [switch]$List, [switch]$Json)

$ErrorActionPreference = "Stop"
if ($Theme -and $List) { throw "Choose -Theme or -List." }
if ($Json -and -not ($Theme -or $List)) { throw "-Json requires -Theme or -List." }
if (-not ($Theme -or $List) -and ($env:STACKOPS_NON_INTERACTIVE -eq "1" -or [Console]::IsInputRedirected -or [Console]::IsOutputRedirected)) {
    throw "Interactive theme selection requires a terminal; pass -Theme or -List."
}
$themesDir = $env:POSH_THEMES_PATH
if (-not $themesDir -and $env:LOCALAPPDATA) {
    $themesDir = Join-Path $env:LOCALAPPDATA "Programs\oh-my-posh\themes"
}
if (-not $themesDir -or -not (Test-Path -LiteralPath $themesDir -PathType Container)) {
    throw "Oh My Posh themes directory is missing; set POSH_THEMES_PATH."
}
$themes = @(Get-ChildItem -LiteralPath $themesDir -Filter "*.omp.json" | Sort-Object Name | ForEach-Object {
    [PSCustomObject]@{ Name = $_.Name.Substring(0, $_.Name.Length - ".omp.json".Length); Path = $_.FullName }
})
if ($List) {
    $names = @($themes | ForEach-Object { $_.Name })
    if ($Json) { @{ target = "pwsh"; themes = $names } | ConvertTo-Json -Compress } else { $names }
    exit 0
}
if ($Theme) {
    $matches = @($themes | Where-Object { $_.Name -ceq $Theme })
    if ($matches.Count -ne 1) { throw "Unknown or ambiguous theme '$Theme'; use -List." }
    $selected = $matches[0]
} else {
    $previewCommand = "oh-my-posh print primary --config {}"
    $selectedPath = $themes | ForEach-Object { $_.Path } | fzf --height 80% --border --ansi --reverse --preview $previewCommand
    if (-not $selectedPath) { exit 130 }
    $selected = $themes | Where-Object { $_.Path -ceq $selectedPath } | Select-Object -First 1
    if (-not $selected) { throw "The selected theme is not in the catalog." }
}
$profilePath = $PROFILE
$profileDir = Split-Path $profilePath -Parent
New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
$profileContent = if (Test-Path -LiteralPath $profilePath) { Get-Content -LiteralPath $profilePath -Raw } else { "" }
if ($null -eq $profileContent) { $profileContent = "" }
$escapedPath = $selected.Path.Replace("'", "''")
$ompLine = "oh-my-posh init pwsh --config '$escapedPath' | Invoke-Expression"
$newline = [Environment]::NewLine
if ($profileContent -match "oh-my-posh init pwsh[^\r\n]*") {
    $profileContent = [regex]::Replace($profileContent, "oh-my-posh init pwsh[^\r\n]*", [System.Text.RegularExpressions.MatchEvaluator]{ param($match) $ompLine })
} else {
    if ($profileContent.Length -gt 0 -and -not $profileContent.EndsWith($newline)) { $profileContent += $newline }
    $profileContent += $ompLine + $newline
}
$profileContent | Set-Content -LiteralPath $profilePath -Encoding UTF8 -NoNewline
if ($Json) {
    @{ target = "pwsh"; theme = $selected.Name; paths = @($profilePath); applied = $true } | ConvertTo-Json -Compress
} else {
    Write-Host "Applied Oh My Posh theme '$($selected.Name)' in $profilePath"
}
