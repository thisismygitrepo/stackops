Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Test-TextPath {
    param(
        [Parameter(Mandatory = $true, Position = 0)]
        [string]$LiteralPath
    )

    if (-not [IO.File]::Exists($LiteralPath)) {
        return $false
    }

    [byte[]]$buffer = [byte[]]::new(8192)
    $stream = [IO.File]::OpenRead($LiteralPath)
    try {
        [int]$bytesRead = $stream.Read($buffer, 0, $buffer.Length)
    }
    finally {
        $stream.Dispose()
    }

    if ($bytesRead -eq 0) {
        return $true
    }
    if ($bytesRead -ge 2 -and (($buffer[0] -eq 0xFF -and $buffer[1] -eq 0xFE) -or ($buffer[0] -eq 0xFE -and $buffer[1] -eq 0xFF))) {
        return $true
    }
    if ($bytesRead -ge 4 -and (($buffer[0] -eq 0x00 -and $buffer[1] -eq 0x00 -and $buffer[2] -eq 0xFE -and $buffer[3] -eq 0xFF) -or ($buffer[0] -eq 0xFF -and $buffer[1] -eq 0xFE -and $buffer[2] -eq 0x00 -and $buffer[3] -eq 0x00))) {
        return $true
    }
    if ([Array]::IndexOf($buffer, [byte]0, 0, $bytesRead) -ge 0) {
        return $false
    }

    try {
        [void][Text.UTF8Encoding]::new($false, $true).GetString($buffer, 0, $bytesRead)
        return $true
    }
    catch [Text.DecoderFallbackException] {
        return $false
    }
}

[string[]]$textExtensions = @(
    ".bash", ".bat", ".cmd", ".css", ".html", ".js", ".json", ".jsx",
    ".md", ".ps1", ".py", ".rs", ".sh", ".toml", ".ts", ".tsx",
    ".txt", ".yaml", ".yml", ".zsh"
)
[string[]]$defaultExtensions = @(
    ".aac", ".avif", ".avi", ".bmp", ".flac", ".gif", ".heic", ".heif",
    ".ico", ".jpeg", ".jpg", ".m4a", ".mkv", ".mov", ".mp3", ".mp4",
    ".ogg", ".opus", ".pdf", ".png", ".svg", ".tif", ".tiff", ".wav",
    ".webm", ".webp"
)
[string[]]$targets = @($Env:fx -split "`n")
$textTargets = [Collections.Generic.List[string]]::new()
$defaultTargets = [Collections.Generic.List[string]]::new()

foreach ($target in $targets) {
    [string]$extension = [IO.Path]::GetExtension($target)
    if ($defaultExtensions -contains $extension) {
        $defaultTargets.Add($target)
    }
    elseif ($textExtensions -contains $extension -or (Test-TextPath $target)) {
        $textTargets.Add($target)
    }
    else {
        $defaultTargets.Add($target)
    }
}

foreach ($target in $defaultTargets) {
    Start-Process -FilePath $target
}

if ($textTargets.Count -gt 0) {
    & code --wait -- @textTargets
    exit $LASTEXITCODE
}
