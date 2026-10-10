# Configuration Management

Configuration and dotfiles workflows now live under `devops config ...`.

---

## Overview

Use the `devops config` command group for machine-facing configuration tasks such as:

- guided machine setup
- packaged init/setup script output
- shell profile setup
- dotfiles registration and synchronization
- theme selection for supported tools
- exporting or importing dotfiles during migration
- copying packaged assets to the local machine

Start here:

```bash
devops config --help
devops config dotfiles --help
```

---

## Terminal configuration

Terminal-profile and terminal-theme commands now live under a dedicated subgroup:

```bash
devops config terminal --help
```

Use `devops config terminal config-shell --which default` or `devops config terminal config-shell --which nushell` to invoke the shell-profile setup action directly.

---

## Syncing configuration

The current sync workflow is:

```bash
devops config dotfiles sync --help
```

Current help shows these key concepts:

- positional `direction` with `up` and `down`
- `--sensitivity` selects whether you are managing `public`, `private`, or `all` configuration files
- `--method` selects `symlink` or `copy`
- `--source`, `-S` chooses which mapper source to use
- `--which` narrows the operation to specific items

That makes `devops config dotfiles sync` the main high-level replacement for older configuration, dotfiles, and links documentation.

For packaged library settings, use `devops config copy-assets settings` explicitly before syncing `down`.

---

## Registering and editing mappings

Use these commands when you need to add new managed dotfiles or inspect the active mapping configuration:

- `devops config dotfiles register`
- `devops config edit dotfiles`

`devops config edit` takes the kind of StackOps user file to open: `config`, `layouts`, `dotfiles`, `data`, or `secrets`.

---

## Exporting and importing dotfiles

For machine migration or archive-style workflows, use:

- `devops config dotfiles export`
- `devops config dotfiles import`

These commands replace the older push, backup, and restore flow.

---

## Configuration versus data

Use `devops config ...` for managed configuration files and shell, editor, or tool settings.

Use `devops data sync --help` when you want backup-style synchronization of data directories and files to or from cloud storage.

---

## Other configuration subcommands

Beyond sync, register, edit, export, and import, `devops config --help` also lists:

- `interactive`
- `copy-assets`
- `dump`
- `terminal`
- `secrets`
- `setup`

Inside `devops config terminal --help`, the current terminal commands are:

- `config-shell`
- `starship-theme`
- `pwsh-theme`
- `wezterm-theme`
- `ghostty-theme`
- `windows-terminal-theme`
- `tmux-style`
