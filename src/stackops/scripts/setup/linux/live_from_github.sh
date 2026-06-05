#!/usr/bin/env bash

# Bootstrap stackops from the current GitHub main branch into this shell session.

. <(curl -sSL "https://raw.githubusercontent.com/thisismygitrepo/stackops/main/src/stackops/scripts/setup/linux/uv.sh")
. <(curl -sSL "https://raw.githubusercontent.com/thisismygitrepo/stackops/main/src/stackops/scripts/linux/wrap_stackops")

STACKOPS_FROM="git+https://github.com/thisismygitrepo/stackops"

_stackops_uvx() {
    "$HOME/.local/bin/uvx" --python 3.14 --from "$STACKOPS_FROM" "$@"
}

stackops() { _stackops_uvx stackops "$@"; }
devops() { _stackops_uvx devops "$@"; }
cloud() { _stackops_uvx cloud "$@"; }
agents() { _stackops_uvx agents "$@"; }
fire() { _stackops_uvx fire "$@"; }
preview() { _stackops_uvx preview "$@"; }
utils() { _stackops_uvx utils "$@"; }
terminal() { _stackops_uvx terminal "$@"; }
seek() { _stackops_uvx seek "$@"; }

d() { wrap_in_shell_script devops "$@"; }
c() { wrap_in_shell_script cloud "$@"; }
a() { wrap_in_shell_script agents "$@"; }
f() { wrap_in_shell_script fire "$@"; }
p() { wrap_in_shell_script preview "$@"; }
u() { wrap_in_shell_script utils "$@"; }
t() { wrap_in_shell_script terminal "$@"; }
s() { wrap_in_shell_script seek "$@"; }

echo "stackops GitHub command functions are now defined in this shell session."

devops config interactive
