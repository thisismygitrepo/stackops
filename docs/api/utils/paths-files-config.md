# Paths, Files, and Config

The paths-and-files layer is where `machineconfig` behaves most like an "ops utility belt". It combines a path abstraction used heavily in existing integrations with small serialization helpers for JSON, INI, pickle, and encrypted blobs.

The most important modules here are `machineconfig.utils.path_extended` and `machineconfig.utils.io`.

---

## PathExtended at a glance

`PathExtended` is a `pathlib.Path` subclass with many convenience methods for path mutation and file operations. It remains common in existing `machineconfig` consumers, especially where scripts need terse, chainable filesystem operations.

### Common operations

| Method | What it does |
| --- | --- |
| `delete(sure, verbose)` | Deletes a file or directory after an explicit confirmation flag |
| `move(...)` | Moves a file or directory, with overwrite and content-only options |
| `copy(...)` | Copies files or directories and can return either the destination or the original object |
| `download(...)` | Downloads a URL-like path to a destination folder |
| `append(...)` | Produces a new filename by appending a suffix or generated token |
| `with_name(..., inplace=...)` | Renames or retitles a path with optional in-place mutation |

### Supporting helpers

| Helper | Purpose |
| --- | --- |
| `validate_name()` | Sanitizes arbitrary strings for filenames |
| `timestamp()` | Produces timestamp strings that are safe for filenames |

!!! note
    `PathExtended` is still worth knowing if you work in the existing codebase or in downstream repos. For brand-new code you can mix it with regular `pathlib.Path` when that keeps things simpler.

---

## Serialization helpers

`machineconfig.utils.io` handles the formats that show up repeatedly in `machineconfig` workflows:

| Function | Purpose |
| --- | --- |
| `save_json()` / `read_json()` | Persist and read structured JSON data |
| `save_ini()` / `read_ini()` | Work with INI-style configuration files |
| `save_pickle()` / `from_pickle()` | Store and restore Python objects |
| `remove_c_style_comments()` | Strip `//` and `/* */` comments before parsing |
| `encrypt()` / `decrypt()` | Encrypt and decrypt bytes with a key or password |

These functions are used for config files, remote-job metadata, installer data, cached artifacts, and lightweight credentials handling.

---

## Example usage

```python
from pathlib import Path

from machineconfig.utils.accessories import get_repo_root
from machineconfig.utils.io import read_ini, read_json, save_ini, save_json

config_path = save_json(
    {"workers": 8, "queue": "jobs"},
    Path("tmp/config.json"),
    indent=2,
)
config = read_json(config_path)

ini_path = save_ini(
    "tmp/redis.ini",
    {"default": {"host": "localhost", "port": 6379}},
)
redis_ini = read_ini(Path(ini_path))

print(config)
print(redis_ini["default"]["host"])
print(get_repo_root(Path.cwd()))
```

---

## How to think about this layer

If `ve.py` helps a tool discover *where* to run, the path and IO helpers help it decide *what files* to read, write, copy, rename, encrypt, or ship around. That is why this layer appears in:

- wallet and credential readers
- source-of-truth config loaders
- remote job metadata files
- lightweight cache serialization
- script-generation flows that create temporary artifacts

---

## IO API reference

::: machineconfig.utils.io
    options:
      show_root_heading: true
      show_source: false
      members_order: source
