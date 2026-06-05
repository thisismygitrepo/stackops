## config

Configuration management.

```bash
devops config [SUBCOMMAND] [ARGS]...
```

Manage guided setup, init scripts, dotfiles, packaged assets, example config generation, and terminal profile/theme setup.

Current `devops config --help` exposes:

| Command | Description |
|---------|-------------|
| `interactive` | Run the interactive machine configuration flow |
| `sync` | Apply dotfile mappings with `symlink` or `copy` |
| `register` | Register a file or directory into the user mapper |
| `edit` | Open the library or user `mapper.toml` |
| `export-dotfiles` | Export `~/dotfiles` for machine migration |
| `import-dotfiles` | Import an exported dotfiles archive |
| `copy-assets` | Copy packaged scripts and settings onto the machine |
| `secrets` | Define env vars from `.stackops/secrets/secrets.json` |
| `dump` | Write example configuration files or print/run packaged init/setup scripts |
| `terminal` | Shell profile and terminal theme commands |

### interactive

Run the guided machine configuration flow.

```bash
devops config interactive
```

This launches the interactive setup helper instead of performing a direct install.

### sync

Apply the current dotfile mapping set.

```bash
devops config sync <up|down> --sensitivity <public|private|all> --method <symlink|copy> [OPTIONS]
```

Key arguments and options from current help:

| Item | Description |
|------|-------------|
| `direction` | Required. Use `up` to push default paths into the managed location, or `down` to apply managed files back to default paths |
| `--sensitivity`, `-s` | Required. Choose `private`, `public`, or `all` |
| `--method`, `-m` | Required. Use `symlink` or `copy` |
| `--repo`, `-r` | Select mappings from `library`, `user`, or `all` |
| `--on-conflict`, `-o` | Conflict policy such as `throw-error`, `overwrite-self-managed`, or `overwrite-default-path` |
| `--which`, `-w` | Limit the run to specific mapping names, or use `all` |

If `--which` is omitted, the command falls back to interactive selection.

For library-backed public configs, copy packaged settings first when needed:

```bash
devops config copy-assets settings
```

Examples:

```bash
# Apply all public mappings with symlinks
devops config sync down --sensitivity public --method symlink --which all

# Push local private config changes back into the managed backup area
devops config sync up --sensitivity private --method copy --repo user
```

### register

Register a new config file or directory into the self-managed dotfiles area and, by default, record that mapping in the user mapper.

Without `--destination`, the managed file is stored flat under `~/dotfiles/stackops/mapper/files/` as `<location-hash>.<original-name>`, for example `5781a41fbab95a09.bot-db.md`.

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
| `--shared`, `-sh` | Place the managed file under a shared layout when using `--destination` |
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
devops config copy-assets <scripts|settings|all>
```

Examples:

```bash
devops config copy-assets scripts
devops config copy-assets all
```

### secrets

Define environment variables from the current directory's `.stackops/secrets/secrets.json`.

```bash
devops config secrets github personal-access-token
devops config secrets aws dev iam-access-key
devops config secrets AWS_ACCESS_KEY_ID
devops config secrets --interactive
devops config secrets -i aws
devops config secrets --verbose aws dev iam-access-key
devops config secrets --name aws-dev --tag iam-access-key
devops config secrets --name aws-dev --tag session-token
devops config secrets --path ~/private/team-secrets.json aws dev
devops config secrets --edit
```

The query terms must identify exactly one `entries[].secrets[].keyValues` object. Terms are case-insensitive substring matches, and all terms must match somewhere across entry name/tags/accountName, secret name/tags/scopes, metadata, or environment variable keys. When one `keyValues` object is selected, all variables in that object are loaded together, for example an AWS access key pair plus region.

Use `--interactive`, `-i` to choose a matching secret bundle with the TV fuzzy picker. If terms or exact selectors are provided, they pre-filter the picker list.

Use `--verbose`, `-v` to print the selected bundle and environment variable keys without printing secret values.

For script-stable matching, use exact selectors. `--name`, `-n` matches `entries[].name`; `--tag`, `--tags`, `-t` requires an exact entry or secret tag and can be repeated; `--key`, `-k` requires an exact environment variable key. More specific selectors are also available: `--secret-name`, `--entry-tag`, `--secret-tag`, and `--scope` for values inside `entries[].secrets[].scopes`. Exact selectors are case-sensitive and can be combined with query terms.

Use `--path`, `-p` to read another secrets JSON file instead of `.stackops/secrets/secrets.json`. Use `--edit`, `-e` to open the selected secrets file, creating it from the packaged example if it does not exist yet.

### dump

Write example configuration files into the current directory, or print one of the packaged init/setup scripts.

```bash
devops config dump --which ve
devops config dump --which layout
devops config dump --which data
devops config dump --which dotfiles
devops config dump --which secrets
devops config dump --which secrets --data
devops config dump --which secrets --schema
devops config dump --which config
devops config dump --which config --default-path
devops config dump --which config --default-path --force
devops config dump --which init
devops config dump --which ia
devops config dump --which live --run
```

Supported `--which` values from current help:

| Value | Meaning |
|-------|---------|
| `ve` | Write `.ve.example.yaml` in the current working directory |
| `layout` | Write `layout.json` and `layout.schema.json` under `.stackops/examples` in the current working directory |
| `data` | Write `data.yaml` and `data.schema.json` under `.stackops/examples` in the current working directory |
| `dotfiles` | Write `dotfiles.yaml` and `dotfiles.schema.json` under `.stackops/examples` in the current working directory |
| `secrets` | Write `secrets.json` and `secrets.schema.json` under `.stackops/secrets` in the current working directory |
| `config` | Write `config.json` and `config.schema.json` under `.stackops/config` in the current working directory |
| `init` | Print the shell init script for the current platform |
| `ia` | Print the interactive setup bootstrap script |
| `live` | Print the live-from-GitHub bootstrap script |

Key options:

| Option | Description |
|--------|-------------|
| `--data`, `-d` | Write only the data/template file for configuration dumps |
| `--schema`, `-s` | Write only the schema file for configuration dumps |
| `--default-path`, `-p` | Write to the default StackOps path for the selected file instead of the current directory |
| `--force`, `-f` | Overwrite existing dump output files |
| `--run`, `-r` | Run the selected init/setup script instead of printing it |

When neither `--data` nor `--schema` is passed, file dumps write both files. Existing files are not overwritten unless `--force` is passed. `--default-path` maps `layout` to `~/dotfiles/stackops/config/layouts.json`, `config` to `~/dotfiles/stackops/config/config.json`, `secrets` to `~/dotfiles/stackops/secrets/secrets.json`, `data` to `~/dotfiles/stackops/mapper/data.yaml`, and `dotfiles` to `~/dotfiles/stackops/mapper/dotfiles.yaml`.

### terminal

Terminal setup lives under a nested Typer app:

```bash
devops config terminal [SUBCOMMAND] [ARGS]...
```

`devops config terminal --help` currently exposes:

| Command | Description |
|---------|-------------|
| `config-shell` | Create or configure the default shell profile or Nushell profile |
| `starship-theme` | Interactive Starship prompt theme selection (`r`) |
| `pwsh-theme` | Interactive PowerShell prompt theme selection |
| `wezterm-theme` | Interactive WezTerm theme selection |
| `ghostty-theme` | Interactive Ghostty theme selection |
| `windows-terminal-theme` | Interactive Windows Terminal color scheme selection |
| `tmux-style` | Oh My Tmux install, local config, preset, option, reload, and status helpers (`t`) |

The nested help screens render `Usage: devops terminal ...`, but the full entrypoint remains `devops config terminal ...`.

Examples:

```bash
devops config terminal config-shell --which default
devops config terminal config-shell --which nushell
devops config terminal wezterm-theme
devops config terminal ghostty-theme
devops config terminal tmux-style install-oh-my-tmux
devops config terminal t i
devops config terminal tmux-style apply-stackops-local --force
devops config terminal tmux-style preset catppuccin-mocha --reload
devops config terminal tmux-style set-option tmux_conf_theme_colour_4 '#89b4fa' --reload
```

`tmux-style install-oh-my-tmux` delegates to the shared `devops install oh-my-tmux` installer. The remaining subcommands operate on the Oh My Tmux local customization file, defaulting to the home-dotfile layout (`~/.tmux.conf.local`) created by that installer. Use `--location xdg` for the XDG layout (`$XDG_CONFIG_HOME/tmux/tmux.conf.local`).

---
