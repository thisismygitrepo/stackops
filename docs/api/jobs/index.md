# Jobs and Installer APIs

`stackops.jobs` is mostly the script asset layer for the installer system. The catalog YAML and the package-group definitions live with the installer schemas under `stackops.utils.schemas.installer`.

It ships:

- platform-specific install scripts
- security-check helpers

The runtime installation engine that consumes those assets lives under `stackops.utils.installer_utils`.

---

## What lives here

| Area | What it provides | Main modules |
| --- | --- | --- |
| Package groups | Named collections of apps such as `termabc`, `agents`, `dev`, and `db-cli` | `stackops.utils.schemas.installer.package_groups` |
| Installer catalog assets | `installer_data.yaml`, installer schema, and typed installer records | `stackops.utils.schemas.installer.*` |
| Installer scripts | Packaged Python, shell, and PowerShell installers | `stackops.jobs.installer.python_scripts.*`, `stackops.jobs.installer.linux_scripts.*`, `stackops.jobs.installer.powershell_scripts.*` |
| Installer runtime | CLI entrypoints, installer selection, bulk install orchestration, direct URL install | `stackops.utils.installer_utils.*` |
| Typed installer schema | Platform names, architecture names, install requests, install results | `stackops.utils.schemas.installer.installer_types` |
| Security checks | Scan and reporting helpers for installed tools | `stackops.jobs.installer.checks.*` |

---

## Package groups

The current `PACKAGE_GROUP2NAMES` keys are:

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

These are the exact package-group keys accepted by the runtime. CLI name aliases such as `agy` for `antigravity` are handled separately by `stackops.utils.installer_utils.installer_cli`.

Example:

```python
from stackops.utils.schemas.installer.package_groups import PACKAGE_GROUP2NAMES

print(PACKAGE_GROUP2NAMES["agents"])
print(PACKAGE_GROUP2NAMES["termabc"])
```

---

## Relationship to the installer helpers

The runtime path looks like this:

1. `utils/schemas/installer/installer_data.yaml` defines the library catalog. `stackops.utils.installer_utils.installer_catalog.read_installer_data()` loads it for the `library` and `all` sources and a user catalog for the `user` and `all` sources; with `all`, a user entry replaces the library entry of the same name.
2. `utils/schemas/installer/package_groups.py` defines named bundles.
3. `stackops.utils.installer_utils.installer_runner.get_installers()` filters the library catalog for a given OS, architecture, and optional groups; `get_installers_from_source()` does the same for a chosen source.
4. `stackops.utils.installer_utils.installer_class.Installer` resolves and executes one install target.
5. `stackops.utils.installer_utils.installer_cli` exposes the higher-level CLI-style entrypoints.

So this section documents both the packaged job assets and the installer APIs that consume them.

---

## Directory layout

```text
utils/schemas/installer/
├── installer_data.yaml           # Catalog of installer definitions
├── installer_data.example.yaml   # Starter user catalog
├── installer_data.schema.json    # JSON Schema for the catalog
├── installer_categories.py       # Titles and descriptions of the category labels
├── installer_types.py            # TypedDicts and platform helpers
└── package_groups.py             # Named package bundles

jobs/installer/
├── checks/                 # Security and reporting helpers
├── linux_scripts/          # Linux and macOS shell installers
├── macos_scripts/          # macOS-specific installers (no scripts at present)
├── powershell_scripts/     # Windows PowerShell installers
└── python_scripts/         # Custom Python installers
```

---

## Next page

Continue to the [Installer reference](installer.md) for the current data model, install strategies, group handling, and callable entrypoints.
