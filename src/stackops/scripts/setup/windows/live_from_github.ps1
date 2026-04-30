
# Short @ https://bit.ly/cfgwg

irm "https://raw.githubusercontent.com/thisismygitrepo/stackops/main/src/stackops/scripts/setup/windows/uv.ps1" | iex
irm "https://raw.githubusercontent.com/thisismygitrepo/stackops/main/src/stackops/scripts/windows/wrap_stackops.ps1" | iex

function stackops { & "$HOME\.local\bin\uvx.exe" --python 3.14 --from "git+https://github.com/thisismygitrepo/stackops" stackops $args }

function devops {stackops devops @args }
function cloud {stackops cloud @args }
function agents {stackops agents @args }
function sessions {stackops sessions @args }
function fire {stackops fire @args }
function croshell {stackops croshell @args }
function utils {stackops utils @args }
function terminal {stackops terminal @args }
function seek { & "$HOME\.local\bin\uvx.exe" --python 3.14 --from "git+https://github.com/thisismygitrepo/stackops" seek @args }

function d { wrap_in_shell_script stackops devops @args }
function c { wrap_in_shell_script stackops cloud @args }
function a { wrap_in_shell_script stackops agents @args }
function sx { wrap_in_shell_script stackops sessions @args }
function f { wrap_in_shell_script stackops fire @args }
function rr { wrap_in_shell_script stackops croshell @args }
function u { wrap_in_shell_script stackops utils @args }
function t { wrap_in_shell_script stackops terminal @args }
function p { wrap_in_shell_script seek @args }

Write-Host "stackops command aliases are now defined in this PowerShell session."
