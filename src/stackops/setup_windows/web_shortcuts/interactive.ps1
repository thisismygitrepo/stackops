
# Short @ bit.ly/cfgwindows

irm "https://raw.githubusercontent.com/thisismygitrepo/stackops/main/src/stackops/setup_windows/uv.ps1" | iex
irm "https://raw.githubusercontent.com/thisismygitrepo/stackops/main/src/stackops/scripts/windows/wrap_mcfg.ps1" | iex

function devops   { & "$HOME\.local\bin\uvx.exe" --python 3.14 --from "stackops>=8.93" devops $args }
function cloud    { & "$HOME\.local\bin\uvx.exe" --python 3.14 --from "stackops>=8.93" cloud $args }
function agents   { & "$HOME\.local\bin\uvx.exe" --python 3.14 --from "stackops>=8.93" agents $args }
function sessions { & "$HOME\.local\bin\uvx.exe" --python 3.14 --from "stackops>=8.93" sessions $args }
function fire     { & "$HOME\.local\bin\uvx.exe" --python 3.14 --from "stackops>=8.93" fire $args }
function croshell { & "$HOME\.local\bin\uvx.exe" --python 3.14 --from "stackops>=8.93" croshell $args }
function utils    { & "$HOME\.local\bin\uvx.exe" --python 3.14 --from "stackops>=8.93" utils $args }
function terminal { & "$HOME\.local\bin\uvx.exe" --python 3.14 --from "stackops>=8.93" terminal $args }
function seek     { & "$HOME\.local\bin\uvx.exe" --python 3.14 --from "stackops>=8.93" seek @args }

function d { wrap_in_shell_script devops @args }
function c { wrap_in_shell_script cloud @args }
function a { wrap_in_shell_script agents @args }
function sx { wrap_in_shell_script sessions @args }
function f { wrap_in_shell_script fire @args }
function rr { wrap_in_shell_script croshell @args }
function u { wrap_in_shell_script utils @args }
function t { wrap_in_shell_script terminal @args }
function p { wrap_in_shell_script seek @args }

Write-Host "mcfg command aliases are now defined in this PowerShell session."

d self config
