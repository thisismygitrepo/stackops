# cloud

`cloud` is the direct entrypoint for cloud sync, copy, mount, and SSH file transfer workflows.

---

## Usage

```bash
cloud [OPTIONS] COMMAND [ARGS]...
```

Current top-level commands:

| Command | Purpose |
|---------|---------|
| `sync` | Synchronize files or folders between local and cloud storage |
| `copy` | Upload or download files and folders |
| `mount` | Mount configured cloud storage locally |
| `ftpx` | Transfer files through SSH |

---

## sync

Synchronize files or folders between a source and target path.

```bash
cloud sync [OPTIONS] SOURCE TARGET
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--config`, `-c` | Path to `.ve.yaml` |
| `--transfers`, `-t` | Number of transfer threads |
| `--root`, `-R` | Remote root |
| `--key`, `-k` | Encryption key |
| `--pwd`, `-P` | Encryption password |
| `--encrypt`, `-e` | Decrypt after receiving |
| `--zip`, `-z` | Unzip after receiving |
| `--bisync`, `-b` | Bidirectional sync |
| `--delete`, `-D` | Delete files in remote that are not in local |
| `--verbose`, `-v` | Show verbose sync details |

Example:

```bash
cloud sync ~/documents remote:documents --bisync
```

---

## copy

Upload or download files and folders between local and cloud paths.

```bash
cloud copy [OPTIONS] SOURCE TARGET
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--overwrite`, `-o` | Overwrite existing file |
| `--share`, `-s` | Share file or directory |
| `--relative2home`, `-r` | Treat paths as relative to `myhome` |
| `--root`, `-R` | Remote root |
| `--key`, `-k` | Encryption key |
| `--password`, `-p` | Encryption password |
| `--encrypt`, `-e` | Encrypt before sending |
| `--zip`, `-z` | Unzip after receiving |
| `--os-specific`, `-O` | Choose a path specific to the current OS |
| `--config`, `-c` | Path to `.ve.yaml` |

Example:

```bash
cloud copy ./report.pdf remote:reports/report.pdf
```

---

## mount

Mount a configured cloud storage target locally.

```bash
cloud mount [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--cloud`, `-c` | Cloud to mount |
| `--destination`, `-d` | Mount destination |
| `--network`, `-n` | Network mount target |
| `--backend`, `-b` | Terminal backend on Linux or macOS |
| `--interactive`, `-i` | Choose the cloud interactively |

---

## ftpx

Transfer files through SSH.

```bash
cloud ftpx [OPTIONS] SOURCE TARGET
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--recursive`, `-r` | Send recursively |
| `--zipFirst`, `-z` | Zip before sending |
| `--cloud`, `-c` | Transfer through the cloud |
| `--overwrite-existing`, `-o` | Overwrite existing remote files when sending local to remote |

Example:

```bash
cloud ftpx localmachine:/tmp/archive remotehost:/tmp/archive --recursive
```

---

## Getting help

Use live help to inspect the exact options available in your installed version:

```bash
cloud --help
cloud sync --help
cloud copy --help
cloud mount --help
cloud ftpx --help
```
