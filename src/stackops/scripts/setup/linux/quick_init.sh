#!/bin/bash

# Source @ https://raw.githubusercontent.com/thisismygitrepo/stackops/refs/heads/main/src/stackops/scripts/setup/linux/quick_init.sh
# Short @ https://bit.ly/sopsuq
# Usage @ . <(curl -L bit.ly/sopsuq)   # sourced, so the final init lands in the calling bash or zsh shell

. <( curl -sSL "https://raw.githubusercontent.com/thisismygitrepo/stackops/main/src/stackops/scripts/setup/linux/uv.sh")
uv tool install --upgrade --python 3.14 stackops

devops software install --group sysabc
# Homebrew on Apple Silicon lives outside the default PATH
if [ -x /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
fi
# sysabc installed bun, whose rc-file PATH entry only reaches new shells
export PATH="$HOME/.bun/bin:$PATH"

devops config copy-assets all
devops config dotfiles sync down --source library --method copy --on-conflict overwrite-default-path --which all
devops config terminal config-shell --shell default

devops software install --group termabc
source $HOME/.config/stackops/settings/shells/bash_zsh/init.sh
