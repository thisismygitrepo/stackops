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
| `layouts` | `~/dotfiles/stackops/config/layout.yaml` | `layout.schema.json` |
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
| `multiplexer` | Select the default session and agent multiplexers and save them in the StackOps config |
| `data` | Interactively register a backup entry and install its YAML schema |
| `dotfiles` | Interactively register a dotfile and install its YAML schema |
| `layouts` | Install starter terminal layouts and their JSON schema |
| `secrets` | Interactively create the global secrets file and schema |

`multiplexer` writes two keys. `default_session_multiplexer` (`tmux`, `herdr`, `tuios`, or `aoe`) is used by `terminal run`, `run-all`, `attach`, `kill`, `trace`, `summary`, and `export` when `--backend` is omitted; the built-in fallback is `tmux`. `default_agent_multiplexer` (`tuios`, `herdr`, or `aoe`) is used by `agents status` and by `agents parallel` launches when `--backend` is omitted; the built-in fallback is `tuios`. An explicit `--backend` always wins. Commands that support fewer multiplexers (`run-all` supports only tmux and tuios; `export` has no aoe) reject a configured value they cannot use instead of silently switching.

Examples:

```bash
devops config setup cloud
devops config setup agent --agent claude
devops config setup multiplexer --session tuios --agent herdr
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
| `collect` | Collect well-known personal files into `~/dotfiles` and record them in the user mapper |
| `register` | Copy or symlink a file into managed storage and register its mapping |
| `export` | Export `~/dotfiles` for machine migration |
| `import` | Import an exported dotfiles archive |
| `status` | Report mapper sizes, sync state, known dotfiles not in your mapper, and storage, without changing anything |

Open the user mapper itself with `devops config edit dotfiles`.

#### sync

Apply the current dotfile mapping set.

```bash
devops config dotfiles sync <up|down> [OPTIONS]
```

Key arguments and options from current help:

| Item | Description |
|------|-------------|
| `direction` | Required. Use `up` to push default paths into the managed location, or `down` to apply managed files back to default paths |
| `--method`, `-m` | Use `symlink` (default) or `copy` |
| `--source`, `-s` | Select mappings from `library`, `user`, or `all` (default) |
| `--on-conflict`, `-c` | Conflict policy such as `throw-error`, `overwrite-self-managed`, or `overwrite-default-path` |
| `--which`, `-w` | Limit the run to specific mapping names, or use `all` |

If `--which` is omitted, the command falls back to interactive selection.

For library-backed public configs, copy packaged settings first when needed:

```bash
devops config copy-assets settings
```

Examples:

```bash
# Apply all packaged settings with symlinks
devops config dotfiles sync down --source library --method symlink --which all

# Push local changes to your own mappings back into the managed area
devops config dotfiles sync up --source user --method copy
```

#### collect

Build your user mapper from the dotfiles on this machine. It covers two catalogs:

- personal files from the packaged user example (ssh, gpg, rclone, git credentials, and similar), stored under `~/dotfiles/creds/...`;
- your own versions of the library settings (yazi, helix, starship, and so on), stored at the library's relative path under `~/dotfiles` instead of `~/.config/stackops`, e.g. `~/dotfiles/settings/yazi/yazi_linux.toml`.

Each chosen entry is stored in `~/dotfiles`, linked back, and recorded in the user mapper; entries for other operating systems that share the same managed path are recorded too, so other machines only need `sync down`. A recorded settings entry replaces the library entry with the same group and name, so `sync --source library` leaves it alone and `--source all` uses yours.

Collect never touches anything you already manage your own way. It skips an entry when its original links somewhere else, when it is identical to (or links to) the packaged settings, when the original and the managed copy both exist, when its paths overlap a mapping in your mapper, or when your mapper has its own group with the same name. An original that already links to the managed path, or a managed copy whose original is missing, is recorded without moving anything. Re-running adds only new entries.

```bash
devops config dotfiles collect                  # print the plan only
devops config dotfiles collect --interactive    # pick groups from the plan
devops config dotfiles collect --which yazi,ssh # or --which all
```

The Group column of the printed plan lists the values `--which` accepts on this machine.

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
| `--destination`, `-d` | Override the default self-managed destination |
| `--group`, `-S` | Group name to write inside the user mapper |
| `--os`, `-o` | Restrict the mapping to one OS or a comma-separated list |
| `--shared`, `-H` | Place the managed file under a shared layout when using `--destination` |

Examples:

```bash
# Register a file and record it in the default mapper group
devops config dotfiles register ~/.config/htop/htoprc

# Register a directory with symlink semantics
devops config dotfiles register ~/.config/nvim --method symlink --group editors
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

#### status

Read-only overview of your dotfiles on this machine. It changes nothing.

- **Mappers**: groups and entries in your mapper and the library mapper, per OS, and how many library entries yours replace.
- **Sync**: the state of each mapped entry for this OS (configured, missing paths, link mismatch, differing copies), counted for your mapper and the library; your entries that are not configured are listed.
- **Known dotfiles not in your mapper**: what `collect` finds on this machine, by category (collectable, skipped, in your mapper, same as the packaged settings, absent, other OS). Collectable and skipped entries are listed one per row, or one row per group when there are more than 25.
- **Storage**: file count and size of `~/dotfiles` (what `export` archives) and of your managed copies, mapper entries whose managed copy lies outside `~/dotfiles` (export does not carry them), and files in `~/dotfiles/stackops/mapper/files` that no mapper entry references.

Options from current help:

| Option | Description |
|--------|-------------|
| `--mappers`, `-m` | Show the mappers section |
| `--sync`, `-s` | Show the sync section |
| `--radar`, `-r` | Show the known-dotfiles section |
| `--storage`, `-d` | Show the storage section |
| `--expand`, `-e` | List every entry in the shown sections: your mapper's groups and the replaced library entries, every synced entry (yours and the library's), every catalog entry for this OS, and the size of each managed copy |
| `--which`, `-w` | Only these groups, comma-separated, as in `sync` and `collect`. Known-dotfile verdicts still account for your whole mapper, and the `~/dotfiles` total and unreferenced stored files stay global |

The section flags pick what to show; without any, all four are shown. Short flags combine.

```bash
devops config dotfiles status         # all sections, summarized
devops config dotfiles status -msr    # everything but storage
devops config dotfiles status -re     # only known dotfiles, every entry listed
devops config dotfiles status -w ssh,yazi -e  # just these groups, in full
```

### edit

Open one StackOps user file in `hx`, `nano`, or `code`.

```bash
devops config edit <config|layouts|dotfiles|data|secrets> [--custom-path PATH] [--editor hx|nano|code]
```

When the file does not exist yet, it is created with the smallest valid content for its kind, and its schema is installed next to it: a versioned `config.json`, an empty dotfiles or data mapper with its YAML header, and the packaged starters for `layout.yaml` (with its YAML header) and `secrets.json`, which require at least one entry. Secrets files are created with mode `0600`.

Use `--custom-path`, `-p` to edit a file of the same kind somewhere else, for example a workspace secrets file:

```bash
devops config edit secrets --custom-path .stackops/secrets/secrets.json
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

StackOps secrets are managed under `devops vault`. `search` inspects matching bundle labels and environment keys; `load` prepares their values for the calling shell. Neither command prints secret values by default. `search --json` explicitly prints matching entries, including their values; `load` has no `--json` option.

```bash
devops vault search github personal-access-token
devops vault search --interactive
devops vault search mail --all-matches --json
devops vault load --name aws-dev --tag iam-access-key
devops vault load --source user github token
devops vault load --all-matches --source all cloudf
devops vault subset ./team-secrets.json --source user
devops vault add --source user
devops vault init --source workspace
devops vault validate --source workspace
```

The command aliases are `search/s`, `load/l`, `stats/t`, `subset/u`, `add/a`, `path/p`, `init/i`, and `validate/v`. `init` and `validate` require an explicit `--source workspace|user` (aliases `w/u`) or `--custom-path`.

Terms are case-insensitive substring matches across login and secret names, tags, scopes, metadata, and environment keys. By default, selection must identify one bundle. Use `--all-matches`, `-a` for every match or `--interactive`, `-i` to choose with the TV picker. `load --all-matches` rejects conflicting values for the same environment variable. `--preview-secrets`, `-P` shows values in the interactive preview; `--verbose`, `-v` shows metadata without values.

Exact, case-sensitive selectors can be combined with query terms: `--name/-n`, `--secret-name/-N`, `--tag/--tags/-t`, `--login-tag/-l`, `--secret-tag/-T`, `--scope/-S`, and `--key/-k`. Tag, scope, and key options are repeatable.

`--source/-s` accepts `workspace/w` or `user/u`; `search`, `load`, and `stats` also accept `all/a`. `--custom-path/-p` selects exactly one secrets file and overrides `--source`, including `all`. With neither supplied, `search` and `load` prefer an existing workspace file and otherwise use the user file. `stats` defaults to `all`; `subset` and `add` default to `workspace`.

The workspace file is `<workspace-root>/.stackops/secrets/secrets.json`. The root is the enclosing Git repository root, including from a subdirectory, or the current directory when it contains at least two immediate child Git repositories. Reads also include `.stackops/secrets/secrets.json` from each immediate child directory of the root that has one, labelled `workspace:<child>`; commands that write one file use the root file. Outside these locations, explicit `workspace` fails and `all` includes only `user`.

`subset OUTPUT_PATH` interactively selects login entries from one source and writes a secrets file. `--on-conflict/-c throw-error|overwrite|append` controls an existing output file. `add` prompts for a new login entry and appends it; `--create/-c` also permits creating the file. Use `devops config edit secrets` to edit the user file, or pass `--custom-path` for another file.

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
