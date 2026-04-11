#!/bin/bash
. <( curl -sSL "https://raw.githubusercontent.com/thisismygitrepo/machineconfig/main/src/machineconfig/setup_linux/uv.sh")
. <( curl -sSL "https://raw.githubusercontent.com/thisismygitrepo/machineconfig/main/src/machineconfig/scripts/linux/wrap_mcfg")

alias devops='$HOME/.local/bin/uvx --python 3.14 --from "machineconfig>=8.91" devops'
alias cloud='$HOME/.local/bin/uvx --python 3.14 --from "machineconfig>=8.91" cloud'
alias agents='$HOME/.local/bin/uvx --python 3.14 --from "machineconfig>=8.91" agents'
alias fire='$HOME/.local/bin/uvx --python 3.14 --from "machineconfig>=8.91" fire'
alias croshell='$HOME/.local/bin/uvx --python 3.14 --from "machineconfig>=8.91" croshell'
alias utils='$HOME/.local/bin/uvx --python 3.14 --from "machineconfig>=8.91" utils'
alias terminal='$HOME/.local/bin/uvx --python 3.14 --from "machineconfig>=8.91" terminal'
seek() { "$HOME/.local/bin/uvx" --python 3.14 --from "machineconfig>=8.91" seek "$@"; }

alias d='wrap_in_shell_script devops'
alias c='wrap_in_shell_script cloud'
alias a='wrap_in_shell_script agents'
alias f='wrap_in_shell_script fire'
alias rr='wrap_in_shell_script croshell'
alias u='wrap_in_shell_script utils'
alias t='wrap_in_shell_script terminal'
alias s='wrap_in_shell_script seek'

echo "mcfg command aliases are now defined in this shell session."

d self config
