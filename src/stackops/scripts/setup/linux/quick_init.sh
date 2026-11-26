#!/bin/bash

# Source @ https://raw.githubusercontent.com/thisismygitrepo/stackops/refs/heads/main/src/stackops/scripts/setup/linux/quick_init.sh
# Short @ https://bit.ly/sopsuq
# Usage @ . <(curl -L bit.ly/sopsuq)   # sourced, so the final init lands in the calling bash or zsh shell

. <( curl -sSL "https://raw.githubusercontent.com/thisismygitrepo/stackops/main/src/stackops/scripts/setup/linux/uv.sh")
uv tool install --upgrade --python 3.14 stackops

devops config copy-assets all
devops config dotfiles sync down --source library --method copy --on-conflict overwrite-default-path --which all
devops config terminal config-shell --shell default

# sysabc installs Homebrew on Apple Silicon outside the default PATH; it is named now so the installers that follow sysabc find it
if [ "$(uname)" = "Darwin" ]; then
    export PATH="/opt/homebrew/bin:$PATH"
fi
# one batch: termabc's downloads run while sysabc installs the base packages
devops software install --group sysabc,termabc
if [ -x /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
fi
# sysabc installed bun, whose rc-file PATH entry only reaches new shells.
# This stays after the install: bun's installer skips that rc-file entry when bun is already on PATH.
export PATH="$HOME/.bun/bin:$PATH"
source $HOME/.config/stackops/settings/shells/bash_zsh/init.sh
