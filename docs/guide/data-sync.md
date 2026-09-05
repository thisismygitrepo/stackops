# Data Sync

StackOps currently splits data movement into two layers:

- `devops data` for repeatable named backups and local file/folder encryption
- `cloud` for direct source/target copy, sync, mount, SSH transfer, and OneDrive access through Microsoft Graph

---

## Repeatable backups with `devops data`

Start with the current backup workflow entrypoint:

```bash
devops data --help
```

Current subcommands:

- `sync`
- `register`
- `display`
- `subset`
- `edit`
- `encrypt`
- `decrypt`

### Register a backup item

Add one file or directory to the user backup config:

```bash
devops data register ~/.config/wezterm --group dotfiles --encryption asymmetric
devops data register ~/.config/wezterm --group dotfiles --encryption symmetric --password "$STACKOPS_BACKUP_PASSWORD"
devops data register ~/Documents/work --group documents --path-cloud backups/work --os linux,darwin
```

`register` records fields such as:

- `path_local`
- `path_cloud`
- `share_url`
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
Every persisted entry requires `encryption: symmetric`, `encryption: asymmetric`, or `encryption: null`. `null` means plaintext. The short values `s` and `a` are CLI aliases only; YAML stores the full mode names.
`--encryption`, `-e` is the sole encryption switch for registration. Omit it to record `encryption: null`. A password supplies credentials but does not select a mode, so `--password` requires explicit `--encryption symmetric` and is never stored in `mapper/data.yaml`.

### Run a backup or restore

`devops data sync` is direction-based:

- `up` backs up to the cloud
- `down` restores from the cloud

Examples:

```bash
# Back up every registered item
devops data sync up --which all

# Restore one group from the user backup config
devops data sync down -s user --which dotfiles

# Back up one item using a specific cloud profile
devops data sync up --cloud myremote --which dotfiles.wezterm

# Use one password for entries that explicitly store encryption: symmetric
devops data sync up --which dotfiles.wezterm --password "$STACKOPS_BACKUP_PASSWORD"

# Restore one item from its recorded share_url instead of rclone
devops data sync down --use-link --which dotfiles.wezterm
```

`--use-link` is only valid for `down`. Every selected entry must have a non-null `share_url`; otherwise StackOps exits with the affected entry names and tells you to either remove `--use-link` or add valid links.

These commands perform the transfers; they do not only print a plan.

### Inspect, subset, or edit the backup config

```bash
devops data display
devops data subset ./laptop-data.yaml --which dotfiles.wezterm
devops data edit -s user
devops data edit -s library
```

`display` renders the registered user entries. `subset` writes selected entries to a standalone YAML file and has its own output-file `--on-conflict` policy. Use `--source`, `-s` on data sync, subset, and edit commands to choose the configuration source where supported.

---

## Local encryption and decryption

Use `devops data encrypt` and `decrypt` for local GPG artifacts without a cloud transfer or backup registration:

```bash
devops data encrypt ./notes.txt
devops data decrypt ./notes.txt.gpg --output ./restored-notes.txt
devops data encrypt ./project --encryption asymmetric --compression tar.gz
devops data decrypt ./project.tar.gz.gpg --encryption asymmetric --output ./restored-project
```

Both commands preserve the source and refuse an existing output. Symmetric encryption is the default and prompts for a password when `--password`, `-p` is omitted. Pass `--encryption asymmetric` for GPG keys; encryption accepts `--recipient`, `-r`, defaulting to the user's own key. Folders are archived before encryption using `--compression`, `-c`: `zip` (default), `tar.gz`, `tar.bz2`, or `tar.xz`.

Without `--output`, `-o`, encryption writes beside the source with a `.gpg` suffix, plus the archive suffix for a folder. Decryption writes beside the encrypted file with those suffixes removed and extracts recognized folder archives.

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
- `onedrive`

### Copy

One-off upload or download:

```bash
cloud copy ./report.pdf remote:reports/report.pdf
cloud copy remote:reports/report.pdf ./report.pdf
cloud copy ./report.pdf remote:reports/report.pdf --record-name report --record-group shared
cloud copy ./report.pdf remote:reports/report.pdf --share-type v --record-name report --record-group shared
```

`--record-name` writes the upload into the user `mapper/data.yaml` entry. Add `--share-scope` or `--share-type` when you also want the generated URL saved there instead of writing a `.share_url_*` sidecar file.

### Sync

Ad hoc directory synchronization:

```bash
cloud sync ~/documents remote:documents
cloud sync ~/documents remote:documents --bisync --resync
cloud sync ~/documents remote:documents --bisync
```

`--resync` requires `--bisync` and initializes or recovers its state; omit it for normal bidirectional runs. Bisync propagates deletions. For one-way sync, `--delete` removes destination-only files; with bisync it changes deletion timing.

`cloud sync` rejects `--pwd`, `--encryption`, and `--zip` because incremental sync cannot stage GPG or ZIP artifacts. Use `cloud copy` when a transfer needs encryption or compression.

### Mount

Mount a configured remote locally:

```bash
cloud mount
```

Mount selection is interactive by default. To choose a remote directly, use `cloud mount --cloud remote --no-interactive`.

### FTP-over-SSH

Transfer files between `machine:path` endpoints:

```bash
cloud ftpx localmachine:/tmp/archive remotehost:/tmp/archive --recursive
```

### OneDrive through Microsoft Graph

The `onedrive` group manages configured Microsoft Graph accounts and supports listing, searching, uploading, downloading, and deleting drive items:

```bash
cloud onedrive --help
cloud onedrive accounts
```

---

## Config sources

The `cloud` commands use explicit CLI flags and configured defaults for transfer behavior. For `cloud copy`, options include:

- `--root`
- `--encryption`
- `--zip`
- `--relative2home`

If a remote path starts with `:`, StackOps fills in the cloud name from the configured default cloud.

`cloud copy` uses `--encryption`, `-e` as the sole encryption switch. Accepted CLI values are `symmetric`/`s` and `asymmetric`/`a`; omitting the option keeps the transfer plaintext. Password options require an explicit symmetric mode. These staging options are not supported by `cloud sync`.

Use `devops data` when you want durable named backup sets. Use `cloud copy` or `cloud sync` when you already know the exact source and destination you want to move.
