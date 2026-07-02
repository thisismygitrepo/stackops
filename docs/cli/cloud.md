# cloud

`cloud` is the direct entrypoint for StackOps's cloud copy, sync, mount, and SSH-transfer helpers.

---

## Usage

```bash
cloud [OPTIONS] COMMAND [ARGS]...
```

Current top-level commands:

| Command | Purpose |
| --- | --- |
| `sync` | Synchronize files or folders between local and cloud storage |
| `copy` | Upload or download files and folders |
| `mount` | Mount a configured cloud target locally |
| `ftpx` | Transfer files through SSH using `machine:path` endpoints |

The command also defines hidden one-letter aliases for the same actions: `s`, `c`, `m`, and `f`.

---

## Defaults

When a command does not override them, cloud defaults come from `stackops.utils.cloud_defaults.read_default_cloud_config()`:

- remote root: `myhome`
- cloud name: `mycloud101`
- `zip`, `share`, `overwrite`, `os_specific`, `rel2home`: `False`
- `pwd`: unset
- encryption mode: unset, so transfers are plaintext unless `--encryption` is passed
- if a remote path starts with `:`, StackOps fills in the cloud name from the configured default rclone remote

---

## `sync`

```bash
cloud sync [OPTIONS] SOURCE TARGET
```

Current options from live help:

| Option | Meaning |
| --- | --- |
| `--transfers`, `-t` | Number of sync threads |
| `--root`, `-R` | Remote root |
| `--pwd`, `-P` | Symmetric GPG encryption password; requires `--encryption symmetric` |
| `--encryption`, `-e` | Enable encryption with `symmetric`/`s` or `asymmetric`/`a`; omit for plaintext |
| `--zip`, `-z` | Current help text: unzip after receiving |
| `--bisync`, `-b` | Bidirectional sync |
| `--delete`, `-D` | Delete remote files not present locally |
| `--verbose`, `-v` | Show more sync details |

Example:

```bash
cloud sync ~/documents remote:documents --bisync
cloud sync ~/documents remote:documents --encryption a
cloud sync ~/documents remote:documents --encryption symmetric --pwd "$STACKOPS_BACKUP_PASSWORD"
```

`--encryption`, `-e` is the only encryption switch. A password supplies credentials but does not select a mode, so `--pwd` is invalid unless the mode is explicitly `symmetric`.

---

## `copy`

```bash
cloud copy [OPTIONS] SOURCE TARGET
```

Current options from live help:

| Option | Meaning |
| --- | --- |
| `--overwrite`, `-o` | Overwrite an existing destination file |
| `--share-scope`, `-s` | Share link scope: `anonymous`/`a` or `organization`/`o`; implies sharing |
| `--share-type`, `-t` | Share link type: `view`/`v`, `edit`/`e`, or `embed`/`m`; implies sharing |
| `--record-group`, `-g` | Group name for the recorded upload; used when `--record-name` is passed |
| `--record-name`, `-n` | Record the upload in `mapper/data.yaml` with this entry name |
| `--record-os`, `-F` | OS filter for recorded uploads; defaults to all supported OS values |
| `--relative2home`, `-r` | Treat remote paths as relative to `myhome` |
| `--root`, `-R` | Remote root |
| `--password`, `-p` | Symmetric GPG encryption password; requires `--encryption symmetric` |
| `--password-name`, `-P` | StackOps secret containing the symmetric password; requires `--encryption symmetric` |
| `--encryption`, `-e` | Enable encryption with `symmetric`/`s` or `asymmetric`/`a`; omit for plaintext |
| `--zip`, `-z` | Current help text: unzip after receiving |
| `--os-specific`, `-O` | Choose a path specific to the current OS |

Example:

```bash
cloud copy ./report.pdf remote:reports/report.pdf
cloud copy ./report.pdf remote:reports/report.pdf --encryption a
cloud copy ./report.pdf remote:reports/report.pdf --encryption symmetric --password "$STACKOPS_BACKUP_PASSWORD"
cloud copy ./report.pdf remote:reports/report.pdf --record-name report --record-group shared
cloud copy ./report.pdf remote:reports/report.pdf --share-type v --record-name report --record-group shared
cloud copy ./report.pdf remote:reports/report.pdf -s o -t v
```

`--record-name` saves the upload in `mapper/data.yaml`. Its required `encryption` field is persisted as `symmetric`, `asymmetric`, or `null` for plaintext. When `--share-scope` or `--share-type` is present, the generated URL is stored in that entry instead of writing a `.share_url_*` sidecar file.
`--share-scope` and `--share-type` are generic StackOps options. StackOps resolves the rclone config name to its backend type and maps supported providers internally; for OneDrive this becomes `--onedrive-link-scope` and `--onedrive-link-type`. Backends without provider-specific scope/type controls use plain `rclone link` for `anonymous` + `view`, and reject unsupported stronger options.
`--encryption`, `-e` is the only encryption switch: use `symmetric`/`s` for password-based GPG or `asymmetric`/`a` for GPG public/private keys, and omit it for plaintext. `--password` and `--password-name` only provide credentials and require an explicit symmetric mode.

---

## `mount`

```bash
cloud mount [OPTIONS]
```

Current options:

| Option | Meaning |
| --- | --- |
| `--cloud`, `-c` | Cloud name to mount |
| `--destination`, `-d` | Mount destination |
| `--network`, `-n` | Network mount target |
| `--no-interactive`, `-I` | Require `--cloud` instead of choosing interactively from config |

Current defaults:

- backend: `tmux`
- interactive selection: enabled unless `--no-interactive` is passed

---

## `ftpx`

```bash
cloud ftpx [OPTIONS] SOURCE TARGET
```

`SOURCE` and `TARGET` use `machine:path` notation.

Current options:

| Option | Meaning |
| --- | --- |
| `--recursive`, `-r` | Transfer recursively |
| `--zipFirst`, `-z` | Zip before sending |
| `--cloud`, `-c` | Transfer through the cloud |
| `--overwrite-existing`, `-o` | Overwrite existing remote files when sending local to remote |

Example:

```bash
cloud ftpx localmachine:/tmp/archive remotehost:/tmp/archive --recursive
```

---

## Getting help

```bash
cloud --help
cloud sync --help
cloud copy --help
cloud mount --help
cloud ftpx --help
```
