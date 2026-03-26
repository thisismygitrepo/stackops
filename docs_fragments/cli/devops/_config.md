## config

Configuration management.

```bash
devops config [SUBCOMMAND] [ARGS]...
```

Manage dotfiles, packaged assets, example config generation, and terminal profile/theme setup.

Current `devops config --help` exposes:

| Command | Description |
|---------|-------------|
| `sync` | Apply dotfile mappings with `symlink` or `copy` |
| `register` | Register a file or directory into the user mapper |
| `edit` | Open the library or user `mapper.toml` |
| `export-dotfiles` | Export `~/dotfiles` for machine migration |
| `import-dotfiles` | Import an exported dotfiles archive |
| `copy-assets` | Copy packaged scripts and settings onto the machine |
| `dump` | Write example configuration files such as `.ve.example.yaml` |
| `terminal` | Shell profile and terminal theme commands |

### sync

Apply the current dotfile mapping set.

```bash
devops config sync --sensitivity <public|private|all> --method <symlink|copy> [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--sensitivity`, `-s` | Required. Choose `private`, `public`, or `all` |
| `--method`, `-m` | Required. Use `symlink` or `copy` |
| `--repo`, `-r` | Select mappings from `library`, `user`, or `all` |
| `--on-conflict`, `-o` | Conflict policy such as `throw-error`, `overwrite-self-managed`, or `overwrite-default-path` |
| `--which`, `-w` | Limit the run to specific mapping names, or use `all` |

If `--which` is omitted, the command falls back to interactive selection.

Examples:

```bash
# Sync all public mappings with symlinks
devops config sync --sensitivity public --method symlink --which all

# Apply only user-defined private mappings by copying files
devops config sync --sensitivity private --method copy --repo user
```

### register

Register a new config file or directory into the self-managed dotfiles area and, by default, record that mapping in the user mapper.

```bash
devops config register [OPTIONS] FILE
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--method`, `-m` | Store it with `copy` or `symlink` semantics |
| `--on-conflict`, `-o` | Conflict strategy during the initial transfer |
| `--sensitivity`, `-s` | Mark the mapping as `private` or `public` |
| `--destination`, `-d` | Override the default self-managed destination |
| `--section`, `-se` | Section name to write inside the user mapper |
| `--os` | Restrict the mapping to one OS or a comma-separated list |
| `--shared`, `-sh` | Place the managed file under a shared destination layout |
| `--record`, `-r` | Record the mapping in the user mapper file |

Examples:

```bash
# Register a private file and record it in the default mapper section
devops config register ~/.config/htop/htoprc --sensitivity private

# Register a public directory with symlink semantics
devops config register ~/.config/nvim --method symlink --sensitivity public --section editors
```

### edit

Open the dotfile mapper in `nano`, `hx`, or `code`.

```bash
devops config edit --editor hx --repo user
```

The user mapper is created automatically if it does not exist yet.

### export-dotfiles

Package and encrypt `~/dotfiles` for transfer to another machine.

```bash
devops config export-dotfiles <password>
```

Optional transfer flags:

| Option | Description |
|--------|-------------|
| `--over-internet`, `-i` | Internet-transfer flag present in the CLI, but the current implementation is not finished |
| `--over-ssh`, `-s` | Use SSH/SCP-style transfer |

### import-dotfiles

Import an encrypted dotfiles archive from a local path or URL.

```bash
devops config import-dotfiles --url /path/to/dotfiles.zip.enc --pwd <password>
```

### copy-assets

Copy packaged helper assets from the library onto the current machine.

```bash
devops config copy-assets <scripts|settings|both>
```

Examples:

```bash
devops config copy-assets scripts
devops config copy-assets both
```

### dump

Write example configuration files into the current directory.

```bash
devops config dump --which ve
```

At the moment, `ve` writes `.ve.example.yaml` in the current working directory.

### terminal

Terminal setup lives under a nested Typer app:

```bash
devops config terminal [SUBCOMMAND] [ARGS]...
```

`devops config terminal --help` currently exposes:

| Command | Description |
|---------|-------------|
| `config-shell` | Create or configure the default shell profile or Nushell profile |
| `starship-theme` | Interactive Starship prompt theme selection |
| `pwsh-theme` | Interactive PowerShell prompt theme selection |
| `wezterm-theme` | Interactive WezTerm theme selection |
| `ghostty-theme` | Interactive Ghostty theme selection |
| `windows-terminal-theme` | Interactive Windows Terminal color scheme selection |

The nested help screens render `Usage: devops terminal ...`, but the full entrypoint remains `devops config terminal ...`.

Examples:

```bash
devops config terminal config-shell --which default
devops config terminal config-shell --which nushell
devops config terminal wezterm-theme
devops config terminal ghostty-theme
```

---
