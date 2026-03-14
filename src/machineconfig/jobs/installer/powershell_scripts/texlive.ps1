$downloadUrl = 'https://mirror.ctan.org/systems/texlive/tlnet/install-tl-windows.exe'
$destination = Join-Path ([System.IO.Path]::GetTempPath()) 'install-tl-windows.exe'

Write-Host "Downloading TeX Live installer from $downloadUrl"
curl.exe -L --fail --output $destination $downloadUrl

if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $destination)) {
    throw "Failed to download TeX Live installer."
}

Write-Host "Launching TeX Live installer: $destination"
$process = Start-Process -FilePath $destination -Wait -PassThru

if ($null -eq $process) {
    throw "Failed to launch TeX Live installer."
}

if ($process.ExitCode -ne 0) {
    throw "TeX Live installer exited with code $($process.ExitCode)."
}

Write-Host "TeX Live installer completed."
