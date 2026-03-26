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
| `--repo`, `-r` | Load backup entries from `library`, `user`, or `all` |

If `--which` is omitted, the command falls back to interactive selection. The selector accepts:

- a group name such as `dotfiles`
- a specific item such as `dotfiles.bashrc`
- `all` for every applicable entry

Examples:

```bash
# Generate commands to back up every registered item
devops data sync up --which all

# Generate commands to restore one group from the user backup config
devops data sync down --repo user --which dotfiles

# Generate commands for selected entries with a specific cloud config
devops data sync up --cloud myremote --which dotfiles.bashrc,history.shell
```

`devops data sync` filters entries by the current OS and then prints the generated `cloud copy` script based on each item's `os`, `zip`, `encrypt`, and `rel2home` fields.

### register

Add or update one entry inside the user backup configuration file at `~/dotfiles/machineconfig/mapper_data.toml`.

```bash
devops data register [OPTIONS] PATH_LOCAL
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--group`, `-g` | Target group/table name inside the config file |
| `--name`, `-n` | Override the generated entry name |
| `--path-cloud`, `-C` | Override the remote path; omit it to let machineconfig deduce one |
| `--zip`, `-z` | Zip before upload |
| `--encrypt`, `-e` | Encrypt before upload |
| `--rel2home`, `-r` | Store the local path relative to your home directory |
| `--os`, `-o` | Restrict the entry to `linux`, `darwin`, `windows`, or a comma-separated list |

Examples:

```bash
# Register a config directory for encrypted, zipped backup
devops data register ~/.config/wezterm --group dotfiles --zip --encrypt

# Register a directory with an explicit cloud path
devops data register ~/Documents/work --group documents --path-cloud backups/work --os linux,darwin
```

If `--name` is omitted, the command generates one from the local path and OS filter.

### edit

Open the backup configuration file in `nano`, `hx`, or `code`.

```bash
devops data edit --editor hx --repo user
```

The user backup config is created automatically if it does not exist yet.

### Backup File Layout

The user backup file uses grouped TOML tables. A representative entry looks like this:

```toml
[dotfiles]
wezterm = { path_local = "~/.config/wezterm", path_cloud = "^", encrypt = true, zip = true, rel2home = true, os = "linux,darwin" }
```

Selection behavior for `devops data sync --which ...`:

- `dotfiles` selects the whole group
- `dotfiles.wezterm` selects one item
- `all` selects every applicable item

The nested help screens render `Usage: devops sync ...`, `devops register ...`, and `devops edit ...`, but the full entrypoints remain `devops data sync ...`, `devops data register ...`, and `devops data edit ...`.

---
