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
| `dump` | Write a packaged example file and its schema |
| `init-script` | Print or run a packaged shell init or machine setup script |
| `terminal` | Shell profile and terminal theme commands |
| `interactive` | Run the interactive machine configuration flow |
| `copy-assets` | Copy packaged scripts and settings onto the machine |

`edit`, `dump`, and `setup` share one set of StackOps user files:

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
| `data` | Interactively add a backup entry and install its YAML schema |
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
| `register` | Register a file or directory into the user mapper |
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

Register a new config file or directory into the self-managed dotfiles area and, by default, record that mapping in the user mapper.

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
| `--section`, `-S` | Section name to write inside the user mapper |
| `--os`, `-o` | Restrict the mapping to one OS or a comma-separated list |
| `--shared`, `-h` | Place the managed file under a shared layout when using `--destination` |
| `--record`, `-r` | Record the mapping in the user mapper file |

Examples:

```bash
# Register a private file and record it in the default mapper section
devops config dotfiles register ~/.config/htop/htoprc --sensitivity private

# Register a public directory with symlink semantics
devops config dotfiles register ~/.config/nvim --method symlink --sensitivity public --section editors
```

#### export

Package and encrypt `~/dotfiles` for transfer to another machine.

```bash
devops config dotfiles export <password>
```

Optional transfer flags:

| Option | Description |
|--------|-------------|
| `--over-internet`, `-i` | Internet-transfer flag present in the CLI, but the current implementation is not finished |
| `--over-ssh`, `-s` | Use SSH/SCP-style transfer |

#### import

Import an encrypted dotfiles archive from a local path or URL.

```bash
devops config dotfiles import --url /path/to/dotfiles.zip.enc --pwd <password>
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

Secrets commands live under `devops vault secrets`. They manage StackOps secrets files and define environment variables from them. When `search` is run without `--source`, it reads the current directory's `.stackops/secrets/secrets.json` when that file exists and otherwise reads the global source-of-truth secrets file.

```bash
devops vault secrets search github personal-access-token
devops vault secrets s aws dev iam-access-key
devops vault secrets s AWS_ACCESS_KEY_ID
devops vault secrets search --interactive
devops vault secrets s -i aws
devops vault secrets search --verbose aws dev iam-access-key
devops vault secrets search --name aws-dev --tag iam-access-key
devops vault secrets search --name aws-dev --tag session-token
devops vault secrets search -s g bitwarden
devops vault secrets s -s b github token
devops vault secrets s --all-matches -s g cloudf
devops vault secrets s -i -P github
devops vault secrets search --path ~/private/team-secrets.json aws dev
devops vault secrets subset ./secrets.json --path ~/private/team-secrets.json
devops vault secrets subset ./team-secrets.json -s global
devops vault secrets add
devops vault secrets a --create
```

By default, the query terms must identify exactly one `entries[].secrets[].keyValues` object. Terms are case-insensitive substring matches, and all terms must match somewhere across login name/tags/accountName, secret name/tags/scopes, metadata, or environment variable keys. When one `keyValues` object is selected, all variables in that object are loaded together, for example an AWS access key pair plus region.

Use `--all-matches`, `-a` to load every matching `keyValues` object. Repeated environment variable names are deduplicated when they resolve to the same environment value; the command fails if matched bundles assign different values to the same name.

Use `devops vault secrets search` or its alias `devops vault secrets s` to select and load a secret bundle. Use `--interactive`, `-i` to choose a matching secret bundle with the TV fuzzy picker. If terms or exact selectors are provided, they pre-filter the picker list.

After an interactive selection, StackOps prints a `jq` command for the selected login entry, for example `jq '.entries[3]' ~/.stackops/secrets/secrets.json`.

Use `--preview-secrets`, `-P` with `--interactive`, `-i` to include secret values and the full selected login entry in the picker preview. Without it, the preview only shows metadata and environment variable names.

Use `--verbose`, `-v` to print the selected bundle and environment variable keys without printing secret values.

For script-stable matching, use exact selectors. `--name`, `-n` matches `entries[].name`; `--tag`, `--tags`, `-t` requires an exact login or secret tag and can be repeated; `--key`, `-k` requires an exact environment variable key. More specific selectors are also available: `--secret-name`, `-N`; `--login-tag`, `-l`; `--secret-tag`, `-T`; and `--scope`, `-S` for values inside `entries[].secrets[].scopes`. Exact selectors are case-sensitive and can be combined with query terms.

Use `search --source`, `-s` to explicitly choose `local`, `global`, or `both`. The one-letter aliases are `l`, `g`, and `b`. With `both`, missing source files are warned and skipped as long as at least one source exists. Use `--path`, `-p` to explicitly select another local secrets JSON file; a missing `--path` file is an error rather than a reason to use the global source.

Use `devops vault secrets subset OUTPUT_PATH` to choose top-level `entries[]` interactively from one source file and write a `secrets.json`. The picker preview shows labels, tags/scopes, secret bundle names, and environment variable names, but not secret values. By default, the command creates a new file and refuses an existing output path. Use `--on-conflict`, `-o` with `append`/`a` to add selected entries to an existing output file, `overwrite`/`o` to replace the output file, or `throw-error`/`t` to keep the default refusal behavior.

Use `devops vault secrets add` or `devops vault secrets a` to step through prompts for a new login entry and append it to one file. It defaults to the local source and accepts `--source`, `-s` with `local|global`, `--path`, and `--create`. To open a secrets file in an editor, use `devops config edit secrets`.

### dump

Write a packaged example file and its schema, by default under `.stackops/examples` in the current working directory.

```bash
devops config dump <config|layouts|dotfiles|data|secrets> [OPTIONS]
```

```bash
devops config dump layouts
devops config dump secrets --data
devops config dump secrets --schema
devops config dump config --default-path
devops config dump config --default-path --force
```

Key options:

| Option | Description |
|--------|-------------|
| `--data`, `-d` | Write only the example data file |
| `--schema`, `-s` | Write only the schema file |
| `--default-path`, `-p` | Write to the real user file path from the table above instead of `.stackops/examples` |
| `--force`, `-f` | Overwrite existing output files |

When neither `--data` nor `--schema` is passed, both files are written. The command refuses to write anything if any selected output already exists, unless `--force` is passed. The `dotfiles` and `data` examples are the packaged library mappers, so dumping them to `--default-path` copies every library entry into the user mapper; use `devops config edit` for an empty user mapper instead.

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
