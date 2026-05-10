Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$pluginRepository = "https://github.com/psmux/psmux-plugins.git"
$temporaryCheckout = Join-Path ([System.IO.Path]::GetTempPath()) ("psmux-plugins-" + [System.Guid]::NewGuid().ToString())
$pluginRoot = Join-Path $HOME ".psmux\plugins"
$ppmTarget = Join-Path $pluginRoot "ppm"

try {
    git clone --depth 1 $pluginRepository $temporaryCheckout

    New-Item -ItemType Directory -Path $pluginRoot -Force | Out-Null

    if (Test-Path $ppmTarget) {
        Remove-Item $ppmTarget -Recurse -Force
    }

    Copy-Item (Join-Path $temporaryCheckout "ppm") $ppmTarget -Recurse
}
finally {
    if (Test-Path $temporaryCheckout) {
        Remove-Item $temporaryCheckout -Recurse -Force
    }
}

Write-Host "PPM installed to $ppmTarget"
Write-Host "Start psmux and press Prefix + I to install the plugins declared in psmux.plugins.conf."
