# Environment and Project Wiring

The environment helpers in `stackops` now live across `stackops.utils.python_env` and `stackops.utils.cloud_defaults`. They answer two practical questions:

- which virtualenv should this project use?
- what cloud-transfer defaults should commands start from?

---

## What this layer provides

| API | Responsibility |
| --- | --- |
| `find_virtualenv_root(init_path)` | Walks upward from a path and resolves the first project-local `.venv` |
| `build_virtualenv_activation_line(virtualenv_root)` | Builds the platform-specific shell line that activates a virtualenv |
| `CloudConfig` | Typed cloud metadata for keys such as `cloud`, `root`, `encrypt`, `encryption`, `share`, and `overwrite` |
| `read_default_cloud_config()` | Returns the default `CloudConfig` payload used by callers as a baseline |

---

## Discovery model

`find_virtualenv_root(init_path)` treats `init_path` as a file-or-directory input, normalizes file paths to their parent directory, then walks upward through that path and its parents.

At each directory it:

1. Checks for a sibling `.venv` directory.
2. Returns the first match immediately.
3. Continues through parent directories if no `.venv` is present.

The function returns a `Path` when it finds a project-local virtualenv and `None` otherwise. It also prints the resolved path, or that no environment was discovered.

---

## Default cloud payload

`read_default_cloud_config()` returns:

- `cloud`: `mycloud101`
- `root`: `myhome`
- `rel2home`, `encrypt`, `os_specific`, `zip`, `share`, `overwrite`: `False`
- `pwd`, `encryption`: `None`

---

## Activation lines

`build_virtualenv_activation_line(virtualenv_root)` returns:

- `. {virtualenv_root}/bin/activate` on Linux and macOS
- `. $HOME/<relative-path>/Scripts/activate.ps1` on Windows

The Windows branch rewrites the expanded virtualenv path to a `$HOME/.../Scripts/activate.ps1` PowerShell source line.
The Windows path must be under the user's home directory because the implementation rewrites it relative to `$HOME`.

---

## Example usage

```python
from pathlib import Path

from stackops.utils.cloud_defaults import read_default_cloud_config
from stackops.utils.python_env import build_virtualenv_activation_line, find_virtualenv_root

project_path = Path.cwd()
virtualenv_root = find_virtualenv_root(project_path)
cloud_defaults = read_default_cloud_config()

print(virtualenv_root)
print(cloud_defaults["root"])

if virtualenv_root is not None:
    print(build_virtualenv_activation_line(virtualenv_root))
```

---

## API reference

::: stackops.utils.python_env
    options:
      show_root_heading: true
      show_source: false
      members_order: source

::: stackops.utils.cloud_defaults
    options:
      show_root_heading: true
      show_source: false
      members_order: source
