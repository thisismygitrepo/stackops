# Data Sync

StackOps currently splits data movement into two layers:

- `devops data` for repeatable, named backup entries stored in the backup config
- `cloud` for direct source/target copy, sync, mount, and SSH file transfer

---

## Repeatable backups with `devops data`

Start with the current backup workflow entrypoint:

```bash
devops data --help
```

Current subcommands:

- `sync`
- `register`
- `edit`

### Register a backup item

Add one file or directory to the user backup config:

```bash
devops data register ~/.config/wezterm --group dotfiles --zip --encrypt
devops data register ~/Documents/work --group documents --path-cloud backups/work --os linux,darwin
```

`register` records fields such as:

- `path_local`
- `path_cloud`
- `encrypt`
- `zip`
- `rel2home`
- `os`

Representative entry:

```toml
[dotfiles]
wezterm = { path_local = "~/.config/wezterm", path_cloud = "^", encrypt = true, zip = true, rel2home = true, os = "linux,darwin" }
```

`^` means "derive the remote path from `path_local`".

### Generate backup or restore commands

`devops data sync` is direction-based:

- `up` backs up to the cloud
- `down` restores from the cloud

Examples:

```bash
# Generate commands for every registered item
devops data sync up --which all

# Restore one group from the user backup config
devops data sync down --repo user --which dotfiles

# Restrict the generated commands to one item and one cloud profile
devops data sync up --cloud myremote --which dotfiles.wezterm
```

### Inspect or edit the backup config

```bash
devops data edit --repo user
devops data edit --repo library
```

---

## Direct transfers with `cloud`

Use `cloud` when you want explicit source/target operations instead of registered backup items:

```bash
cloud --help
```

Current top-level commands:

- `sync`
- `copy`
- `mount`
- `ftpx`

### Copy

One-off upload or download:

```bash
cloud copy ./report.pdf remote:reports/report.pdf
cloud copy remote:reports/report.pdf ./report.pdf
```

### Sync

Ad hoc directory synchronization:

```bash
cloud sync ~/documents remote:documents
cloud sync ~/documents remote:documents --bisync
```

### Mount

Mount a configured remote locally:

```bash
cloud mount --interactive
```

### FTP-over-SSH

Transfer files between `machine:path` endpoints:

```bash
cloud ftpx localmachine:/tmp/archive remotehost:/tmp/archive --recursive
```

---

## Config sources

The `cloud` commands can load defaults from a nearby `.ve.yaml` file or from an explicit `--config` path. The live help shows the current flags for ad hoc operations such as:

- `--config`
- `--root`
- `--encrypt`
- `--zip`
- `--relative2home`

Use `devops data` when you want durable named backup sets. Use `cloud copy` or `cloud sync` when you already know the exact source and destination you want to move.
