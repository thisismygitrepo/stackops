# Configuration Management

Configuration and dotfiles workflows now live under `devops config ...`.

---

## Overview

Use the `devops config` command group for machine-facing configuration tasks such as:

- shell profile setup
- dotfiles registration and synchronization
- theme selection for supported tools
- exporting or importing dotfiles during migration
- copying packaged assets to the local machine

Start here:

```bash
devops config --help
devops config sync --help
```

---

## Terminal configuration

Terminal-profile and terminal-theme commands now live under a dedicated subgroup:

```bash
devops config terminal --help
```

Use `devops config terminal config-shell --which default` or `devops config terminal config-shell --which nushell` to invoke the shell-profile setup action directly.

The nested help screen renders `Usage: devops terminal ...`, but the full entrypoint remains `devops config terminal ...`.

---

## Syncing configuration

The current sync workflow is:

```bash
devops config sync --help
```

Current help shows these key concepts:

- positional `direction` with `up` and `down`
- `--sensitivity` selects whether you are managing `public`, `private`, or `all` configuration files
- `--method` selects `symlink` or `copy`
- `--repo` chooses which mapper source to use
- `--which` narrows the operation to specific items

That makes `devops config sync` the main high-level replacement for older configuration, dotfiles, and links documentation.

For packaged library settings, use `devops config copy-assets settings` explicitly before syncing `down`.

---

## Registering and editing mappings

Use these commands when you need to add new managed dotfiles or inspect the active mapping configuration:

- `devops config register`
- `devops config edit`

---

## Exporting and importing dotfiles

For machine migration or archive-style workflows, use:

- `devops config export-dotfiles`
- `devops config import-dotfiles`

These commands replace the older init, push, backup, and restore flow.

---

## Configuration versus data

Use `devops config ...` for managed configuration files and shell, editor, or tool settings.

Use `devops data sync --help` when you want backup-style synchronization of data directories and files to or from cloud storage.

---

## Other configuration subcommands

Beyond sync, register, edit, export, and import, `devops config --help` also lists:

- `copy-assets`
- `dump`
- `terminal`

Inside `devops config terminal --help`, the current terminal commands are:

- `config-shell`
- `starship-theme`
- `pwsh-theme`
- `wezterm-theme`
- `ghostty-theme`
- `windows-terminal-theme`
