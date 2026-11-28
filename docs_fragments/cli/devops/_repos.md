## repos

Manage development repositories.

```bash
devops repos [SUBCOMMAND] [ARGS]...
```

Handles cloning, updating, and maintaining development repositories.

Current `devops repos --help` exposes:

| Command | Description |
|---------|-------------|
| `sync` | Clone Git repositories and sync encrypted guard repositories described by a `repos.json` specification |
| `register` | Scan repositories, refresh registrations, and prune missing records under the directory |
| `edit` | Edit and validate the `repos.json` specification |
| `path` | Print the specification and schema paths as JSON |
| `init` | Create a missing specification and its schema without opening an editor |
| `validate` | Validate a specification without opening an editor |
| `list` | List registered repositories with change counts |
| `action` | Run Git status/pull/commit/push actions or a shell command across repositories |
| `version` | Capture, inspect, and restore named repository versions |
| `guard` | Securely sync a git repository to and from cloud storage with encryption |

### sync

Clone the Git repositories and sync the encrypted guard repositories described by a `repos.json` specification.

```bash
devops repos sync [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--specs-path`, `-s` | Explicit path to the `repos.json` specification. Defaults to `~/dotfiles/stackops/mapper/repos.json` |
| `--which`, `-w` | Comma-separated repository names or full destination paths, or `all` (the default) |
| `--interactive`, `-i` | Choose repositories with the `tv` multi-select picker |
| `--checkout-to-commit`, `-c` | Check out commits pinned in the specification |
| `--checkout-to-branch`, `-b` | Check out the branch recorded in the specification |
| `--password`, `-p` | Password for guard archives; otherwise GPG keys are used |
| `--json`, `-j` | Print repository sync results as JSON |

Important behavior from the implementation:

- `--checkout-to-commit` and `--checkout-to-branch` are mutually exclusive
- `--which` cannot be combined with `--interactive`, and `--json` cannot be combined with `--interactive`
- Without `--specs-path`, stackops reads `~/dotfiles/stackops/mapper/repos.json`
- Repository destination paths come from the records inside the spec file
- An existing Git repository is reused instead of cloned again; guard repositories are synced with their encrypted archive

Examples:

```bash
# Clone from the default global repos.json
devops repos sync

# Use an explicit spec file
devops repos sync --specs-path ~/backups/work/repos.json

# Sync only selected repositories
devops repos sync --which stackops,notes

# Check out the branches declared in the spec
devops repos sync --checkout-to-branch
```

### register

Scan a directory of repositories and merge those entries into a `repos.json` specification.

```bash
devops repos register [DIRECTORY] [OPTIONS]
```

By default, `register` updates `~/dotfiles/stackops/mapper/repos.json`. Use `--specs-path` to update another file. Records under the registered directory are refreshed; records missing from that scan are removed from the registry. Records from other roots are preserved. Repository files are not deleted.

`--sync-mode`, `-g` sets the sync destination of the scanned repositories to `guard` or `git`; omit it to keep saved settings. With `--sync-mode guard`, `--cloud`, `-C` selects the rclone storage profile and `--gitignore`, `-I` (`include` or `respect`) decides whether archives contain Git-ignored files. `--interactive`, `-i` prompts for each field.

Examples:

```bash
devops repos register ~/code
devops repos register ~/code --specs-path ~/backups/work/repos.json
devops repos register ~/code/private-repo --sync-mode guard --cloud myremote
```

### edit

Create if missing and open the `repos.json` specification to adjust repository destinations, sync settings, or records.

```bash
devops repos edit
devops repos edit --path ./repos.json --editor code
```

The alias is `e`. `--path` (`-p`) selects another specification, matching `repos path`, `repos init`, and `repos validate`. `--editor` (`-e`) accepts `nano`, `hx`, or `code`, with `hx` as the default. VS Code waits until the file closes before validation runs. `--install-lsp` (`-l`) installs the JSON language server for Helix when it is missing.

The command validates JSON and repository fields after the editor exits. Invalid edits produce an error and a nonzero exit status. A missing specification and its schema are initialized before the editor opens.

### list

List the registered repositories with their change counts.

```bash
devops repos list
devops repos list --guarded --json
```

`--guarded` (`-g`) shows only repositories using encrypted guard sync, `--json` (`-j`) prints destinations, sync settings, and local status as a JSON array, and `--specs-path` (`-s`) reads another specification.

### action

Run status, pull, commit, and push actions, or a shell command, across one repository or a whole tree of repositories.

```bash
devops repos action [DIRECTORY] [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--recursive`, `-r` | Recurse into nested repositories |
| `--command`, `-C` | Run a quoted shell command in every repository |
| `--uv-sync`, `-u` | Run `uv sync` automatically after pulls |
| `--status`, `-s` | Show status across repositories |
| `--pull`, `-P` | Pull changes |
| `--commit`, `-c` | Commit changes |
| `--push`, `-p` | Push changes |
| `--message`, `-m` | Commit message; required with `--commit` |
| `--dry-run`, `-n` | Preview mutating actions without changing repositories |
| `--specs-path`, `-S` | Repository specification containing sync destinations |
| `--password`, `-w` | Password for guard archives; otherwise GPG keys are used |

At least one of `--command`, `--status`, `--pull`, `--commit`, or `--push` is required. `--command` and `--status` each run alone, `--uv-sync` requires `--pull`, and `--dry-run` applies only to pull, commit, and push.

Examples:

```bash
# Pull every repo below a root directory
devops repos action ~/code --recursive --pull

# Pull and run uv sync where relevant
devops repos action ~/code --recursive --pull --uv-sync

# Commit and push one repo
devops repos action ~/code/stackops --commit --push --message "update docs"

# Run a shell command in every repo
devops repos action ~/code --recursive --command "git status --short"
```

### guard

Securely sync a git repository to or from cloud storage with encryption.

```bash
devops repos guard [REPO] [OPTIONS]
```

`REPO` defaults to the current directory.

Key options from current help:

| Option | Description |
|--------|-------------|
| `--cloud`, `-C` | Cloud storage profile name; otherwise the registered or default profile is used |
| `--message`, `-m` | Commit message for local changes |
| `--mode`, `-M` | `merge`/`m` (default) merges both copies, `overwrite-local`/`l` replaces local with remote, and `overwrite-remote`/`r` replaces remote with local. Overwrite modes never merge |
| `--on-conflict`, `-c` | Merge-conflict strategy: `ask`/`a` (default), `stop-on-conflict`/`s`, `merge-accept-remote`/`r`, or `merge-accept-local`/`l` |
| `--password`, `-p` | Password for encryption and decryption; otherwise GPG keys are used |
| `--gitignore`, `-I` | `include` or `respect` Git-ignored files; omit to keep the saved archive setting |
| `--specs-path`, `-s` | Repository specification containing saved guard settings |
| `--create-remote`, `-R` | Allow creating the remote archive from the local repository when none exists. Without it, a missing remote is an error and nothing is uploaded |

Example:

```bash
devops repos guard ~/code/private-repo --cloud myremote --message "sync before travel"
```

The first sync of a repository has no remote archive yet, so it fails until you create one deliberately:

```bash
devops repos guard ~/code/private-repo --cloud myremote --create-remote
```

`merge-accept-remote` and `merge-accept-local` keep the merge in progress, then resolve only the conflicted files by accepting the remote (`--theirs`) or local (`--ours`) side before finalizing the merge commit.

### version

Capture, list, compare, and restore named repository versions:

```bash
devops repos version declare release-1 --message "Ready for release" --directory ~/code
devops repos version list --directory ~/code
devops repos version status release-1 --directory ~/code
devops repos version checkout release-1 --directory ~/code --dry-run
```

`list` (`l`) lists saved versions. `status` (`s`) requires a version identifier and compares it with current repositories. `declare` (`d`) captures a named version and requires `--message` (`-m`); `--recursive` (`-r`) includes nested repositories. `checkout` (`c`) restores a version; `--dry-run` (`-n`) previews it and `--password` (`-p`) decrypts guard archives. `--directory` (`-d`) selects the workspace holding `versions.json` and defaults to the current directory. `list`, `status`, and `checkout` accept `--json` (`-j`).

---
