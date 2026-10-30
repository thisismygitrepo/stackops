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

Use `devops config terminal config-shell --shell default` or `devops config terminal config-shell --shell nushell` to invoke the shell-profile setup action directly.

---

## Syncing configuration

The current sync workflow is:

```bash
devops config dotfiles sync --help
```

Current help shows these key concepts:

- positional `direction` with `up` and `down`
- `--method` selects `symlink` or `copy`
- `--source`, `-s` chooses `user`, `library`, or `all` mapper sources
- `--which` narrows the operation to specific items

For dotfile sync, `library` selects the bundled mappings backed by `~/.config/stackops/settings`. `user` selects your mapper, and `all` combines both. An entry in your mapper replaces the library entry with the same group and name: `library` skips it and `all` uses yours. `devops config dotfiles collect` builds your mapper from what is on this machine: personal files (ssh, gpg, rclone, and similar) and your own versions of library settings (yazi, helix, and so on). It stores them in `~/dotfiles`, links them back, and skips anything identical to the packaged settings or already managed another way. Sync processes all entries selected by the mapper source and `--which`.

For packaged library settings, use `devops config copy-assets settings` explicitly before syncing `down`. `devops self update` refreshes these assets by default, and `--sync-configs` also applies the library mappings to their default application paths.

---

## Registering and editing mappings

Use these commands when you need to add new managed dotfiles or inspect the active mapping configuration:

- `devops config dotfiles collect`
- `devops config dotfiles register`
- `devops config edit dotfiles`

`devops config edit` takes the kind of StackOps user file to open: `config`, `layouts`, `dotfiles`, `data`, or `secrets`.

Dotfile registration accepts `--source user` / `-s user`, which is also the default. It records the mapping in the user mapper and stores files in its `mapper/files` directory. Use `--destination` to choose an explicit storage directory.

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
