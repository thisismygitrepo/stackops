# User Guide Overview

Machineconfig is organized around several direct CLI entrypoints rather than a single giant command tree.

---

## What Machineconfig covers

Machineconfig helps you work with:

- package installation and machine bootstrap
- shell and tool configuration
- dotfiles synchronization
- data backup and retrieval
- cloud workflows
- session and automation helpers

---

## Current command surface

The main commands you will see today are:

- `devops`
- `cloud`
- `sessions`
- `agents`
- `utils`
- `fire`
- `croshell`
- `msearch`

`mcfg` and `machineconfig` still exist as compatibility entrypoints that dispatch into the main command families.

---

## Core concepts

### 1. Direct entrypoints first

Use the command that matches the workflow you want:

- `devops` for install, config, data, repos, and machine-oriented operations
- `cloud` for cloud storage workflows
- `sessions` for layout and session management
- `msearch` for search workflows

### 2. Shared stack management

Machineconfig treats your working environment as a stack of related assets:

- packages and CLI tools
- configuration files
- dotfiles mappings
- backed-up data
- repositories and automation helpers

### 3. High-level wrappers still exist

If you already use `mcfg` or `machineconfig`, they still work as umbrella commands, but the detailed command trees now live under direct entrypoints.

---

## Guide sections

| Section | Description |
|---------|-------------|
| [Package Management](packages.md) | Install software with the current `devops install` workflow |
| [Configuration](configuration.md) | Manage shell and tool configuration under `devops config` |
| [Dotfiles](dotfiles.md) | Sync and move dotfiles with current config-oriented workflows |
| [Data Sync](data-sync.md) | Back up and retrieve data with current data workflows |
| [Automation](automation.md) | Use sessions, jobs, and helpers |

---

## Getting help

Start with the command family you need:

```bash
devops --help
cloud --help
sessions --help
msearch --help
```

If you want the compatibility wrapper instead:

```bash
mcfg --help
machineconfig --help
```

For the current command map, see [CLI Reference](../cli/index.md).
