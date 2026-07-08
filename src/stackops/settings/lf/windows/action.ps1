param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet(
        "toggle-preview-max",
        "repo-root",
        "fullscreen-preview",
        "interactive-view",
        "open-default",
        "compress-selected",
        "decrypt",
        "copy-paths"
    )]
    [string]$Action
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

[string[]]$selectedPaths = @()
if (-not [string]::IsNullOrEmpty($Env:fs)) {
    $selectedPaths = @($Env:fs -split "`n")
}

[string[]]$targets = @($Env:fx -split "`n")
[string]$scriptName = ""

switch ($Action) {
    "toggle-preview-max" {
        [string]$remoteCommand = if ($Env:lf_ratios -eq "1:999") {
            ":set ratios 1:3:5; set preview"
        }
        else {
            ":set preview; set ratios 1:999"
        }
        & $Env:lf -remote "send $Env:id $remoteCommand"
        exit $LASTEXITCODE
    }
    "repo-root" {
        [string]$repoRoot = & git rev-parse --show-toplevel
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
        [string]$quotedRepoRoot = ConvertTo-Json -Compress -InputObject $repoRoot
        & $Env:lf -remote "send $Env:id cd $quotedRepoRoot"
        exit $LASTEXITCODE
    }
    "copy-paths" {
        $targets -join "`n" | & cb cp0
        exit $LASTEXITCODE
    }
    "decrypt" {
        if (-not $Env:f.EndsWith(".gpg", [StringComparison]::OrdinalIgnoreCase)) {
            throw "Expected a .gpg file: $Env:f"
        }
        [string]$outputPath = $Env:f.Substring(0, $Env:f.Length - 4)
        & gpg --output $outputPath --decrypt $Env:f
        exit $LASTEXITCODE
    }
    "fullscreen-preview" {
        $scriptName = "fullscreen_preview.py"
    }
    "interactive-view" {
        $scriptName = "interactive_view.py"
    }
    "open-default" {
        $scriptName = "open_default_app.py"
    }
    "compress-selected" {
        $scriptName = "compress_selected.py"
    }
}

[string]$scriptPath = Join-Path $HOME ".config/stackops/settings/yazi/scripts/$scriptName"
[string[]]$markedArguments = @(
    "__YAZI_HOVERED__",
    $Env:f,
    "__YAZI_SELECTED__"
) + $selectedPaths

& uv run --isolated --no-project --python 3.14 --with stackops $scriptPath @markedArguments
exit $LASTEXITCODE
