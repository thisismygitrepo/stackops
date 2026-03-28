# Environment and Project Wiring

Many `machineconfig` integrations start with one question: "what environment should this project run in?" The environment helpers answer that by discovering project-local virtualenvs, optional IPython profiles, and cloud sync metadata from a lightweight convention file.

The core API for that lives in `machineconfig.utils.ve`.

---

## What this layer provides

| API | Responsibility |
| --- | --- |
| `FILE_NAME` | The project config filename used for environment discovery: `.ve.yaml` |
| `CLOUD` | Typed structure for cloud-sync metadata such as cloud name, root, encryption, and sharing flags |
| `VE_YAML` | Typed structure for the overall `.ve.yaml` document |
| `read_default_cloud_config()` | Returns the default `CLOUD` structure used as a baseline |
| `get_ve_path_and_ipython_profile(init_path)` | Walks upward from a path to discover virtualenv and optional IPython profile |
| `get_ve_activate_line(ve_root)` | Builds a platform-appropriate shell activation command |

---

## Discovery model

`get_ve_path_and_ipython_profile()` walks upward through parent directories and looks for two things:

1. A `.ve.yaml` file, which can declare a specific virtualenv path and IPython profile.
2. A `.venv` directory, which acts as a fallback virtualenv location.

The search stops early once both a virtualenv path and an IPython profile have been found.

That makes the API useful for tools that need to "attach" themselves to whatever environment a project already expects, instead of re-deriving that configuration from scratch.

---

## Example `.ve.yaml`

```yaml
specs:
  ve_path: ~/.venvs/my-project
  ipy_profile: default

cloud:
  cloud: mycloud101
  root: myhome
  rel2home: false
  pwd: null
  key: null
  encrypt: false
  os_specific: false
  zip: false
  share: false
  overwrite: false
```

---

## Example usage

```python
from pathlib import Path

from machineconfig.utils.ve import (
    FILE_NAME,
    get_ve_activate_line,
    get_ve_path_and_ipython_profile,
)

project_path = Path.cwd()
ve_path, ipy_profile = get_ve_path_and_ipython_profile(project_path)

print(f"Config file name: {FILE_NAME}")
print(f"Virtualenv: {ve_path}")
print(f"IPython profile: {ipy_profile}")

if ve_path is not None:
    print(get_ve_activate_line(ve_path))
```

---

## Where this shows up in practice

This layer is useful whenever a project wants to:

- keep a machine-local virtualenv path in a checked-in convention file
- discover an IPython startup profile without hard-coding it in every script
- attach cloud-related metadata to the same project-level config
- generate activation commands for local or remote shell sessions

That is why it appears in machine-orchestration, layout generation, and shared helper modules across downstream repos.

---

## API reference

::: machineconfig.utils.ve
    options:
      show_root_heading: true
      show_source: false
      members_order: source
