# 🗜 StackOps

StackOps is a cross-platform CLI for bootstrapping and maintaining a development machine. It groups package installation, config syncing, data syncing, session automation, and helper utilities into one install.

See the [online docs](https://thisismygitrepo.github.io/stackops/) for full usage and reference material.

## Install with `uv`

### Linux / macOS

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install --upgrade --python 3.14 stackops
```

### Windows

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
uv tool install --upgrade --python 3.14 stackops
```


## Quick init

```shell
devops install --group sysabc  # Install (if missing) package manager (apt, brew, winget)
devops config copy-assets all  # copy config files to machine
devops config sync down --sensitivity public --method copy --on-conflict overwrite-default-path --which all  # link config files
devops config terminal config-shell --which default  # add alias to shell
devops install --group termabc  # install the basic terminal cli's
```

## Author

Alex Al-Saffar. [email](mailto:programmer@usa.com)

## Contributor

Ruby Chan. [email](mailto:ruby.chan@sa.gov.au)
