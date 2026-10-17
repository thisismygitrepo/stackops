## config

Configuration management.

```bash
devops config [SUBCOMMAND] [ARGS]...
```

Manage dotfiles, guided setup, the StackOps user files, init scripts, packaged assets, and terminal profile/theme setup.

Current `devops config --help` exposes:

| Command | Description |
|---------|-------------|
| `dotfiles` | Sync, register, export, and import dotfiles listed in the user `mapper/dotfiles.yaml` |
| `setup` | Guided creation of StackOps user configuration files |
| `edit` | Open one StackOps user file in an editor, creating a minimal one with its schema when missing |
| `path` | Print the selected configuration file and schema paths |
| `init` | Create a missing configuration file and its schema |
| `validate` | Validate the selected configuration file |
| `export-example` | Write a packaged example file and its schema |
| `init-script` | Print or run a packaged shell init or machine setup script |
| `terminal` | Shell profile and terminal theme commands |
| `interactive` | Run the interactive machine configuration flow |
| `copy-assets` | Copy packaged scripts and settings onto the machine |

`devops config dotfiles` also provides `path`, `init`, and `validate` for its managed mapping. Each accepts `--path`, `-p` to select another file. Use `init` to prepare an empty mapping and `register` to copy or symlink an existing dotfile and record its mapping.

`edit`, `export-example`, and `setup` share one set of StackOps user files:

| Kind | User file | Schema |
|------|-----------|--------|
| `config` | `~/dotfiles/stackops/config/config.json` | `config.schema.json` |
| `layouts` | `~/dotfiles/stackops/config/layouts.json` | `layout.schema.json` |
| `dotfiles` | `~/dotfiles/stackops/mapper/dotfiles.yaml` | `dotfiles.schema.json` |
| `data` | `~/dotfiles/stackops/mapper/data.yaml` | `data.schema.json` |
| `secrets` | `~/dotfiles/stackops/secrets/secrets.json` | `secrets.schema.json` |

### interactive

Run the guided machine configuration flow.

```bash
devops config interactive
```

This launches the interactive setup helper instead of performing a direct install.

### setup

Create or update StackOps user configuration through focused guided flows:

```bash
devops config setup [SUBCOMMAND] [ARGS]...
```

| Command | Description |
|---------|-------------|
| `cloud` | Select an rclone remote and create or update the StackOps config and schema |
| `email` | Select or create an SMTP profile and save the default recipient |
| `agent` | Select the default coding agent and save it in the StackOps config |
| `data` | Interactively register a backup entry and install its YAML schema |
| `dotfiles` | Interactively register a dotfile and install its YAML schema |
| `layouts` | Install starter terminal layouts and their JSON schema |
| `secrets` | Interactively create the global secrets file and schema |

Examples:

```bash
devops config setup cloud
devops config setup agent --agent claude
devops config setup data
devops config setup layouts
```

### dotfiles

Dotfile management lives under a nested Typer app, mirroring `devops data` for backups:

```bash
devops config dotfiles [SUBCOMMAND] [ARGS]...
```

| Command | Description |
|---------|-------------|
| `sync` | Apply dotfile mappings with `symlink` or `copy` |
| `register` | Copy or symlink a file into managed storage and register its mapping |
| `export` | Export `~/dotfiles` for machine migration |
| `import` | Import an exported dotfiles archive |

Open the user mapper itself with `devops config edit dotfiles`.

#### sync

Apply the current dotfile mapping set.

```bash
devops config dotfiles sync <up|down> --sensitivity <public|private|all> --method <symlink|copy> [OPTIONS]
```

Key arguments and options from current help:

| Item | Description |
|------|-------------|
| `direction` | Required. Use `up` to push default paths into the managed location, or `down` to apply managed files back to default paths |
| `--sensitivity`, `-s` | Required. Choose `private`, `public`, or `all` |
| `--method`, `-m` | Required. Use `symlink` or `copy` |
| `--source`, `-S` | Select mappings from `library`, `user`, or `all` |
| `--on-conflict`, `-c` | Conflict policy such as `throw-error`, `overwrite-self-managed`, or `overwrite-default-path` |
| `--which`, `-w` | Limit the run to specific mapping names, or use `all` |

If `--which` is omitted, the command falls back to interactive selection.

For library-backed public configs, copy packaged settings first when needed:

```bash
devops config copy-assets settings
```

Examples:

```bash
# Apply all public mappings with symlinks
devops config dotfiles sync down --sensitivity public --method symlink --which all

# Push local private config changes back into the managed backup area
devops config dotfiles sync up --sensitivity private --method copy -S user
```

#### register

Copy or symlink a config file or directory into the managed dotfiles area and add or update its mapping in the user mapper. Registration always records the mapping.

Without `--destination`, the managed file is stored flat under `~/dotfiles/stackops/mapper/files/` as `<location-hash>.<original-name>`, for example `5781a41fbab95a09.bot-db.md`.

```bash
devops config dotfiles register [OPTIONS] FILE
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--method`, `-m` | Store it with `copy` or `symlink` semantics |
| `--on-conflict`, `-c` | Conflict strategy during the initial transfer |
| `--sensitivity`, `-s` | Mark the mapping as `private` or `public` |
| `--destination`, `-d` | Override the default self-managed destination |
| `--group`, `-S` | Group name to write inside the user mapper |
| `--os`, `-o` | Restrict the mapping to one OS or a comma-separated list |
| `--shared`, `-H` | Place the managed file under a shared layout when using `--destination` |

Examples:

```bash
# Register a private file and record it in the default mapper group
devops config dotfiles register ~/.config/htop/htoprc --sensitivity private

# Register a public directory with symlink semantics
devops config dotfiles register ~/.config/nvim --method symlink --sensitivity public --group editors
```

#### export

Package and encrypt `~/dotfiles` for transfer to another machine.

```bash
devops config dotfiles export
```

The command prompts for an encryption password. Use `--ssh` for SSH transfer; otherwise it exposes the encrypted archive on the LAN.

| Option | Description |
|--------|-------------|
| `--ssh`, `-s` | Use SSH/SCP-style transfer |

#### import

Import an encrypted dotfiles archive from a local path or URL. The command prompts for the decryption password; `--ssh` selects SSH transfer.

```bash
devops config dotfiles import --url /path/to/dotfiles.zip.gpg
devops config dotfiles import --ssh
```

### edit

Open one StackOps user file in `hx`, `nano`, or `code`.

```bash
devops config edit <config|layouts|dotfiles|data|secrets> [--path PATH] [--editor hx|nano|code]
```

When the file does not exist yet, it is created with the smallest valid content for its kind, and its schema is installed next to it: a versioned `config.json`, an empty dotfiles or data mapper with its YAML header, and the packaged starter for `layouts.json` and `secrets.json`, which require at least one entry. Secrets files are created with mode `0600`.

Use `--path`, `-p` to edit a file of the same kind somewhere else, for example a project-local secrets file:

```bash
devops config edit secrets --path .stackops/secrets/secrets.json
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

StackOps secrets are managed under `devops vault`. `search` inspects matching bundle labels and environment keys; `load` prepares their values for the calling shell. Neither command prints secret values by default. `--json` explicitly prints matching entries, including their values, without loading the environment.

```bash
devops vault search github personal-access-token
devops vault search --interactive
devops vault search mail --all-matches --json
devops vault load --name aws-dev --tag iam-access-key
devops vault load --source global github token
devops vault load --all-matches --source both cloudf
devops vault subset ./team-secrets.json --source global
devops vault add --source global
devops vault init --source local
devops vault validate --source local
```

The command aliases are `search/s`, `load/l`, `stats/t`, `subset/u`, `add/a`, `path/p`, `init/i`, and `validate/v`. `init` and `validate` require an explicit `--source local|global` or `--path`.

Terms are case-insensitive substring matches across login and secret names, tags, scopes, metadata, and environment keys. By default, selection must identify one bundle. Use `--all-matches`, `-a` for every match or `--interactive`, `-i` to choose with the TV picker. `load --all-matches` rejects conflicting values for the same environment variable. `--preview-secrets`, `-P` shows values in the interactive preview; `--verbose`, `-v` shows metadata without values.

Exact, case-sensitive selectors can be combined with query terms: `--name/-n`, `--secret-name/-N`, `--tag/--tags/-t`, `--login-tag/-l`, `--secret-tag/-T`, `--scope/-S`, and `--key/-k`. Tag, scope, and key options are repeatable.

Both `search` and `load` accept `--source/-s local|global|both` (aliases `l/g/b`) and `--path/-p` for another local file. With neither supplied, the local `.stackops/secrets/secrets.json` is preferred; the global file is used when local is absent.

`subset OUTPUT_PATH` interactively selects login entries from one source and writes a secrets file. `--on-conflict/-c throw-error|overwrite|append` controls an existing output file. `add` prompts for a new login entry and appends it; `--create/-c` also permits creating the file. Use `devops config edit secrets` to edit the global file, or pass `--path` for another file.

Bitwarden operations have their own provider group:

```bash
devops vault bitwarden login-and-unlock
devops vault bitwarden search github
devops vault bitwarden sync
eval "$(devops vault bitwarden export-session)"
devops vault bitwarden clean-cache
```

`login-and-unlock` authenticates and saves a session. `export-session` prints shell code for an already unlocked saved session; it does not unlock the vault. Its short alias remains `u`, and the Bitwarden group alias remains `k`.

### export-example

Write a packaged example file and its schema, by default under `.stackops/examples` in the current working directory.

```bash
devops config export-example <config|layouts|dotfiles|data|secrets> [OPTIONS]
```

```bash
devops config export-example layouts
devops config export-example secrets --data
devops config export-example secrets --schema
devops config export-example config --default-path
devops config export-example config --default-path --overwrite
```

Key options:

| Option | Description |
|--------|-------------|
| `--data`, `-d` | Write only the example data file |
| `--schema`, `-s` | Write only the schema file |
| `--default-path`, `-p` | Write to the real user file path from the table above instead of `.stackops/examples` |
| `--overwrite`, `-f` | Overwrite existing output files |

When neither `--data` nor `--schema` is passed, both files are written. The command refuses to write anything if any selected output already exists, unless `--overwrite` is passed. The `dotfiles` and `data` examples are the packaged library mappers, so exporting them to `--default-path` copies every library entry into the user mapper; use `devops config edit` for an empty user mapper instead.

### init-script

Print one of the packaged shell init or machine setup scripts, or run it.

```bash
devops config init-script <init|ia|live> [--run]
```

| Value | Meaning |
|-------|---------|
| `init` | Shell init script for the current platform |
| `ia` | Interactive setup bootstrap script |
| `live` | Live-from-GitHub bootstrap script |

Use `--run`, `-R` to run the script instead of printing it.

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

Examples:

```bash
devops config terminal config-shell --shell default
devops config terminal config-shell --shell nushell
devops config terminal wezterm-theme
devops config terminal ghostty-theme
devops config terminal tmux-style install-oh-my-tmux
devops config terminal t i
devops config terminal tmux-style apply-stackops-local --overwrite
devops config terminal tmux-style preset catppuccin-mocha --reload
devops config terminal tmux-style set-option tmux_conf_theme_colour_4 '#89b4fa' --reload
```

`tmux-style install-oh-my-tmux` delegates to the shared `devops software install oh-my-tmux` installer. The remaining subcommands operate on the Oh My Tmux local customization file, defaulting to the home-dotfile layout (`~/.tmux.conf.local`) created by that installer. Use `--location xdg` for the XDG layout (`$XDG_CONFIG_HOME/tmux/tmux.conf.local`).

---
