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
devops data register ~/.config/wezterm --group dotfiles --encryption asymmetric
devops data register ~/.config/wezterm --group dotfiles --password "$STACKOPS_BACKUP_PASSWORD"
devops data register ~/Documents/work --group documents --path-cloud backups/work --os linux,darwin
```

`register` records fields such as:

- `path_local`
- `path_cloud`
- `share_url`
- `encrypt`
- `encryption`
- `zip`
- `rel2home`
- `os`

Representative entry:

```yaml
dotfiles:
  wezterm:
    path_local: "~/.config/wezterm"
    path_cloud: "^"
    share_url: null
    encrypt: true
    encryption: asymmetric
    zip: true
    rel2home: true
    os:
      - linux
      - darwin
```

`^` means "derive the remote path from `path_local`".
`path_cloud` can include a cloud prefix such as `od:/something`.
`share_url` is `null` until a share link exists.
`encryption` is required only when `encrypt` is `true`; use `symmetric` for password-based GPG and `asymmetric` for GPG public/private keys.
Passing `--password` to `register` records `encryption: symmetric` but does not store the password in `mapper/data.yaml`.

### Generate backup or restore commands

`devops data sync` is direction-based:

- `up` backs up to the cloud
- `down` restores from the cloud

Examples:

```bash
# Generate commands for every registered item
devops data sync up --which all

# Restore one group from the user backup config
devops data sync down --source user --which dotfiles

# Restrict the generated commands to one item and one cloud profile
devops data sync up --cloud myremote --which dotfiles.wezterm

# Use one password for selected symmetric entries
devops data sync up --which dotfiles.wezterm --password "$STACKOPS_BACKUP_PASSWORD"

# Restore one item from its recorded share_url instead of rclone
devops data sync down --use-link --which dotfiles.wezterm
```

`--use-link` is only valid for `down`. Every selected entry must have a non-null `share_url`; otherwise StackOps exits with the affected entry names and tells you to either remove `--use-link` or add valid links.

### Inspect or edit the backup config

```bash
devops data edit --source user
devops data edit --source library
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
cloud copy ./report.pdf remote:reports/report.pdf --record --record-name report --record-group shared
cloud copy ./report.pdf remote:reports/report.pdf --share-type v --record --record-name report --record-group shared
```

`--record` requires `--record-name` and writes the upload into the user `mapper/data.yaml` entry. Add `--share-scope` or `--share-type` when you also want the generated URL saved there instead of writing a `.share_url_*` sidecar file.

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

The `cloud` commands rely on explicit CLI flags for transfer behavior. The live help shows the current flags for ad hoc operations such as:

- `--root`
- `--encrypt`
- `--encryption`
- `--zip`
- `--relative2home`

If a remote path starts with `:`, StackOps fills in the cloud name from the configured default cloud.

Use `devops data` when you want durable named backup sets. Use `cloud copy` or `cloud sync` when you already know the exact source and destination you want to move.
