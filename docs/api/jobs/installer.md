# Installer Module

The installer system is split across three layers:

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
| `categoryLabels` | Searchable category labels used by `devops software explore`; each must be one of `INSTALLER_CATEGORY_LABELS` |
| `fileNamePattern` | `arch -> os -> installer value` mapping |
| `lastCommitDate`, `lastCommitDateCheckDate`, `comment` | Optional strings; the two dates are refreshed by `devops software update-attrs` |

Linux installer values may be portable strings or native mappings with the exact keys `apk`, `apt`, `dnf`, and `pacman`, plus an optional `omarchy` key that replaces the `pacman` value on Omarchy. A `null` value marks an installer as unsupported by that package manager. A portable string that contains a native package-manager command or a native package file (`.apk`, `.deb`, `.rpm`, `.pkg.tar.zst`) is rejected with `ValueError`; it belongs in the mapping.

### Other types

| Type | Purpose |
| --- | --- |
| `InstallerDataFiles` | Shape of `installer_data.yaml`: `version` and `installers` |
| `InstallRequest` | Frozen dataclass: `version: str | None`, `update: bool`, `user_scripts_root: Path | None` (all required) |
| `InstallerDataSource` | `"library"`, `"user"`, or `"all"`, with the short forms `"l"`, `"u"`, and `"a"` |
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

- the given OS
- the given architecture
- optional package-group list

With a group list, the result follows the order in which the groups list their apps rather than catalog order. `get_installers()` always reads the library catalog; `get_installers_from_source(source, user_path, os, arch, which_cats)` applies the same filter to the `library`, `user`, or `all` source, where `all` lets user entries override library entries with the same name.

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

If the resolved installer value contains a whitespace-separated package-manager token such as `apk`, `apt`, `dnf`, `pacman`, `bun`, `npm`, `pip`, `uv`, `winget`, `brew`, or `cargo`, the installer executes that shell command directly.

This is also the path used for entries whose `repoURL` is `"CMD"` and whose platform value is a raw command string. A `"CMD"` value that matches none of the first three strategies raises `NotImplementedError`.

### 2. Script installers

If the resolved installer value ends in:

- `.sh`
- `.ps1`
- `.py`

the installer searches (recursively, by file name) the packaged installer assets under `stackops.jobs.installer` and, unless `--source library` is used, the `installer_scripts/` directory next to the user catalog (`~/dotfiles/stackops/config/installer_scripts/` by default, or beside the `--custom-path` catalog). The resolved directory travels as `InstallRequest.user_scripts_root`. Exactly one match across both roots is required; a name present in both is an error, so user scripts that replace a library script need a distinct file name. `devops software validate` applies the same resolution to every script reference in the user catalog.

Python installer scripts run in-process inside the stackops tool environment, so they can import `stackops` and its dependencies but cannot declare their own.

Current Python installer scripts are expected to expose:

```python
main(installer_data: InstallerData, version: str | None, update: bool)
```

Extra parameters are allowed only if they are optional.

### 3. Direct binary or archive URLs

If the resolved installer value is an `http://` or `https://` URL, the installer downloads it to `~/tmp_results/tmp_installers`, decompresses supported archives, and then installs the resulting executable, native `.apk`, `.deb`, `.rpm`, or `.pkg.tar.zst` package, Windows `.msi` package, or macOS `.dmg` application bundle.

### 4. GitHub releases

If `repoURL` is a GitHub repository URL, `Installer.get_github_release()` fetches release metadata and matches a release asset against the current platform's `fileNamePattern`.

Current matching behavior includes:

- `{version}` substitution with the resolved tag name
- fallback checks for `v`-prefixed versus unprefixed versions
- hyphen / underscore filename variants before the install fails

### Install request handling

`InstallRequest(version, update, user_scripts_root)` is resolved against the installer kind before installation:

- installs are skipped when the executable already exists unless `update=True` or `version` is set
- `--version` is accepted for GitHub release installers, script installers, and `winget install ...` commands
- `--update` is accepted for binary URL, GitHub release, script installers, `winget install ...` commands, and `uv tool install ...` commands (which gain `--upgrade`)
- unsupported `version` requests are ignored with a warning; unsupported `update` requests warn and continue

---

## `Installer`

`stackops.utils.installer_utils.installer_class.Installer` is the per-package orchestrator.

### Main methods

| Method | Purpose |
| --- | --- |
| `get_exe_name()` | Derives the executable name from `appName` (lowercased, spaces removed) and applies known aliases such as `antigravity` -> `agy` |
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
    install_request=InstallRequest(version=None, update=False, user_scripts_root=None),
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
    update=False,
    version=None,
    source="all",
    path=None,
)
```

Parameters:

| Parameter | Meaning |
| --- | --- |
| `which` | Comma-separated app names, group names, or URLs |
| `group` | Treat `which` as package-group names |
| `interactive` | Launch interactive selection instead of parsing `which` |
| `update` | Allow reinstall or upgrade when supported |
| `version` | Request a specific version or tag when supported |
| `source` | Catalog to read: `library`, `user`, or `all` (the default); with `all`, user entries override library entries of the same name |
| `path` | Another user catalog file (the `--custom-path` option); not valid with `source="library"` |

### Other entrypoints

| Helper | Purpose |
| --- | --- |
| `install_interactively(install_request, source, user_path)` | Shows package groups plus installers, with rendered text previews when `tv` is available; needs an interactive terminal |
| `install_groups(package_groups, install_request, source, user_path)` | Resolves the named package groups and installs every matching catalog entry as one batch |
| `install_clis(clis_names, install_request, source, user_path)` | Installs explicit catalog names, aliases, GitHub URLs, or direct binary URLs, and returns the `InstallationResult` list for the catalog installs; an unknown name raises `typer.BadParameter` with close matches |
| `install_if_missing(which, binary_name, verbose)` | Convenience guard that returns `True` if the tool already exists or was installed from the library catalog and is now on `PATH` |
| `check_installations(which, group)` | Prints a table showing which of the named executables are installed; with `group=True`, `which` names one check group (currently only `agents`) |

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

`stackops.utils.installer_utils.installer_bulk_runner.install_bulk()` is the multi-package entrypoint behind `devops software install --group <name>`.

```python
from stackops.utils.installer_utils.installer_bulk_runner import install_bulk
from stackops.utils.schemas.installer.installer_types import InstallRequest

install_bulk(
    installers_data=installers,
    install_request=InstallRequest(version=None, update=False, user_scripts_root=None),
    batch_label="termabc",
)
```

Current behavior:

- already-installed apps are skipped up front and listed once, unless `update` or `version` is set
- every other installer runs in its own process, up to 20 at a time, with its output captured in `~/tmp_results/installer_logs/<timestamp>_<batch_label>/<exe>.log`
- installers that drive a system package manager (`apt`, `dnf`, `pacman`, `apk`, `winget`, `brew`, `choco`, `snap`, `msiexec`, `.apk`/`.deb`/`.rpm`/`.pkg.tar.zst`/`.msi`/`.dmg` files) and script installers other than the download-only `nerdfont.py` run one at a time, so they never contend for the package-manager lock; one that prints a `::system-ready::` line lets the next start while it finishes
- when the batch contains `sysabc`, only installers that just download a release start alongside it: system installers and scripts wait for its system packages, and the remaining command installers wait until it is done
- when any of those may call `sudo`, the password is requested once before the batch starts and the credentials are kept alive; if that is not possible the batch continues and the installers that need `sudo` fail on their own
- the terminal shows one line per finished app plus a live progress bar with the latest log line of each running installer; an installer that prints `::step::` lines gets each step listed with its duration
- the closing summary reports counts per outcome, wall time versus summed install time, the slowest installers, and a log excerpt for each of the first five failures

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
- writes no version marker, because a bare URL gives it no repository or asset name to derive a tool name from

---

## Uninstalling

`stackops.utils.installer_utils.installer_removal.remove_installed_binary(exe_name, installer_data, show_output)` is the function behind `devops software uninstall`. It returns `BinaryRemoved(path, command)` when the app was removed and `BinaryKept(path, problem)` when it was left in place, including when it is not installed at all.

Current behavior:

- a non-empty program file that sits directly in the StackOps install folder (`WINDOWS_INSTALL_PATH` on Windows, `LINUX_INSTALL_PATH` elsewhere) and is not a symlink is deleted
- a symlink in that folder, or a program found only elsewhere on `PATH`, belongs to another installer; it is removed only when `installer_uninstall_command.derive_uninstall_command(install_command)` can turn the catalog's install command for this platform into an uninstall command, and is otherwise kept with a `problem` that says so
- `derive_uninstall_command()` returns a command only for a single install of a single named package, with nothing around it but `apt`/`apt-get`/`nala`/`brew update` or `brew tap`. It understands `apt`, `apt-get`, `nala`, and `dnf install`, `pacman -S`, `apk add`, `brew install`, global `bun` and `npm` installs, `cargo install`, `uv tool install`, and `winget install`; anything else, several packages, a local path, or a URL gives `None`
- with `show_output=True` the uninstall command runs attached to the terminal, where it can ask for a password or a confirmation; with `False` it gets no input and its last five non-empty output lines go into `problem` on failure
- a command that exits non-zero, or that succeeds while the program is still there, also yields `BinaryKept`
- after a removal the tool's version marker under `INSTALL_VERSION_ROOT` is deleted

`locate_installed_binary(exe_name, installer_data)` does only the lookup. It returns `None` when the program is not installed, or an `InstalledBinary` whose `removal_command` is empty for a plain file deletion and whose `removal_problem` is non-empty when StackOps will not remove it.

---

## Version tracking and install paths

Current constants come from `stackops.utils.source_of_truth`:

| Constant | Current path |
| --- | --- |
| `INSTALL_VERSION_ROOT` | `~/.config/stackops/cli_tools_installers/versions` |
| `INSTALL_TMP_DIR` | `~/tmp_results/tmp_installers` |
| `INSTALL_LOGS_ROOT` | `~/tmp_results/installer_logs` |
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

## Package groups reference

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

## Installer catalog

::: stackops.utils.installer_utils.installer_catalog
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Installer script resolution

::: stackops.utils.installer_utils.installer_scripts
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Installer bulk runner

::: stackops.utils.installer_utils.installer_bulk_runner
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Installer bulk planning

::: stackops.utils.installer_utils.installer_bulk_plan
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Installer bulk models

::: stackops.utils.installer_utils.installer_bulk_models
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

## Linux package manager detection

::: stackops.utils.installer_utils.linux_package_manager
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Linux package files

::: stackops.utils.installer_utils.linux_package_file
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Package-manager command execution

::: stackops.utils.installer_utils.package_manager_installation
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

## Installer removal

::: stackops.utils.installer_utils.installer_removal
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Uninstall command derivation

::: stackops.utils.installer_utils.installer_uninstall_command
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
