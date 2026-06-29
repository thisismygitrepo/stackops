# Installer Module

The installer system is split across two layers:

- `stackops.jobs.installer` for packaged install scripts
- `stackops.utils.schemas.installer` for the installer catalog and typed schema
- `stackops.utils.installer_utils` for the runtime engine

This page documents the runtime behavior that the current code exposes.

---

## Core data model

The typed schema lives in `stackops.utils.schemas.installer.installer_types`.

### `InstallerData`

```python
from stackops.utils.schemas.installer.installer_types import InstallerData

installer_data: InstallerData = {
    "appName": "fd",
    "license": "MIT",
    "doc": "A simple, fast and user-friendly alternative to find",
    "repoURL": "https://github.com/sharkdp/fd",
    "categoryLabels": ["search-navigation"],
    "fileNamePattern": {
        "amd64": {
            "linux": "fd-v{version}-x86_64-unknown-linux-musl.tar.gz",
            "windows": "fd-v{version}-x86_64-pc-windows-msvc.zip",
            "darwin": "fd-v{version}-x86_64-apple-darwin.tar.gz",
        },
        "arm64": {
            "linux": "fd-v{version}-aarch64-unknown-linux-musl.tar.gz",
            "windows": None,
            "darwin": "fd-v{version}-aarch64-apple-darwin.tar.gz",
        },
    },
}
```

Fields:

| Field | Meaning |
| --- | --- |
| `appName` | Display name and base executable name |
| `license` | License label stored in the installer catalog |
| `doc` | Description used in interactive selection |
| `repoURL` | `"CMD"` for command / script driven installs, or a GitHub repository URL |
| `categoryLabels` | Searchable category labels used by `devops install --explore` |
| `fileNamePattern` | `arch -> os -> installer value` mapping |

### Other types

| Type | Purpose |
| --- | --- |
| `InstallerDataFiles` | Shape of `installer_data.json` |
| `InstallRequest` | `{version: str | None, update: bool}` |
| `InstallationResult` | Typed union of `skipped`, `same_version`, `updated`, and `failed` results |
| `CPU_ARCHITECTURES` | `"amd64"` or `"arm64"` |
| `OPERATING_SYSTEMS` | `"windows"`, `"linux"`, or `"darwin"` |

Helpers:

- `get_os_name()`
- `get_normalized_arch()`

---

## How installers are resolved

`stackops.utils.installer_utils.installer_runner.get_installers()` loads the catalog from:

- `stackops.utils.schemas.installer.INSTALLER_DATA_PATH_REFERENCE`
- resolved through `stackops.utils.path_reference.get_path_reference_path(...)`

It then filters by:

- current OS
- current architecture
- optional package-group list

Example:

```python
from stackops.utils.installer_utils.installer_runner import get_installers
from stackops.utils.schemas.installer.installer_types import (
    get_normalized_arch,
    get_os_name,
)

installers = get_installers(
    os=get_os_name(),
    arch=get_normalized_arch(),
    which_cats=["termabc"],
)
```

---

## Installation strategies

`Installer._install_from_value()` supports four current strategies.

### 1. Package-manager commands

If the resolved installer value contains a whitespace-separated package-manager token such as `bun`, `npm`, `pip`, `uv`, `winget`, `powershell`, `irm`, `brew`, `curl`, `sudo`, or `cargo`, the installer executes that shell command directly.

This is also the path used for entries whose `repoURL` is `"CMD"` and whose platform value is a raw command string.

### 2. Script installers

If the resolved installer value ends in:

- `.sh`
- `.ps1`
- `.py`

the installer searches the packaged installer assets under `stackops.jobs.installer` and runs the matching script.

Current Python installer scripts are expected to expose:

```python
main(installer_data: InstallerData, version: str | None, update: bool)
```

Extra parameters are allowed only if they are optional.

### 3. Direct binary or archive URLs

If the resolved installer value is an `http://` or `https://` URL, the installer downloads it to `~/tmp_results/tmp_installers`, decompresses supported archives, and then moves the resulting executable or `.deb` package into place.

### 4. GitHub releases

If `repoURL` is a GitHub repository URL, `Installer.get_github_release()` fetches release metadata and matches a release asset against the current platform's `fileNamePattern`.

Current matching behavior includes:

- `{version}` substitution with the resolved tag name
- fallback checks for `v`-prefixed versus unprefixed versions
- hyphen / underscore filename variants before the install fails

### Install request handling

`InstallRequest(version, update)` is resolved against the installer kind before installation:

- installs are skipped when the executable already exists unless `update=True` or `version` is set
- `--version` is accepted for GitHub release installers, script installers, and `winget install ...` commands
- `--update` is accepted for binary URL, GitHub release, script installers, and `winget install ...` commands
- unsupported `version` requests are ignored with a warning; unsupported `update` requests warn and continue

---

## `Installer`

`stackops.utils.installer_utils.installer_class.Installer` is the per-package orchestrator.

### Main methods

| Method | Purpose |
| --- | --- |
| `get_description()` | Builds the interactive display label and includes a `check_tool_exists()` status mark |
| `install(version)` | Installs one tool without the typed `InstallRequest` wrapper |
| `install_requested(install_request)` | Installs one tool using `InstallRequest` |
| `install_robust(install_request)` | Returns a typed `InstallationResult` instead of raising install failures to the caller |
| `binary_download(version)` | Downloads and extracts the selected asset without final installation |
| `get_github_release(repo_url, version)` | Returns the selected asset URL and resolved version tag |

### Example

```python
from stackops.utils.installer_utils.installer_class import Installer
from stackops.utils.schemas.installer.installer_types import InstallRequest

installer = Installer(installer_data)
result = installer.install_robust(
    install_request=InstallRequest(version=None, update=False),
)

print(result["kind"])
```

`install_robust()` currently returns one of these result shapes:

- `{"kind": "skipped", ...}`
- `{"kind": "same_version", ...}`
- `{"kind": "updated", ...}`
- `{"kind": "failed", ...}`

---

## CLI-style entrypoints

These helpers live in `stackops.utils.installer_utils.installer_cli`.

### `main_installer_cli(...)`

```python
from stackops.utils.installer_utils.installer_cli import main_installer_cli

main_installer_cli(
    which="fd,bat,rg",
    group=False,
    interactive=False,
    explore=False,
    update=False,
    version=None,
)
```

Parameters:

| Parameter | Meaning |
| --- | --- |
| `which` | Comma-separated app names, group names, or URLs |
| `group` | Treat `which` as package-group names |
| `interactive` | Launch interactive selection instead of parsing `which` |
| `explore` | Explore installer categoryLabels before installing |
| `update` | Allow reinstall or upgrade when supported |
| `version` | Request a specific version or tag when supported |

### Other entrypoints

| Helper | Purpose |
| --- | --- |
| `install_interactively(install_request)` | Shows package groups plus installers, with JSON previews when `tv` is available |
| `install_group(package_group, install_request)` | Resolves a named package group and installs every matching catalog entry |
| `install_clis(clis_names, install_request)` | Installs explicit catalog names, aliases, GitHub URLs, or direct binary URLs |
| `install_if_missing(which, binary_name, verbose)` | Convenience guard that returns `True` if the tool exists or becomes installable |

Current CLI aliases:

- `agy` -> `antigravity`

Interactive mode currently:

- lists package groups first, prefixed with `📦`
- lists installer options using `Installer.get_description()`
- uses `choose_from_dict_with_preview()` when `tv` exists
- falls back to `choose_from_options()` otherwise

---

## Package groups

The installer runtime consumes the groups defined in `stackops.utils.schemas.installer.package_groups.PACKAGE_GROUP2NAMES`.

Current group names:

- `sysabc`
- `shell`
- `search`
- `sys-monitor`
- `code-analysis`
- `termabc`
- `dev`
- `dev-utils`
- `eye`
- `agents`
- `terminal`
- `browsers`
- `editors`
- `db-all`
- `db-cli`
- `db-desktop`
- `db-web`
- `db-tui`
- `media`
- `gui`
- `nw`
- `file-sharing`
- `productivity`

Example:

```python
from stackops.utils.schemas.installer.package_groups import PACKAGE_GROUP2NAMES

print(PACKAGE_GROUP2NAMES["agents"])
```

---

## Bulk installation

`stackops.utils.installer_utils.installer_runner.install_bulk()` is the multi-package entrypoint.

```python
from stackops.utils.installer_utils.installer_runner import install_bulk
from stackops.utils.schemas.installer.installer_types import InstallRequest

install_bulk(
    installers_data=installers,
    install_request=InstallRequest(version=None, update=False),
    safe=False,
    jobs=10,
    fresh=False,
)
```

Current behavior:

- the first installer runs serially
- the remaining installers run through a stdlib process pool
- `fresh=True` clears the version cache first
- `safe` is accepted but currently has no behavior
- a Rich summary is rendered after the batch finishes

---

## Direct URL installers

Two URL-oriented helpers are exposed separately:

```python
from stackops.utils.installer_utils.install_from_url import (
    install_from_binary_url,
    install_from_github_url,
)
```

### `install_from_github_url(github_url)`

- fetches the latest release
- lets the user choose a release asset interactively
- downloads, extracts, and installs it
- records the resolved version in the install-version cache when a tool name can be derived from the selected asset or repository

### `install_from_binary_url(binary_url)`

- downloads a binary or archive directly
- extracts and installs it
- records `"latest"` in the install-version cache only when a tool name can be derived during finalization

---

## Version tracking and install paths

Current constants come from `stackops.utils.source_of_truth`:

| Constant | Current path |
| --- | --- |
| `INSTALL_VERSION_ROOT` | `~/.config/stackops/cli_tools_installers/versions` |
| `INSTALL_TMP_DIR` | `~/tmp_results/tmp_installers` |
| `LINUX_INSTALL_PATH` | `~/.local/bin` |
| `WINDOWS_INSTALL_PATH` | `~/AppData/Local/Microsoft/WindowsApps` |

Each installed tool gets a version marker file under `INSTALL_VERSION_ROOT`.

---

## Security checks

Security and reporting helpers live under `stackops.jobs.installer.checks.*`. They are part of the installer subsystem, but they are not on the main install path described above. Use them when you need auditing or reporting around already installed tools rather than installation itself.

---

## API reference

## Installer schema

::: stackops.utils.schemas.installer.installer_types
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Package groups

::: stackops.utils.schemas.installer.package_groups
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Installer class

::: stackops.utils.installer_utils.installer_class
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Installer runner

::: stackops.utils.installer_utils.installer_runner
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Install request logic

::: stackops.utils.installer_utils.install_request_logic
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Installer helper utilities

::: stackops.utils.installer_utils.installer_helper
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Installer locator utilities

::: stackops.utils.installer_utils.installer_locator_utils
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## GitHub release scraper

::: stackops.utils.installer_utils.github_release_scraper
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## GitHub release bulk helpers

::: stackops.utils.installer_utils.github_release_bulk
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Install from URL helpers

::: stackops.utils.installer_utils.install_from_url
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Installer CLI helpers

::: stackops.utils.installer_utils.installer_cli
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Installer Python script main protocol

::: stackops.utils.installer_utils.installer_main_protocol
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Installer explore helpers

::: stackops.utils.installer_utils.installer_explore
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Installer summary helpers

::: stackops.utils.installer_utils.installer_summary
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Offline installer entrypoint

::: stackops.utils.installer_utils.installer_offline
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Offline installer models

::: stackops.utils.installer_utils.installer_offline_models
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Offline installer constants

::: stackops.utils.installer_utils.installer_offline_constants
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Offline installer publish helpers

::: stackops.utils.installer_utils.installer_offline_publish
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Offline installer render helpers

::: stackops.utils.installer_utils.installer_offline_render
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Offline installer script helpers

::: stackops.utils.installer_utils.installer_offline_scripts
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Offline installer steps

::: stackops.utils.installer_utils.installer_offline_steps
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Offline installer uv helpers

::: stackops.utils.installer_utils.installer_offline_uv
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Installation check utilities

::: stackops.jobs.installer.checks.install_utils
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Installation checks

::: stackops.jobs.installer.checks.check_installations
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Security CLI helpers

::: stackops.jobs.installer.checks.security_cli
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Security helper utilities

::: stackops.jobs.installer.checks.security_helper
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Security report utilities

::: stackops.jobs.installer.checks.report_utils
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## VirusTotal utilities

::: stackops.jobs.installer.checks.vt_utils
    options:
      show_root_heading: true
      show_source: false
      members_order: source
