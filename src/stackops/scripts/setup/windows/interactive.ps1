
# Source @ https://raw.githubusercontent.com/thisismygitrepo/machineconfig/refs/heads/main/src/machineconfig/setup_windows/web_shortcuts/interactive.ps1
# Short @ bit.ly/cfgwindows
# Source @ https://raw.githubusercontent.com/thisismygitrepo/stackops/refs/heads/main/src/stackops/scripts/setup/windows/interactive.ps1
# Short @ bit.ly/sopsw

irm "https://raw.githubusercontent.com/thisismygitrepo/stackops/main/src/stackops/scripts/setup/windows/uv.ps1" | iex
irm "https://raw.githubusercontent.com/thisismygitrepo/stackops/main/src/stackops/scripts/windows/wrap_stackops.ps1" | iex

# live from github version
# function stackops { & "$HOME\.local\bin\uvx.exe" --python 3.14 --from "git+https://github.com/thisismygitrepo/stackops" stackops $args }

function devops   { & "$HOME\.local\bin\uvx.exe" --python 3.14 --from "stackops>=26.8.2" devops $args }
function cloud    { & "$HOME\.local\bin\uvx.exe" --python 3.14 --from "stackops>=26.8.2" cloud $args }
function agents   { & "$HOME\.local\bin\uvx.exe" --python 3.14 --from "stackops>=26.8.2" agents $args }
function sessions { & "$HOME\.local\bin\uvx.exe" --python 3.14 --from "stackops>=26.8.2" sessions $args }
function fire     { & "$HOME\.local\bin\uvx.exe" --python 3.14 --from "stackops>=26.8.2" fire $args }
function preview { & "$HOME\.local\bin\uvx.exe" --python 3.14 --from "stackops>=26.8.2" preview $args }
function utils    { & "$HOME\.local\bin\uvx.exe" --python 3.14 --from "stackops>=26.8.2" utils $args }
function terminal { & "$HOME\.local\bin\uvx.exe" --python 3.14 --from "stackops>=26.8.2" terminal $args }
function seek     { & "$HOME\.local\bin\uvx.exe" --python 3.14 --from "stackops>=26.8.2" seek @args }

function d { wrap_in_shell_script devops @args }
function c { wrap_in_shell_script cloud @args }
function a { wrap_in_shell_script agents @args }
function sx { wrap_in_shell_script sessions @args }
function f { wrap_in_shell_script fire @args }
function p { wrap_in_shell_script preview @args }
function u { wrap_in_shell_script utils @args }
function t { wrap_in_shell_script terminal @args }
function s { wrap_in_shell_script seek @args }

Write-Host "stackops command aliases are now defined in this PowerShell session."

devops config interactive
