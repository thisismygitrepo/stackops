if (-not (Get-Command "starship" -ErrorAction SilentlyContinue)) {
    Write-Host "Error: 'starship' not found."
    exit 1
}

$presetNames = @(& starship preset --list 2>$null | ForEach-Object { $_.Trim() } | Where-Object { $_ })

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: failed to list Starship presets."
    exit 1
}

if (-not $presetNames) {
    Write-Host "Error: no Starship presets found."
    exit 1
}

$input_list = $presetNames

$preview_config = "$env:TEMP/starship_preview.toml"
$preview_shell = if (Get-Command "pwsh" -ErrorAction SilentlyContinue) { "pwsh" } else { "powershell" }

$preview_cmd = "$preview_shell -NoProfile -Command `"`$preset = '{}'; starship preset `$preset > '$preview_config'; `$env:STARSHIP_CONFIG='$preview_config'; `$env:STARSHIP_SHELL='powershell'; starship prompt`""

if (Get-Command "tv" -ErrorAction SilentlyContinue) {
    $selected_line = $input_list | tv --preview-command $preview_cmd --preview-size 50
} elseif (Get-Command "fzf" -ErrorAction SilentlyContinue) {
    $selected_line = $input_list | fzf --ansi --preview $preview_cmd --preview-window bottom:50%
} else {
    Write-Host "Error: 'tv' or 'fzf' not found."
    exit 1
}

if ($selected_line) {
    $selected_preset = $selected_line
    Write-Host "Applying $selected_preset..."
    starship preset $selected_preset -o "$HOME/.config/starship.toml"
    Write-Host "Done!"
}
