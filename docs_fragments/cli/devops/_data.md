## data

Data backup and retrieval operations.

```bash
devops data [SUBCOMMAND] [ARGS]...
```

Back up configured files and directories to cloud storage, retrieve them back, and maintain the backup item registry.

Current `devops data --help` exposes:

| Command | Description |
|---------|-------------|
| `sync` | Generate backup or retrieve commands through `cloud copy` |
| `register` | Add or update a backup entry in the user data-mapping file |
| `subset` | Select entries interactively or with `--which` and write a standalone data-mapping file |
| `edit` | Open the user or library backup configuration file |

### sync

Generate backup or restore commands for registered items.

```bash
devops data sync <up|down> [OPTIONS]
```

`up` means backup to the cloud. `down` means retrieve from the cloud.

Key options from current help:

| Option | Description |
|--------|-------------|
| `--cloud`, `-c` | Select the rclone config name to use |
| `--which`, `-w` | Choose specific items, a whole group, or `all` |
| `--source`, `-s` | Load backup entries from `library`, `user`, or `all` |
| `--use-link`, `-l` | On `down`, download from each entry's `share_url` with requests instead of rclone |

If `--which` is omitted, the command falls back to interactive selection. The selector accepts:

- a group name such as `dotfiles`
- a specific item such as `dotfiles.bashrc`
- `all` for every applicable entry

Examples:

```bash
# Generate commands to back up every registered item
devops data sync up --which all

# Generate commands to restore one group from the user backup config
devops data sync down -s user --which dotfiles

# Generate commands for selected entries with a specific cloud config
devops data sync up --cloud myremote --which dotfiles.bashrc,history.shell

# Restore selected entries from their recorded share_url values
devops data sync down --use-link --which dotfiles.bashrc
```

`devops data sync` filters entries by the current OS and then prints the generated `cloud copy` script based on each item's `path_cloud`, `os`, `zip`, `encryption`, and `rel2home` fields. With `--use-link`, only `down` is allowed, every selected entry must define a non-null `share_url`, and the retrieve path uses direct HTTP downloads instead of rclone.

### register

Add or update one entry inside the user backup configuration file at `~/dotfiles/stackops/mapper/data.yaml`.

```bash
devops data register [OPTIONS] PATH_LOCAL
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--group`, `-g` | Target group/table name inside the config file |
| `--name`, `-n` | Override the generated entry name |
| `--path-cloud`, `-C` | Override the remote path; omit it to let stackops deduce one |
| `--zip`, `-z` | Zip before upload |
| `--encryption`, `-e` | Enable encryption with `symmetric`/`s` or `asymmetric`/`a`; omit for plaintext |
| `--password`, `-p` | Symmetric GPG password; requires `--encryption symmetric` and is not stored |
| `--rel2home`, `-r` | Store the local path relative to your home directory |
| `--os`, `-o` | Restrict the entry to `linux`, `darwin`, `windows`, or a comma-separated list |

Examples:

```bash
# Register a config directory for encrypted, zipped backup
devops data register ~/.config/wezterm --group dotfiles --encryption asymmetric

# Register a directory with an explicit cloud path
devops data register ~/Documents/work --group documents --path-cloud backups/work --os linux,darwin
```

If `--name` is omitted, the command generates one from the local path and OS filter.

### subset

Choose backup entries and write them to a separate YAML configuration.

```bash
devops data subset OUTPUT_PATH [OPTIONS]
```

The command preserves each selected entry's group. Without `--which`, it opens a multi-select `tv` picker. For non-interactive use, pass comma-separated selectors: `group.item` selects one entry, a bare `group` selects every entry in that group, and `all` selects every entry. It reads the user configuration by default; use `--source library` or `-s l` to select from the packaged library configuration.

Output handling is strict:

- `--on-conflict throw-error` (the default) creates a new file and refuses an existing path.
- `--on-conflict overwrite` replaces the complete output configuration.
- `--on-conflict append` merges selected entries into an existing configuration. It refuses an existing `group.item` key instead of replacing it.

The one-letter conflict aliases are `t`, `o`, and `a`.

Examples:

```bash
# Select entries from the user configuration into a new file
devops data subset ./laptop-data.yaml

# Select entries from the packaged library
devops data subset ./linux-data.yaml --source library

# Select one dotfiles entry and the complete history group without opening the picker
devops data subset ./laptop-data.yaml --which dotfiles.wezterm,history

# Add newly selected entries to an existing output file
devops data subset ./laptop-data.yaml --on-conflict append
```

### edit

Open the backup configuration file in `nano`, `hx`, or `code`.

```bash
devops data edit --editor hx -s user
```

Use `--source`, `-s` to choose `user` or `library`. The user backup config is created automatically if it does not exist yet.

### Backup File Layout

The user backup file uses grouped YAML mappings. A representative entry looks like this:

```yaml
dotfiles:
  wezterm:
    path_local: "~/.config/wezterm"
    path_cloud: "^"
    share_url: null
    encryption: asymmetric
    zip: true
    rel2home: true
    os:
      - linux
      - darwin
```

Every persisted entry requires `encryption: symmetric`, `encryption: asymmetric`, or `encryption: null`; `null` means plaintext. `--encryption`, `-e` is the sole encryption switch. Passwords provide symmetric credentials but do not select the mode.

Selection behavior for `devops data sync --which ...`:

- `dotfiles` selects the whole group
- `dotfiles.wezterm` selects one item
- `all` selects every applicable item

The nested help screens render `Usage: devops sync ...`, `devops register ...`, `devops subset ...`, and `devops edit ...`, but the full entrypoints remain under `devops data`.

---
