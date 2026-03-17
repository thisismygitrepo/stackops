# Configuration Management

Configuration workflows now live under `devops config ...`.

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
```

---

## Shell configuration

The current shell entrypoint is:

```bash
devops config shell --help
```

The live help shows a `--which` option for selecting the shell profile variant to configure.

---

## Syncing configuration

The current sync workflow is:

```bash
devops config sync --help
```

Current help shows these key concepts:

- `--sensitivity` selects whether you are managing `public`, `private`, or `all` configuration files
- `--method` selects `symlink` or `copy`
- `--repo` chooses which mapper source to use
- `--which` narrows the operation to specific items

That makes `devops config sync` the main high-level replacement for older global `mcfg config ...`, `mcfg dotfiles ...`, and `mcfg links ...` documentation.

---

## Other configuration subcommands

Current `devops config --help` also lists subcommands for:

- `register`
- `edit`
- `export-dotfiles`
- `import-dotfiles`
- `shell`
- `starship-theme`
- `pwsh-theme`
- `wezterm-theme`
- `ghostty-theme`
- `windows-terminal-theme`
- `copy-assets`
- `dump`
- `list-devices`
- `mount`

Use `devops config --help` as the entrypoint, then drill down with `--help` on the specific subcommand you need.

---

## Related workflows

- For data backup and retrieval, use `devops data --help`.
- For cloud storage actions, use `cloud --help`.
- For the umbrella compatibility wrapper, use `mcfg devops config --help`.
