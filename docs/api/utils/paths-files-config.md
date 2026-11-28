# Paths, Files, and Config

This part of the utility API is the filesystem and configuration layer that current StackOps code actually uses. The relevant modules today are:

| Module | Role |
| --- | --- |
| `stackops.utils.path_core` | Core path operations such as copy, move, delete, symlink, download, temp-path creation, and safe naming |
| `stackops.utils.path_reference` | Resolve package-relative asset paths from imported modules |
| `stackops.utils.io` | JSON / INI / pickle IO plus GPG-backed file encryption helpers |
| `stackops.utils.files.read` | Suffix-dispatched readers such as `read_json()`, `read_yaml()`, and `read_toml()` |

---

## `path_core`

`stackops.utils.path_core` is the current low-level path toolbox.

Key functions:

| Function | Current behavior |
| --- | --- |
| `resolve()` | Resolve a path with optional non-strict fallback |
| `validate_name()` | Sanitize arbitrary strings for filenames |
| `timestamp()` | Create filename-safe timestamp strings |
| `collapseuser()` | Rewrite a home-prefixed absolute path back to `~` |
| `delete_path()` | Delete a file, symlink, or directory tree |
| `with_name()` | Compute or perform a rename |
| `move()` | Move a file or directory, optionally by `folder`, `name`, or explicit `path` |
| `copy()` | Copy files or directories, with overwrite and `content=True` support |
| `symlink_to()` | Create a symlink, with Windows elevation handling when needed |
| `download()` | Download a URL to a local file, inferring the output filename when possible |
| `tmp()`, `tmpdir()`, `tmpfile()` | Create temp paths under `~/tmp_results` |

Two behaviors worth knowing:

- `copy(..., content=True)` and `move(..., content=True)` act on the children of a directory instead of the directory root itself
- `download()` tries `Content-Disposition`, then the final URL, then the original URL before falling back to a sanitized filename

---

## `path_reference`

`stackops.utils.path_reference` is the small bridge between Python modules and package data files.

Use it when a helper module stores shell scripts or other assets next to its Python file:

- `get_path_reference_path(module, path_reference)` returns the absolute path
- `get_path_reference_library_relative_path(module, path_reference)` returns the path relative to `LIBRARY_ROOT`

This is the mechanism used by the current `seek` text-search helpers to load platform-specific shell scripts.

---

## `io`

`stackops.utils.io` covers the serialization and encryption helpers used by the current codebase.

Main helpers:

| Function or class | Purpose |
| --- | --- |
| `save_json()` | Persist JSON (the matching `read_json()` lives in `stackops.utils.files.read`) |
| `save_ini()` / `read_ini()` | Persist and read INI files |
| `save_pickle()` / `from_pickle()` | Persist and restore Python objects |
| `encrypt_file_symmetric()` / `decrypt_file_symmetric()` | GPG symmetric encryption using loopback passphrase mode |
| `encrypt_file_asymmetric()` / `decrypt_file_asymmetric()` | GPG public-key encryption and decryption of files |
| `encrypt_bytes_asymmetric()` / `decrypt_bytes_asymmetric()` | GPG public-key encryption and decryption of in-memory bytes |
| `GpgCommandError` | Rich error wrapper for failed GPG subprocess calls |

Current GPG behavior:

- `build_gpg_environment()` populates `GPG_TTY` when possible
- symmetric helpers stream the password through stdin with `--pinentry-mode loopback`
- `encrypt_file_asymmetric(file_path, recipient=...)` passes `--recipient <recipient>`, or `--default-recipient-self` when `recipient` is `None`; `encrypt_bytes_asymmetric()` always uses `--default-recipient-self`
- file helpers write next to the source: encryption appends `.gpg`, decryption strips it (or prefixes `decrypted_` when the name has no `.gpg` suffix)
- `GpgCommandError` includes the command, exit code, stdout, stderr, and a tailored hint when it can infer one

---

## Example usage

```python
from pathlib import Path

from stackops.utils.io import read_ini, save_json
from stackops.utils.path_core import tmpfile, validate_name

target_path = tmpfile(name=validate_name("example config"), suffix=".json")
save_json({"workers": 8, "queue": "jobs"}, target_path, indent=2)

print(target_path)
print(read_ini(Path("settings.ini")) if Path("settings.ini").exists() else "no ini file")
```

---

## API reference

## Path Core

::: stackops.utils.path_core
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## File compression

::: stackops.utils.files.compression
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Path Reference

::: stackops.utils.path_reference
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Source of truth

::: stackops.utils.source_of_truth
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## IO

::: stackops.utils.io
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Encryption mode helpers

::: stackops.utils.cloud.encryption
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Terminal header and logo

::: stackops.utils.files.headers
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## ASCII art helpers

`stackops.utils.files.ascii_art` is what `print_logo()` above draws with. `get_art()` renders a comment through `figlet` and `boxes`, or through `cowsay`; `font_box_color()`, `character_color()` (Windows only), and `character_or_box_color()` (Linux and macOS only) print a logo coloured by `lolcatjs`. Every function shells out to those tools, so they have to be installed.

::: stackops.utils.files.ascii_art
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Notebook helpers

::: stackops.utils.files.notebook
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Archive decompression

::: stackops.utils.files.ouch.decompress
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## File reading helpers

::: stackops.utils.files.read
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## YAML schema helpers

::: stackops.utils.schemas.yaml_schema
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## YAML document text

`yaml_document_text(document)` dumps a mapping as the YAML text StackOps writes to its own files: keys in insertion order, block style, list items indented under their key, no anchors or aliases, no line wrapping, and Unicode kept as written.

::: stackops.utils.schemas.yaml_document
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## JSON schema document text

`json_schema_document_text(content, schema_reference)` is the JSON counterpart of `yaml_schema_document_text()`. It returns the JSON text with its top-level `"$schema"` set to `schema_reference`: an existing string value is replaced, and a missing key is inserted as the first one. `//` and `/* */` comments are tolerated, and text that does not start with an object is returned unchanged.

::: stackops.utils.schemas.json_schema
    options:
      show_root_heading: true
      show_source: false
      members_order: source
