param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$LiteralPath,
    [Parameter(Mandatory = $true, Position = 1)]
    [int]$Width,
    [Parameter(Mandatory = $true, Position = 2)]
    [int]$Height,
    [Parameter(Mandatory = $true, Position = 3)]
    [int]$_X,
    [Parameter(Mandatory = $true, Position = 4)]
    [int]$_Y,
    [Parameter(Mandatory = $true, Position = 5)]
    [ValidateSet("preview", "preload")]
    [string]$_Mode
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

[string]$lowerPath = $LiteralPath.ToLowerInvariant()
[string]$extension = [IO.Path]::GetExtension($lowerPath)

if ($extension -in ".md", ".markdown") {
    $Env:CLICOLOR_FORCE = "1"
    & glow --width $Width --style dark -- $LiteralPath
    exit $LASTEXITCODE
}
if ($extension -eq ".csv") {
    & uvx --from rich-cli rich --force-terminal --csv --head $Height --width $Width $LiteralPath
    exit $LASTEXITCODE
}
if ($extension -eq ".json") {
    & jq --color-output . -- $LiteralPath
    exit $LASTEXITCODE
}

[string[]]$archiveSuffixes = @(
    ".7z", ".bz2", ".gz", ".jar", ".rar", ".tar", ".tar.bz2", ".tar.gz",
    ".tar.xz", ".tar.zst", ".tgz", ".txz", ".xz", ".zip", ".zst"
)
if ($null -ne ($archiveSuffixes | Where-Object { $lowerPath.EndsWith($_) } | Select-Object -First 1)) {
    & ouch list -- $LiteralPath
    exit $LASTEXITCODE
}

[string[]]$imageExtensions = @(
    ".avif", ".bmp", ".gif", ".heic", ".heif", ".ico", ".jpeg", ".jpg",
    ".png", ".tif", ".tiff", ".webp"
)
if ($extension -in $imageExtensions) {
    & chafa --size "${Width}x${Height}" -- $LiteralPath
    exit $LASTEXITCODE
}
if ($extension -eq ".pdf") {
    & pdftotext -layout -nopgbrk -q -- $LiteralPath -
    exit $LASTEXITCODE
}

& bat --color=always --style=plain --paging=never --terminal-width $Width --line-range "1:$Height" -- $LiteralPath
exit $LASTEXITCODE
