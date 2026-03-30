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

- `direction` is now required: use `up` for default path to managed path, or `down` for managed path to default path
- `--sensitivity` selects whether you are managing `public`, `private`, or `all` configuration files
- `--method` selects `symlink` or `copy`
- `--repo` chooses which mapper source to use
- `--which` narrows the operation to specific items

That makes `devops config sync` the main high-level replacement for older global configuration, dotfiles, and links documentation.

For packaged library settings, use `devops config copy-assets settings` explicitly before syncing `down`.

---

## Other configuration subcommands

Current `devops config --help` lists subcommands for:

- `register`
- `edit`
- `export-dotfiles`
- `import-dotfiles`
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

Device inspection and local mounting now live under `utils machine`:

- `utils machine list-devices`
- `utils machine mount`

Use `devops config --help` as the entrypoint for config workflows, then drill down with `--help` on the specific subgroup or subcommand you need.

---

## Related workflows

- For data backup and retrieval, use `devops data --help`.
- For cloud storage actions, use `cloud --help`.
