# Bootstrap stackops from the current GitHub main branch into this PowerShell session.

irm "https://raw.githubusercontent.com/thisismygitrepo/stackops/main/src/stackops/scripts/setup/windows/uv.ps1" | iex
irm "https://raw.githubusercontent.com/thisismygitrepo/stackops/main/src/stackops/scripts/windows/wrap_stackops.ps1" | iex

$script:StackopsFrom = "git+https://github.com/thisismygitrepo/stackops"

function Invoke-StackopsUvx {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Arguments
    )

    & "$HOME\.local\bin\uvx.exe" --python 3.14 --from $script:StackopsFrom @Arguments
}

function stackops { Invoke-StackopsUvx stackops @args }
function devops { Invoke-StackopsUvx devops @args }
function cloud { Invoke-StackopsUvx cloud @args }
function agents { Invoke-StackopsUvx agents @args }
function fire { Invoke-StackopsUvx fire @args }
function croshell { Invoke-StackopsUvx croshell @args }
function utils { Invoke-StackopsUvx utils @args }
function terminal { Invoke-StackopsUvx terminal @args }
function seek { Invoke-StackopsUvx seek @args }

function d { wrap_in_shell_script devops @args }
function c { wrap_in_shell_script cloud @args }
function a { wrap_in_shell_script agents @args }
function f { wrap_in_shell_script fire @args }
function rr { wrap_in_shell_script croshell @args }
function u { wrap_in_shell_script utils @args }
function t { wrap_in_shell_script terminal @args }
function p { wrap_in_shell_script seek @args }

Write-Host "stackops GitHub command functions are now defined in this PowerShell session."

devops config interactive
