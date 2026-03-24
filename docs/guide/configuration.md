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

Shell-specific commands now live under a dedicated subgroup:

```bash
devops config shell --help
```

Running `devops config shell` shows the shell subgroup help. Use `devops config shell config-shell --which default` or `devops config shell config-shell --which nushell` if you want to invoke the shell-profile setup action directly.

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

Current `devops config --help` lists subcommands for:

- `register`
- `edit`
- `export-dotfiles`
- `import-dotfiles`
- `shell`
- `copy-assets`
- `dump`

Inside `devops config shell --help`, the current shell commands are:

- `config-shell`

- `starship-theme`
- `pwsh-theme`
- `wezterm-theme`
- `ghostty-theme`
- `windows-terminal-theme`

Device inspection and local mounting now live under `utils`:

- `utils list-devices`
- `utils mount`

Use `devops config --help` as the entrypoint for config workflows, then drill down with `--help` on the specific subgroup or subcommand you need.

---

## Related workflows

- For data backup and retrieval, use `devops data --help`.
- For cloud storage actions, use `cloud --help`.
- For the umbrella compatibility wrapper, use `mcfg devops config --help`.
