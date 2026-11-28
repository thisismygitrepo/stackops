# Environment and Project Wiring

The environment helpers in `stackops` now live across `stackops.scripts.python.helpers.helpers_utils.python_env` (virtualenv discovery and activation) and `stackops.utils.cloud.defaults` (cloud defaults). They answer two practical questions:

- which virtualenv should this project use?
- what cloud-transfer defaults should commands start from?

---

## What this layer provides

| API | Responsibility |
| --- | --- |
| `find_virtualenv_root(init_path)` | Walks upward from a path and resolves the first project-local `.venv` |
| `build_virtualenv_activation_line(virtualenv_root)` | Builds the platform-specific shell line that activates a virtualenv |
| `CloudConfig` | Typed cloud metadata for keys such as `cloud`, `root`, `rel2home`, `pwd`, `encryption`, `os_specific`, `zip`, `share`, and `overwrite` |
| `read_default_cloud_config()` | Returns the default `CloudConfig` payload used by callers as a baseline |
| `read_default_rclone_remote()` | In `stackops.utils.cloud.default_remote`: returns the `default_rclone_config` value of the StackOps config file, or raises `DefaultRcloneRemoteConfigError` (a `ValueError`) with setup instructions when the file is missing, invalid, or lacks that key |

---

## Discovery model

`find_virtualenv_root(init_path)` treats `init_path` as a file-or-directory input, normalizes file paths to their parent directory, then walks upward through that path and its parents.

At each directory it:

1. Checks for a `.venv` directory inside it.
2. Returns the first match immediately.
3. Continues through parent directories if no `.venv` is present.

The function returns a `Path` when it finds a project-local virtualenv and `None` otherwise. It also prints the resolved path, or that no environment was discovered.

---

## Default cloud payload

`read_default_cloud_config()` returns:

- `cloud`: `mycloud101`
- `root`: `myhome`
- `rel2home`, `os_specific`, `zip`, `share`, `overwrite`: `False`
- `pwd`, `encryption`: `None`

---

## Activation lines

`build_virtualenv_activation_line(virtualenv_root)` returns:

- `. {virtualenv_root}/bin/activate` on Linux and macOS
- `. $HOME/<relative-path>/Scripts/activate.ps1` on Windows

The Windows branch rewrites the expanded virtualenv path to a `$HOME/.../Scripts/activate.ps1` PowerShell source line.
The Windows path must be under the user's home directory because the implementation rewrites it relative to `$HOME`.
Any other platform raises `NotImplementedError`.

---

## Example usage

```python
from pathlib import Path

from stackops.scripts.python.helpers.helpers_utils.python_env import build_virtualenv_activation_line, find_virtualenv_root
from stackops.utils.cloud.defaults import read_default_cloud_config

virtualenv_root = find_virtualenv_root(Path.cwd())
cloud_defaults = read_default_cloud_config()

print(cloud_defaults["root"])

if virtualenv_root is not None:
    print(build_virtualenv_activation_line(virtualenv_root))
```

## Profile helpers

Use `stackops.profile.create_helper.copy_assets_to_machine(which)` when a script needs to install the
packaged `"scripts"` or `"settings"` assets into the StackOps config root. Use `stackops.profile.dotfiles_mapper`
for typed dotfile mapper reads and writes. The profile modules that parse CLI options or apply
machine-local symlink changes are command implementation modules, not general-purpose public APIs.

---

## API reference

::: stackops.utils.cloud.defaults
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Default rclone remote

::: stackops.utils.cloud.default_remote
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Package logger

::: stackops.logger
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Profile creation helpers

::: stackops.profile.create_helper
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Dotfiles mapper

::: stackops.profile.dotfiles_mapper
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Secrets API

`stackops.secrets` is a package with an empty `__init__`, so the API is imported from its submodules. The ones documented here are `search`, `loader`, `models`, and `writer`.

::: stackops.secrets.search
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Secrets file loader

::: stackops.secrets.loader
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Secrets schema types

::: stackops.secrets.models
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Secrets file writer

::: stackops.secrets.writer
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## OneDrive auth

::: stackops.utils.cloud.onedrive.auth
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## OneDrive file operations

::: stackops.utils.cloud.onedrive.file_ops
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Rclone helpers

::: stackops.utils.cloud.rclone
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Rclone wrapper

::: stackops.utils.cloud.rclone_wrapper
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Project root resolution

::: stackops.utils.repos.project
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## StackOps repository helpers

::: stackops.utils.repos.stackops_paths
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## StackOps config schema

::: stackops.utils.schemas.config.config_types
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Multiplexer names

`stackops.utils.schemas.config.multiplexer_types` holds the literal types the config schema uses for its multiplexer settings: `SessionMultiplexer` (`tmux`, `herdr`, `tuios`, `aoe`, `zellij`), `SessionMultiplexerOption` (the same names plus the one-letter forms `t`, `h`, `u`, `e`, `z`), `AgentMultiplexer` (`tuios`, `herdr`, `aoe`), and `AgentStatusBackend` (an `AgentMultiplexer` or `t3`). `SESSION_MULTIPLEXERS` and `AGENT_MULTIPLEXERS` are the same names as tuples.

::: stackops.utils.schemas.config.multiplexer_types
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Repository schema

::: stackops.utils.schemas.repos.repos_types
    options:
      show_root_heading: true
      show_source: false
      members_order: source
