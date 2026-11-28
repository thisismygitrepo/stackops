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
| `transfer` | Transfer files through SSH using `machine:path` endpoints |
| `onedrive` | Access OneDrive accounts and files through Microsoft Graph |

The command also defines hidden one-letter aliases for the same actions: `s`, `c`, `m`, `t`, and `o`.

`cloud --non-interactive`/`-N` (or `STACKOPS_NON_INTERACTIVE`) never prompts or opens a picker; it is enabled automatically without a terminal.

---

## Defaults

The rclone-backed commands use defaults from `stackops.utils.cloud.defaults.read_default_cloud_config()` where applicable:

- remote root: `myhome`
- cloud name: `mycloud101`
- `zip`, `share`, `overwrite`, `os_specific`, `rel2home`: `False`
- `pwd`: unset
- encryption mode: unset; `copy` supports encryption and ZIP staging, while `sync` transfers directory contents directly
- if a remote path starts with `:`, StackOps fills in the cloud name from the configured default rclone remote

---

## `sync`

```bash
cloud sync [OPTIONS] SOURCE TARGET
```

Current options from live help:

| Option | Meaning |
| --- | --- |
| `--transfers`, `-T` | Number of concurrent sync transfers (default `10`) |
| `--root`, `-R` | Remote root |
| `--bisync`, `-b` | Bidirectional sync |
| `--resync`, `-r` | Initialize or recover bidirectional sync state; requires `--bisync` |
| `--delete`, `-D` | Delete destination-only files during one-way sync; with bisync, changes deletion timing rather than enabling deletion |
| `--verbose`, `-v` | Show the rclone command being executed |
| `--json`, `-j` | Print a completion receipt as JSON |

Example:

```bash
cloud sync ~/documents remote:documents
cloud sync ~/documents remote:documents --bisync --resync
cloud sync ~/documents remote:documents --bisync
```

Use `--resync` for the first bidirectional run or to recover its state; omit it for normal runs. Bisync propagates deletions even without `--delete`. Use `cloud copy` for encrypted or compressed transfers; incremental sync does not stage ZIP or GPG artifacts.

---

## `copy`

```bash
cloud copy [OPTIONS] SOURCE TARGET
```

Current options from live help:

| Option | Meaning |
| --- | --- |
| `--transfers`, `-T` | Number of concurrent file transfers (default `32`) |
| `--overwrite`, `-o` | Overwrite an existing destination file |
| `--share-scope`, `-s` | Share link scope: `anonymous`/`a` or `organization`/`o`; implies sharing |
| `--share-type`, `-t` | Share link type: `view`/`v`, `edit`/`e`, or `embed`/`m`; implies sharing |
| `--record-group`, `-g` | Group name for the recorded upload (default `default`); used when `--record-name` is passed |
| `--record-name`, `-n` | Record the upload in `mapper/data.yaml` with this entry name |
| `--record-os`, `-F` | Comma-separated OS filter for recorded uploads; defaults to `linux,darwin,windows` |
| `--relative-to-home`, `-r` | Treat remote paths as relative to `myhome` |
| `--root`, `-R` | Remote root |
| `--password`, `-p` | Symmetric GPG encryption password; implies symmetric encryption when no mode is specified |
| `--password-name`, `-P` | StackOps secret containing the symmetric password; implies symmetric encryption when no mode is specified |
| `--password-file`, `-f` | Read the encryption password from a file; `-` reads standard input |
| `--password-env`, `-E` | Environment variable containing the encryption password |
| `--encryption`, `-e` | Enable encryption with `symmetric`/`s` or `asymmetric`/`a`; defaults to symmetric with a password, otherwise plaintext |
| `--zip`, `-z` | Compress uploads and extract downloads |
| `--os-specific`, `-O` | Choose a path specific to the current OS |
| `--json`, `-j` | Print resolved paths and share links as JSON |

Example:

```bash
cloud copy ./report.pdf remote:reports/report.pdf
cloud copy ./report.pdf remote:reports/report.pdf --encryption a
cloud copy ./report.pdf remote:reports/report.pdf --encryption symmetric --password "$STACKOPS_BACKUP_PASSWORD"
cloud copy ./report.pdf remote:reports/report.pdf --record-name report --record-group shared
cloud copy ./report.pdf remote:reports/report.pdf --share-type v --record-name report --record-group shared
cloud copy ./report.pdf remote:reports/report.pdf -s o -t v
```

`--record-name` saves the upload in `mapper/data.yaml`. Its required `encryption` field is persisted as `symmetric`, `asymmetric`, or `null` for plaintext. When `--share-scope` or `--share-type` is present, the generated URL is printed and stored in that entry.
`--share-scope` and `--share-type` are generic StackOps options. StackOps resolves the rclone config name to its backend type and maps supported providers internally; for OneDrive this becomes `--onedrive-link-scope` and `--onedrive-link-type`. Backends without provider-specific scope/type controls use plain `rclone link` for `anonymous` + `view`, and reject unsupported stronger options.
Use `--encryption symmetric`/`s` for password-based GPG or `--encryption asymmetric`/`a` for GPG public/private keys. `--password` and `--password-name` imply symmetric encryption when the mode is omitted. Omit both encryption and password options for plaintext. Choose only one password source among `--password`, `--password-name`, `--password-file`, and `--password-env`.

---

## `mount`

```bash
cloud mount [OPTIONS] [CLOUDS]...
```

Current options:

| Option | Meaning |
| --- | --- |
| `CLOUDS` | Cloud names, separated by spaces or commas; omit to select interactively |
| `--destination`, `-d` | Mount destination |
| `--network`, `-n` | Windows network mount target, for example `X:` |
| `--backend`, `-b` | Session multiplexer on Linux/macOS: `tmux`/`t` or `tuios`/`u` |
| `--daemon`, `-D` | Keep mounts running in the background independently of a terminal |
| `--timeout`, `-T` | Seconds to wait for each background mount (default `30`) |
| `--json`, `-j` | Print background mount locations and process identities as JSON; requires `--daemon` and explicit cloud names |

Current defaults:

- backend: `default_session_multiplexer` from the StackOps config, otherwise `tmux`
- mount location: `~/data/rclone/<cloud>` unless `--destination` or `--network` is given
- interactive selection: used when cloud names are omitted

Example:

```bash
cloud mount drive,dropbox
cloud mount drive --daemon --json
```

---

## `transfer`

```bash
cloud transfer [OPTIONS] SOURCE TARGET
```

`SOURCE` and `TARGET` use `machine:path` notation.

Current options:

| Option | Meaning |
| --- | --- |
| `--recursive`, `-r` | Transfer recursively |
| `--zip-first`, `-z` | Zip before sending |
| `--cloud`, `-c` | Transfer through the cloud |
| `--overwrite`, `-o` | Overwrite existing remote files when sending local to remote |
| `--password-file`, `-f` | Read the SSH password from a file; `-` reads standard input |
| `--password-env`, `-E` | Environment variable containing the SSH password |

Example:

```bash
cloud transfer localmachine:/tmp/archive remotehost:/tmp/archive --recursive
```

---

## `onedrive`

```bash
cloud onedrive [OPTIONS] COMMAND [ARGS]...
```

This group manages OneDrive accounts and files directly through Microsoft Graph. Its current commands are:

| Command | Purpose |
| --- | --- |
| `add-account` | Add an account name and Microsoft application client ID |
| `auth` | Authenticate a configured account with Microsoft |
| `status` | Show account and storage status |
| `accounts` | List configured OneDrive accounts |
| `list` | List a remote folder |
| `search` | Search the drive, optionally as JSON |
| `download` | Download a remote file |
| `upload` | Upload a local file, optionally replacing the remote item |
| `delete` | Move a remote item to the recycle bin |
| `config-path` | Print the global StackOps secrets path used for account configuration |

File operations select an account with `--account/-a`. Omit it to use the only configured account or enter its name interactively. Most commands accept `--json/-j` for JSON output, and `delete --yes/-y` skips the confirmation prompt. `add-account`, `auth`, and `status` take the account name as a positional argument:

```bash
cloud onedrive add-account work --client-id <microsoft-client-id>
cloud onedrive auth work
cloud onedrive accounts
cloud onedrive list / --account work
cloud onedrive download /report.pdf ./report.pdf --account work
```

---

## Getting help

```bash
cloud --help
cloud sync --help
cloud copy --help
cloud mount --help
cloud transfer --help
cloud onedrive --help
```
