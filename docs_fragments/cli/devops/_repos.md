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
| `config-linters` | Add linter config files to a git repository |
| `cleanup` | Clean repository directories from cache files |

Hidden compatibility aliases still exist for older checkout flows, but the current path is `sync --checkout-to-commit` or `sync --checkout-to-branch`.

### sync

Clone or check out repositories described by a `repos.json` specification.

```bash
devops repos sync [DIRECTORY] [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--specs-path`, `-s` | Explicit path to the `repos.json` specification |
| `--interactive`, `-i` | Choose a backed-up `repos.json` interactively |
| `--checkout-to-commit`, `-ctc` | Check out commits pinned in the specification |
| `--checkout-to-branch`, `-ctb` | Check out the main branch from the specification |

Important behavior from the implementation:

- `--checkout-to-commit` and `--checkout-to-branch` are mutually exclusive
- Without `--specs-path`, machineconfig derives the expected `repos.json` from the target directory
- With `--interactive`, machineconfig searches backed-up `repos.json` files and lets you choose which one to apply

Examples:

```bash
# Clone from the default repos.json associated with a directory
devops repos sync ~/code

# Use an explicit spec file
devops repos sync ~/code --specs-path ~/backups/work/repos.json

# Check out the branches declared in the spec
devops repos sync ~/code --checkout-to-branch

# Interactively choose from backed-up specs
devops repos sync --interactive
```

### register

Scan a directory of repositories and write a `repos.json` specification for it.

```bash
devops repos register [DIRECTORY]
```

`register` currently takes only the optional repository root argument. The generated spec is intended to become the source for future `repos sync` runs.

Example:

```bash
devops repos register ~/code
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
devops repos action ~/code/machineconfig --commit --push
```

### analyze

Analyze repository development over time.

```bash
devops repos analyze REPO_PATH
```

This delegates to the plotting-oriented repository analyzer.

Example:

```bash
devops repos analyze ~/code/machineconfig
```

### guard

Securely sync a git repository to or from cloud storage with encryption.

```bash
devops repos guard REPO [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--cloud`, `-c` | Cloud storage profile name |
| `--message`, `-m` | Commit message for local changes |
| `--on-conflict`, `-o` | Conflict strategy such as `ask`, `push-local-merge`, `overwrite-local`, `stop-on-conflict`, or `remove-rclone-conflict` |
| `--password` | Password for encryption and decryption |

Example:

```bash
devops repos guard ~/code/private-repo --cloud myremote --message "sync before travel"
```

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
| `--resolution`, `-res` | Output resolution |
| `--seconds-per-day`, `-spd` | Playback speed |
| `--start-date` | Lower date bound |
| `--stop-date` | Upper date bound |
| `--title`, `-t` | Visualization title |
| `--self` | Clone and visualize the machineconfig repository |

The current help also exposes additional rendering controls for hidden layers, viewport, avatars, file limits, framerate, background color, and camera mode.

Examples:

```bash
# Interactive visualization
devops repos viz --repo ~/code/machineconfig

# Render to video
devops repos viz --repo ~/code/machineconfig --output machineconfig.mp4 --resolution 1280x720
```

### count-lines

Count Python lines of code in the current state and through repository history.

```bash
devops repos count-lines REPO_PATH
```

Example:

```bash
devops repos count-lines ~/code/machineconfig
```

### config-linters

Copy standard linter config files into a git repository.

```bash
devops repos config-linters [DIRECTORY] [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--linter`, `-t` | Restrict the copy to `ruff`, `mypy`, `pylint`, `flake8`, or `ty` |

Without `--linter`, machineconfig copies the full supported set of linter config files.

Examples:

```bash
devops repos config-linters ~/code/myrepo
devops repos config-linters ~/code/myrepo --linter ruff
```

### cleanup

Clean repository directories from cache files.

```bash
devops repos cleanup [REPO] [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--recursive`, `-r` | Recurse into nested repositories under the given directory |

Without `--recursive`, the target must already be a git repository. With `--recursive`, machineconfig searches for nested `.git` directories and cleans each repository it finds.

Examples:

```bash
# Clean one repo
devops repos cleanup ~/code/machineconfig

# Clean every repo below a root directory
devops repos cleanup ~/code --recursive
```

The nested help screens render shortened usage such as `devops sync ...`, `devops action ...`, or `devops viz ...`, but the full entrypoints remain `devops repos sync ...`, `devops repos action ...`, and `devops repos viz ...`.

---
