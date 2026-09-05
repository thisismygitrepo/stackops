# cloud

`cloud` is the direct entrypoint for StackOps's cloud copy, sync, mount, SSH-transfer, and Microsoft Graph OneDrive helpers.

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
| `onedrive` | Access OneDrive accounts and files through Microsoft Graph |

The command also defines hidden one-letter aliases for the same actions: `s`, `c`, `m`, `f`, and `o`.

---

## Defaults

The rclone-backed commands use defaults from `stackops.utils.cloud.defaults.read_default_cloud_config()` where applicable:

- remote root: `myhome`
- cloud name: `mycloud101`
- `zip`, `share`, `overwrite`, `os_specific`, `rel2home`: `False`
- `pwd`: unset
- encryption mode: unset; `copy` supports explicit encryption, while `sync` rejects encryption and ZIP staging options
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
| `--pwd`, `-P` | Listed by the CLI but rejected by sync; use `cloud copy` for encrypted transfers |
| `--encryption`, `-e` | Listed by the CLI but rejected by sync; use `cloud copy` for encrypted transfers |
| `--zip`, `-z` | Listed by the CLI but rejected by sync; use `cloud copy` for compressed transfers |
| `--bisync`, `-b` | Bidirectional sync |
| `--resync`, `-r` | Initialize or recover bidirectional sync state; requires `--bisync` |
| `--delete`, `-D` | Delete destination-only files during one-way sync; with bisync, changes deletion timing rather than enabling deletion |
| `--verbose`, `-v` | Show the rclone command being executed |

Example:

```bash
cloud sync ~/documents remote:documents
cloud sync ~/documents remote:documents --bisync --resync
cloud sync ~/documents remote:documents --bisync
```

Use `--resync` for the first bidirectional run or to recover its state; omit it for normal runs. Bisync propagates deletions even without `--delete`. Incremental sync cannot stage ZIP or GPG artifacts, so it rejects `--pwd`, `--encryption`, and `--zip`; use `cloud copy` for those transfers.

---

## `copy`

```bash
cloud copy [OPTIONS] SOURCE TARGET
```

Current options from live help:

| Option | Meaning |
| --- | --- |
| `--transfers`, `-T` | Number of concurrent file transfers |
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
| `--zip-first`, `-z` | Zip before sending |
| `--cloud`, `-c` | Transfer through the cloud |
| `--overwrite-existing`, `-o` | Overwrite existing remote files when sending local to remote |

Example:

```bash
cloud ftpx localmachine:/tmp/archive remotehost:/tmp/archive --recursive
```

---

## `onedrive`

```bash
cloud onedrive [OPTIONS] COMMAND [ARGS]...
```

This group manages OneDrive accounts and files directly through Microsoft Graph. Its current commands are:

| Command | Purpose |
| --- | --- |
| `add` | Add an account name and Microsoft application client ID |
| `auth` | Authenticate a configured account with Microsoft |
| `status` | Show account and storage status |
| `accounts` | List configured OneDrive accounts |
| `ls` | List a remote folder |
| `search` | Search the drive, optionally as JSON |
| `download` | Download a remote file |
| `upload` | Upload a local file, optionally replacing the remote item |
| `delete` | Move a remote item to the recycle bin |
| `config-path` | Print the global StackOps secrets path used for account configuration |

Most file operations require `--account-name/-a`. Start by adding and authenticating an account:

```bash
cloud onedrive add --account-name work --client-id <microsoft-client-id>
cloud onedrive auth --account-name work
cloud onedrive accounts
cloud onedrive ls --account-name work /
```

---

## Getting help

```bash
cloud --help
cloud sync --help
cloud copy --help
cloud mount --help
cloud ftpx --help
cloud onedrive --help
```
