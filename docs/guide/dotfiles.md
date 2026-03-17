# Dotfiles Management

Dotfiles workflows are now documented through `devops config ...` rather than older `mcfg dotfiles ...` commands.

---

## Overview

Machineconfig treats dotfiles as part of the configuration management flow:

- register the files you want managed
- sync them onto a machine
- choose whether to copy or symlink
- separate public and private material
- export or import them during migration

Start with:

```bash
devops config --help
devops config sync --help
```

---

## Sync model

Current `devops config sync --help` exposes the main dotfiles concepts:

- `--sensitivity` for `public`, `private`, or `all`
- `--method` for `symlink` or `copy`
- `--repo` for mapper source selection
- `--which` to target one item or all items

This is the current replacement for older top-level `mcfg dotfiles sync` examples.

---

## Registering and editing mappings

The current configuration command group includes:

- `devops config register`
- `devops config edit`

Those are the relevant entrypoints when you need to add new managed dotfiles or inspect the active mapping configuration.

Use:

```bash
devops config --help
```

to discover the current subcommand surface before making changes.

---

## Exporting and importing dotfiles

For machine migration or archive-style workflows, `devops config --help` currently lists:

- `export-dotfiles`
- `import-dotfiles`

These commands are the current source-backed path for packaging or restoring dotfiles, instead of the older init/push/backup/restore guide flow.

---

## Dotfiles versus data

Use `devops config ...` for managed configuration files and shell/editor/tool settings.

Use `devops data sync --help` when you want backup-style synchronization of data directories and files to or from cloud storage.
