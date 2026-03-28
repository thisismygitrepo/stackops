# Jobs and Installer APIs

The `machineconfig.jobs` package is where curated installer metadata and setup flows live. In practice, most direct usage here comes from the installer subsystem.

There are two complementary ways these APIs show up:

- directly, when you want to inspect package groups or use the installer catalog
- indirectly, when higher-level helpers call into the installer layer through guards like `install_if_missing()`

---

## What lives here

| Area | What it provides | Main modules |
| --- | --- | --- |
| Package groups | Named collections of tools for common machine setups | `machineconfig.jobs.installer.package_groups` |
| Installer catalog | Per-tool install metadata and routing across package managers | `machineconfig.jobs.installer.*` |
| Security checks | Verification and reporting helpers used around installation | `machineconfig.jobs.installer.checks.*` |
| Per-tool scripts | Python installers for tools that need custom flows | `machineconfig.jobs.installer.python_scripts.*` |

---

## Package groups

Machineconfig defines curated package groups for common use cases:

| Group | Description |
| --- | --- |
| `gui` | Essential GUI applications |
| `agents` | AI and coding-assistant tools |
| `termabc` | Terminal essentials and shell tooling |
| `dev` | Broader development environment packages |
| `sysabc` | Core system helpers |

### Example

```python
from machineconfig.jobs.installer.package_groups import PACKAGE_GROUP2NAMES

print(PACKAGE_GROUP2NAMES.keys())
print(PACKAGE_GROUP2NAMES["agents"])
```

---

## Relationship to utility helpers

The low-level helper:

```python
from machineconfig.utils.installer_utils.installer_cli import install_if_missing
```

is often used inside other utility or networking modules before they invoke an external CLI. The full installer catalog and package-manager logic still lives here in `jobs.installer`.

So a good rule of thumb is:

- use `install_if_missing()` when you just need a guard before continuing
- use the installer docs when you want to understand or extend the actual installation pipeline

---

## Directory layout

```text
jobs/installer/
├── checks/              # Security and reporting helpers
├── linux_scripts/       # Linux shell installers
├── powershell_scripts/  # Windows PowerShell installers
├── python_scripts/      # Custom Python installers for specific tools
└── package_groups.py    # Named tool bundles
```

---

## Next page

Continue to the [Installer reference](installer.md) for the detailed catalog, data model, package groups, and per-tool installer behavior.
