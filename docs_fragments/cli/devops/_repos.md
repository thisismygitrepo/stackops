## repos

Manage development repositories.

```bash
devops repos [SUBCOMMAND] [ARGS]...
```

Handles cloning, updating, analyzing, and maintaining development repositories.

Current `devops repos --help` exposes:

| Command | Description |
|---------|-------------|
| `sync` | Clone repositories described by a `repos.json` specification |
| `register` | Record repositories into a `repos.json` specification |
| `action` | Run pull/commit/push actions across repositories |
| `analyze` | Analyze repository development over time |
| `guard` | Securely sync a git repository to and from cloud storage with encryption |
| `viz` | Visualize repository activity using Gource |
| `count-lines` | Count current Python lines and historical edits |

### sync

Clone or check out repositories described by a `repos.json` specification.

```bash
devops repos sync [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--specs-path`, `-s` | Explicit path to the `repos.json` specification. Defaults to `/home/alex/dotfiles/stackops/mapper/repos.json` |
| `--checkout-to-commit`, `-c` | Check out commits pinned in the specification |
| `--checkout-to-branch`, `-b` | Check out the main branch from the specification |

Important behavior from the implementation:

- `--checkout-to-commit` and `--checkout-to-branch` are mutually exclusive
- Without `--specs-path`, stackops reads `/home/alex/dotfiles/stackops/mapper/repos.json`
- Repository destination paths come from the records inside the spec file

Examples:

```bash
# Clone from the default global repos.json
devops repos sync

# Use an explicit spec file
devops repos sync --specs-path ~/backups/work/repos.json

# Check out the branches declared in the spec
devops repos sync --checkout-to-branch
```

### register

Scan a directory of repositories and merge those entries into a `repos.json` specification.

```bash
devops repos register [DIRECTORY] [OPTIONS]
```

By default, `register` updates `/home/alex/dotfiles/stackops/mapper/repos.json`. Use `--specs-path` to update another file. Records under the registered directory are refreshed, while records from other roots are preserved.

Examples:

```bash
devops repos register ~/code
devops repos register ~/code --specs-path ~/backups/work/repos.json
```

### action

Run pull, commit, and push actions across one repository or a whole tree of repositories.

```bash
devops repos action [DIRECTORY] [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--recursive`, `-r` | Recurse into nested repositories |
| `--uv-sync`, `-u` | Run `uv sync` automatically after pulls |
| `--pull`, `-P` | Pull changes |
| `--commit`, `-c` | Commit changes |
| `--push`, `-p` | Push changes |

At least one of `--pull`, `--commit`, or `--push` is required.

Examples:

```bash
# Pull every repo below a root directory
devops repos action ~/code --recursive --pull

# Pull and run uv sync where relevant
devops repos action ~/code --recursive --pull --uv-sync

# Commit and push one repo
devops repos action ~/code/stackops --commit --push
```

### analyze

Analyze repository development over time.

```bash
devops repos analyze REPO_PATH
```

This delegates to the plotting-oriented repository analyzer.

Example:

```bash
devops repos analyze ~/code/stackops
```

### guard

Securely sync a git repository to or from cloud storage with encryption.

```bash
devops repos guard REPO [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--cloud`, `-C` | Cloud storage profile name |
| `--message`, `-m` | Commit message for local changes |
| `--on-conflict`, `-c` | Conflict strategy such as `ask`, `push-local-merge`, `merge-accept-remote`, `merge-accept-local`, `overwrite-local`, `stop-on-conflict`, or `remove-rclone-conflict` |
| `--password` | Password for encryption and decryption |

Example:

```bash
devops repos guard ~/code/private-repo --cloud myremote --message "sync before travel"
```

`merge-accept-remote` and `merge-accept-local` keep the merge in progress, then resolve only the conflicted files by accepting the remote (`--theirs`) or local (`--ours`) side before finalizing the merge commit.

### viz

Visualize repository history with Gource, either live or rendered to video.

```bash
devops repos viz [OPTIONS]
```

Commonly used options from current help:

| Option | Description |
|--------|-------------|
| `--repo`, `-r` | Repository to visualize |
| `--output`, `-o` | Render to a video file instead of interactive mode |
| `--resolution`, `-R` | Output resolution |
| `--seconds-per-day`, `-D` | Playback speed |
| `--start-date`, `-S` | Lower date bound |
| `--stop-date`, `-E` | Upper date bound |
| `--title`, `-t` | Visualization title |
| `--self`, `-x` | Clone and visualize the stackops repository |

The current help also exposes additional rendering controls for hidden layers, viewport, avatars, file limits, framerate, background color, and camera mode.

Examples:

```bash
# Interactive visualization
devops repos viz --repo ~/code/stackops

# Render to video
devops repos viz --repo ~/code/stackops --output stackops.mp4 --resolution 1280x720
```

### count-lines

Count Python lines of code in the current state and through repository history.

```bash
devops repos count-lines REPO_PATH
```

Example:

```bash
devops repos count-lines ~/code/stackops
```

The nested help screens render shortened usage such as `devops sync ...`, `devops action ...`, or `devops viz ...`, but the full entrypoints remain `devops repos sync ...`, `devops repos action ...`, and `devops repos viz ...`.

---
