#!/bin/bash

# https://bit.ly/sopsuq

. <( curl -sSL "https://raw.githubusercontent.com/thisismygitrepo/stackops/main/src/stackops/scripts/setup/linux/uv.sh")
uv tool install --upgrade --python 3.14 stackops
devops install --group sysabc
devops config copy-assets all
devops config sync down --sensitivity public --method copy --on-conflict overwrite-default-path --which all
devops config terminal config-shell --which default
devops install --group termabc
wt  # start Windows Terminal to pick up config changes

