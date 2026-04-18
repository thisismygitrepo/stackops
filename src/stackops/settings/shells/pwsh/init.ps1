

$CONFIG_ROOT = "$HOME\.config\stackops"

function Add-ToPathIfNotAlready {
    param (
        [Parameter(Mandatory=$true)]
        [string[]]$Directories
    )
    foreach ($dir in $Directories) {
        if ($env:Path -notlike "*$dir*") {
            $env:Path += ";$dir"
        }
    }
}

# Use bun as node if available
if (Test-Path "$HOME\.bun\bin\bun.exe") {
    Set-Alias -Name node -Value "$HOME\.bun\bin\bun.exe" -Option AllScope
}

Add-ToPathIfNotAlready -Directories @(
    "$HOME\.local\bin",
    "$HOME\.local\share\poppler\Library\bin",
    "$HOME\.bun\bin",
    "$CONFIG_ROOT\scripts",
    "$HOME\dotfiles\stackops\scripts\windows",
    "C:\Program Files (x86)\GnuWin32\bin",
    "C:\Program Files\CodeBlocks\MinGW\bin",
    "C:\Program Files\nu\bin",
    "C:\Program Files\Graphviz\bin",
    "C:\Program Files\7-Zip",
    "C:\Program Files\Git\bin"  # gives sh.exe bash.exe & git.exe
)

function xx { codex --dangerously-bypass-approvals-and-sandbox @args }
function xc { copilot --yolo @args }


# sources  ================================================================
if (Test-Path "$CONFIG_ROOT\scripts\wrap_mcfg.ps1") {
    . $CONFIG_ROOT\settings\broot\brootcd.ps1
    . $CONFIG_ROOT\settings\lf\windows\lfcd.ps1
    . $CONFIG_ROOT\settings\tere\terecd.ps1
    . $CONFIG_ROOT\settings\yazi\shell\yazi_cd.ps1
    . $CONFIG_ROOT\scripts\wrap_mcfg.ps1

    function lsdla { lsd -la }
    Set-Alias -Name l -Value lsdla -Option AllScope

    function d { wrap_in_shell_script devops $args }
    function c { wrap_in_shell_script cloud $args }
    function a { wrap_in_shell_script agents $args }
    function t { wrap_in_shell_script terminal $args }
    function f { wrap_in_shell_script fire $args }
    function rr { wrap_in_shell_script croshell $args }
    function u { wrap_in_shell_script utils $args }
    function s { wrap_in_shell_script seek @args }

}
else {
    Write-Host "Missing config files: $CONFIG_ROOT"
    function lsdla { lsd -la }
    Set-Alias -Name l -Value lsdla -Option AllScope
    function d { devops $args }
    function c { cloud $args }
    function a { agents $args }
    function t { terminal $args }
    function f { fire $args }
    function rr { croshell $args }
    function u { utils $args }
    function s { seek @args }
}


# prompt integrations ===========================================================

try {
    # Initialize Starship prompt
    Invoke-Expression (&starship init powershell)
}
catch {
    # Do nothing
}


# history search =====================================================

if (Get-Command atuin -ErrorAction SilentlyContinue) {
    try {
        # Invoke-Expression (& atuin init powershell | Out-String)
        atuin init powershell --disable-up-arrow | Out-String | Invoke-Expression
    }
    catch {
        # Do nothing
    }
}
elseif (Get-Command mcfly -ErrorAction SilentlyContinue) {
    try {
        Invoke-Expression (& mcfly init powershell | Out-String)
    }
    catch {
        # Do nothing
    }
}
else {
    try {
        Import-Module PSReadLine -ErrorAction Stop | Out-Null
        Set-PSReadLineKeyHandler -Chord Ctrl+r -ScriptBlock {
            param($key, $arg)

            $buffer = $null
            $cursor = 0
            try { [Microsoft.PowerShell.PSConsoleReadLine]::GetBufferState([ref]$buffer, [ref]$cursor) } catch { }

            $selected = $null
            try {
                [Console]::WriteLine()
                $selected = (& tv pwsh-history 2>$null | Select-Object -First 1)
            }
            catch {
                $selected = $null
            }

            if ([string]::IsNullOrWhiteSpace($selected)) {
                return
            }

            $selected = $selected.TrimEnd("`r", "`n")

            try {
                $existingLen = if ($null -eq $buffer) { 0 } else { $buffer.Length }
                [Microsoft.PowerShell.PSConsoleReadLine]::Replace(0, $existingLen, $selected)
                try { [Microsoft.PowerShell.PSConsoleReadLine]::SetCursorPosition($selected.Length) } catch { }
            }
            catch {
                try { [Microsoft.PowerShell.PSConsoleReadLine]::Insert($selected) } catch { }
            }
        }
    }
    catch {
        # Do nothing
    }
}

try {
    # zoxide must be initialized after other prompt integrations so its hook
    # wraps the final prompt function instead of getting replaced on Windows.
    Invoke-Expression (& {
        (zoxide init --hook pwd powershell | Out-String)
    })
}
catch {
    # Do nothing
}
