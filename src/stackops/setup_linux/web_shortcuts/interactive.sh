#!/bin/bash
. <( curl -sSL "https://raw.githubusercontent.com/thisismygitrepo/stackops/main/src/stackops/setup_linux/uv.sh")
. <( curl -sSL "https://raw.githubusercontent.com/thisismygitrepo/stackops/main/src/stackops/scripts/linux/wrap_stackops")

alias devops='$HOME/.local/bin/uvx --python 3.14 --from "stackops>=8.94" devops'
alias cloud='$HOME/.local/bin/uvx --python 3.14 --from "stackops>=8.94" cloud'
alias agents='$HOME/.local/bin/uvx --python 3.14 --from "stackops>=8.94" agents'
alias fire='$HOME/.local/bin/uvx --python 3.14 --from "stackops>=8.94" fire'
alias croshell='$HOME/.local/bin/uvx --python 3.14 --from "stackops>=8.94" croshell'
alias utils='$HOME/.local/bin/uvx --python 3.14 --from "stackops>=8.94" utils'
alias terminal='$HOME/.local/bin/uvx --python 3.14 --from "stackops>=8.94" terminal'
seek() { "$HOME/.local/bin/uvx" --python 3.14 --from "stackops>=8.94" seek "$@"; }

alias d='wrap_in_shell_script devops'
alias c='wrap_in_shell_script cloud'
alias a='wrap_in_shell_script agents'
alias f='wrap_in_shell_script fire'
alias rr='wrap_in_shell_script croshell'
alias u='wrap_in_shell_script utils'
alias t='wrap_in_shell_script terminal'
alias s='wrap_in_shell_script seek'

echo "stackops command aliases are now defined in this shell session."

d config interactive
