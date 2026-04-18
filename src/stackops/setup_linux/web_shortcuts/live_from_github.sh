#!/bin/bash

# @ https://bit.ly/cfglg

. <( curl -sSL "https://raw.githubusercontent.com/thisismygitrepo/stackops/main/src/stackops/setup_linux/uv.sh")
. <( curl -sSL "https://raw.githubusercontent.com/thisismygitrepo/stackops/main/src/stackops/scripts/linux/wrap_stackops")

alias stackops='$HOME/.local/bin/uvx --python 3.14 --from "git+https://github.com/thisismygitrepo/stackops" stackops'

alias d='wrap_in_shell_script stackops devops'
alias c='wrap_in_shell_script stackops cloud'
alias a='wrap_in_shell_script stackops agents'
alias fx='wrap_in_shell_script stackops cloud ftpx'
alias f='wrap_in_shell_script stackops fire'
alias rr='wrap_in_shell_script stackops croshell'
alias u='wrap_in_shell_script stackops utils'
alias t='wrap_in_shell_script stackops terminal'
seek() { "$HOME/.local/bin/uvx" --python 3.14 --from "git+https://github.com/thisismygitrepo/stackops" seek "$@"; }
alias s='wrap_in_shell_script seek'

alias devops='stackops devops'
alias cloud='stackops cloud'
alias agents='stackops agents'
alias ftpx='stackops cloud ftpx'
alias fire='stackops fire'
alias croshell='stackops croshell'
alias utils='stackops utils'
alias terminal='stackops terminal'


echo "stackops command aliases are now defined in this shell session."
