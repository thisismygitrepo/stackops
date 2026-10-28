#!/bin/bash

# Source @ https://raw.githubusercontent.com/thisismygitrepo/stackops/refs/heads/main/src/stackops/scripts/setup/linux/quick_init.sh
# Short @ https://bit.ly/sopsuq

. <( curl -sSL "https://raw.githubusercontent.com/thisismygitrepo/stackops/main/src/stackops/scripts/setup/linux/uv.sh")
uv tool install --upgrade --python 3.14 stackops
devops config copy-assets all
devops config dotfiles sync down --source library --method copy --on-conflict overwrite-default-path --which all
devops config terminal config-shell --shell default
devops software install --group termabc
devops software install --group sysabc
