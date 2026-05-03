#!/bin/bash

# https://bit.ly/sopsu

. <( curl -sSL "https://raw.githubusercontent.com/thisismygitrepo/stackops/main/src/stackops/scripts/setup/linux/uv.sh")
. <( curl -sSL "https://raw.githubusercontent.com/thisismygitrepo/stackops/main/src/stackops/scripts/linux/wrap_stackops")

# live from github version
# alias stackops='$HOME/.local/bin/uvx --python 3.14 --from "git+https://github.com/thisismygitrepo/stackops" stackops'

alias devops='$HOME/.local/bin/uvx --python 3.14 --from "stackops>=8.97" devops'
alias cloud='$HOME/.local/bin/uvx --python 3.14 --from "stackops>=8.97" cloud'
alias agents='$HOME/.local/bin/uvx --python 3.14 --from "stackops>=8.97" agents'
alias fire='$HOME/.local/bin/uvx --python 3.14 --from "stackops>=8.97" fire'
alias croshell='$HOME/.local/bin/uvx --python 3.14 --from "stackops>=8.97" croshell'
alias utils='$HOME/.local/bin/uvx --python 3.14 --from "stackops>=8.97" utils'
alias terminal='$HOME/.local/bin/uvx --python 3.14 --from "stackops>=8.97" terminal'
seek() { "$HOME/.local/bin/uvx" --python 3.14 --from "stackops>=8.97" seek "$@"; }

alias d='wrap_in_shell_script devops'
alias c='wrap_in_shell_script cloud'
alias a='wrap_in_shell_script agents'
alias f='wrap_in_shell_script fire'
alias rr='wrap_in_shell_script croshell'
alias u='wrap_in_shell_script utils'
alias t='wrap_in_shell_script terminal'
alias s='wrap_in_shell_script seek'

echo "stackops command aliases are now defined in this shell session."

devops config interactive
