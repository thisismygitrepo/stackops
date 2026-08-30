# Security and trust

StackOps is high-trust local automation. It installs software, executes shell and
Python code, copies credentials, changes SSH services and firewall rules, and
transfers data to remote systems. It is not a sandbox, a privilege broker, an
antivirus, or an encrypted secrets manager. Treat a StackOps command with the
same care as the scripts, package-manager commands, and remote services it
invokes.

This page describes the current trust boundaries. It is not a guarantee that an
operation is safe or reversible.

## Credential and session storage

| Data | Default location | Protection and exposure |
| --- | --- | --- |
| Global StackOps secrets | `~/dotfiles/stackops/secrets/secrets.json` | Plaintext JSON. On POSIX, the canonical writer creates a `0700` directory and `0600` file, but other edit paths and pre-existing files may retain broader permissions. StackOps does not configure Windows ACLs. |
| Project-local StackOps secrets | `<project>/.stackops/secrets/secrets.json`, or an explicit `--path` | Plaintext JSON. Do not commit it; a repository is not guaranteed to ignore this path. |
| Secret shell handoff | `~/tmp_results/tmp_scripts/stackops/*.secrets.env.sh` or `*.secrets.env.ps1` | Temporary plaintext, set to mode `0600` on POSIX and intended to be deleted after it is sourced. StackOps does not configure a private Windows ACL. An interruption can leave it behind. Values then remain in the current shell environment and are inherited by child processes. |
| Bitwarden login material | The global StackOps secrets file | `BW_CLIENTID`, `BW_CLIENTSECRET`, and `BW_PASSWORD` are plaintext at rest in that file and are placed in the `bw` child-process environment during login. |
| Bitwarden session and search cache | `~/tmp_results/cache/pwdmgr/cache.json.gpg` | GPG-encrypted to the user's default self-recipient. The cache contains `BW_SESSION` and raw cached `bw list items` results. At runtime, sessions may appear in process arguments, shell state, or command output; retrieved credential data can also be copied to the clipboard. |
| OneDrive CLI authentication | The global StackOps secrets file | Client IDs and refresh tokens are plaintext JSON. Rotated refresh tokens are written back to this file. |
| AI-agent credential profiles | `~/dotfiles/creds/llm/<agent>/<profile>/...` | Byte-for-byte copies with no additional StackOps encryption. On POSIX, credential files are set to mode `0600`; profile-directory permissions follow the local filesystem and umask. StackOps does not configure Windows ACLs. Agents using a keychain or another native secure store are not necessarily profile-backed. |
| Browser profiles | `~/data/browsers-profiles/<browser>/<profile>` | Ordinary browser profile trees, not encrypted by StackOps. They can contain cookies, tokens, history, extensions, and saved site data. MCP browser profiles use the same root. |
| Browser working profiles | The OS temporary directory under `stackops-browser-profiles`, or `<saved-profile>/.tmp/<name>` with `--tmp` | The OS-temporary path is a fresh port-scoped profile. `--tmp` makes a full saved-profile copy, deliberately preserves it after runtime launch begins, including after interruption, and requires manual cleanup after the browser is closed. |
| rclone, SSH, cloud, and other tool credentials | Locations owned by those tools | For example, use `rclone config file` to find the active rclone configuration; repository-guard integration also uses `~/dotfiles/creds/rclone/rclone.conf`. SSH normally uses `~/.ssh`. StackOps does not add encryption to these files. |

The global secrets file can contain the VirusTotal key, cloud tokens, email
credentials, Bitwarden credentials, passwords, and other arbitrary environment
values. Schema validation does not encrypt them. Check permissions after
creating or editing any secrets file, and keep the whole `~/dotfiles/creds` tree
out of source control and unencrypted backups.

`devops config secrets` can intentionally print JSON, preview secret values, or
export values into the caller's environment. `devops vault search` can print or
copy credentials and always handles the selected item's raw JSON. Terminal
scrollback, shell exports, process inspection, clipboard managers, and child
processes are outside the protection provided by file encryption.

`devops vault clean-cache` deletes only the StackOps GPG cache. It does not clear
the current shell, command output, clipboard history, or Bitwarden CLI's own
application state.

## Encryption and transfer

StackOps uses GPG for the operations that explicitly request encryption:

- symmetric transfer encryption uses GPG with AES-256;
- asymmetric transfer encryption uses the user's default self-recipient;
- repository guard archives are GPG-encrypted before upload;
- dotfile export produces a symmetrically encrypted `.zip.gpg` archive; and
- the Bitwarden cache is asymmetrically GPG-encrypted.

Cloud copy and data sync are **not encrypted by StackOps by default**. When an
entry has `encryption: null`, or `cloud copy` is run without `--encryption`, the
source is uploaded without application-level encryption. `--zip` is compression,
not encryption. An rclone `crypt` remote or a provider's server-side encryption
is a separate boundary controlled by that configuration.

Encrypted uploads are staged locally before transfer, and downloads are staged
and decrypted before being placed at their target. Temporary plaintext can
therefore exist on the local filesystem while an operation is running. A hard
termination or power loss can leave staging artifacts behind.

HTTPS, SSH, and provider APIs can protect data in transit, but they do not make a
remote object encrypted end to end. Share links may grant other people access.
The local file name, size, remote path, provider metadata, and access logs can
remain visible even when the payload is GPG-encrypted.

## Remote code and installer provenance

StackOps can obtain and execute code from several places:

- released StackOps packages are installed from PyPI by `uv`;
- the documented live bootstrap downloads scripts from the StackOps GitHub
  `main` branch and runs StackOps from `git+https://github.com/...` without a
  commit pin;
- when `uv` is absent, that bootstrap also downloads and executes Astral's
  `https://astral.sh/uv/install.sh` or `install.ps1` installer;
- the bundled installer catalog is shipped with StackOps;
- an optional user catalog at
  `~/dotfiles/stackops/mapper/installer_data.json` can add installers and
  replace same-named bundled entries;
- catalog entries and direct CLI arguments can select GitHub releases,
  arbitrary HTTP(S) downloads, native package managers, or shell commands;
- bundled installer scripts can add vendor repositories, clone repositories,
  download more scripts, or use pipe-to-shell installers;
- `devops execute` can run a command, a local script, a script from configured
  private/public/library directories, or an unpinned dynamic script fetched
  from the StackOps GitHub `main` branch; and
- `agents add-skill` can invoke `bunx` or `npx` with `skills@latest` to fetch
  skills from third-party GitHub repositories.

Catalog shell commands run through the operating-system shell. Bundled `.sh`,
`.ps1`, and `.py` installers run through Bash, PowerShell (including execution-
policy bypass where used), or Python. They are not sandboxed.

StackOps does not impose a uniform checksum, signature, publisher, or
reproducibility requirement on downloads. Some upstream package repositories
and individual installers perform their own signature checks; others do not.
Generic downloads and direct URLs are not made trustworthy merely because they
use HTTPS or appear in the catalog.

Before installing, inspect the resolved catalog entry and bundled script, review
every upstream URL, pin a version or commit when supported, and verify an
upstream checksum or signature independently. Avoid the live-from-`main`
bootstrap for environments that require reproducible or reviewed code.

## Telemetry and network activity

The StackOps codebase has no intentional first-party usage analytics, automatic
telemetry collector, crash-reporting service, or StackOps-owned telemetry
endpoint. StackOps does persist local operational logs and state, and some
cluster features synchronize operational logs or metadata to the configured
cloud remote.

That does not mean StackOps is offline. A requested operation may contact PyPI,
GitHub, package repositories, vendor installers, Bitwarden, VirusTotal, rclone
remotes, OneDrive, email servers, SSH hosts, `temp.sh`, AI providers, MCP
servers, or other configured services. Those services receive the data needed
for the operation, and installed third-party tools may have their own telemetry
and privacy behavior. StackOps settings that attempt to disable telemetry in
third-party agent tools are not a guarantee about those products.

## Permission and privilege boundaries

- By default, StackOps has the permissions of the invoking user and inherits the
  caller's working directory and environment. There is no filesystem, process,
  network, or environment sandbox.
- A script executed by StackOps can read any file and environment variable that
  the invoking account can read and can change anything that account can change.
- Commands containing `sudo`, native package installers, macOS Remote Login
  changes, and Administrator PowerShell operations cross into system privilege.
  If StackOps itself is launched as root or Administrator, all of its child code
  starts from that larger boundary.
- Generic standalone binary installation on Unix currently sets mode `0777`
  before moving or replacing the executable in `~/.local/bin`. Other local
  users can therefore modify it on a multi-user system. Direct APK installation
  invokes `apk add --allow-untrusted`.
- Remote commands have the authority of the selected SSH or cloud account. SSH
  host-key handling is not uniform: newer network SSH paths prompt with a
  fingerprint, while an older Paramiko path accepts unknown host keys. Verify
  host fingerprints independently for sensitive systems.
- SSH server installation enables and starts the service. On Windows it creates
  an inbound TCP/22 allow rule for all firewall profiles and remote addresses.
  Linux/WSL port changes inspect firewall and SELinux policy but generally
  require the operator to prepare those policies separately.
- Browser automation binds to loopback by default. `agents browser ... --lan`
  exposes the automation relay on `0.0.0.0` with no StackOps authentication
  layer. Anyone able to reach that port may be able to control the authenticated
  browser profile. Use it only on an isolated, trusted network.

Prefer an unprivileged account, elevate only for the specific operation, keep a
second administrative session open for remote network changes, and do not pass
secrets to unreviewed installers or scripts.

## Recovery after interruption or an incorrect operation

There is no global StackOps transaction log or universal undo command. A failed
bulk operation can be partially complete locally and remotely. Before rerunning,
read the last output, inspect the destination and provider state, and determine
which steps already succeeded.

Some paths provide limited transactional behavior:

- cloud downloads stage and restore content before changing the target, and a
  target replacement is restored if the final rename fails;
- an SSH port change snapshots `sshd_config` and any StackOps systemd socket
  override in memory, then attempts to restore and reactivate the old listener
  after a handled failure; and
- some Cloudflare route changes maintain a temporary rollback copy and trap
  ordinary script exits.

These protections do not cover power loss, `SIGKILL`, every subprocess, or every
operation. Installer and package-manager changes are generally not rolled back,
and a bulk install can leave a mix of old, new, and missing tools.

Use this recovery sequence:

1. Stop the affected StackOps, installer, browser, or remote process. Preserve
   terminal output and avoid immediately repeating a destructive command.
2. Inspect both local and remote state. Check the explicit target, the relevant
   package manager or service, cloud-provider objects and shares, and scoped
   leftovers under `~/tmp_results`. Do not delete the whole temporary root.
3. For a forced SSH interruption, use the existing session, a second session,
   or the provider console to restore `/etc/ssh/sshd_config` and any
   `99-stackops-port.conf` socket override, validate the configuration, restart
   SSH, and reconcile firewall/SELinux policy before disconnecting.
4. For an incorrect installer, use the native package manager's repair/removal
   procedure or replace the executable with a separately verified copy. The
   StackOps version marker is bookkeeping, not a backup.
5. For a transfer, restore from the authoritative local, cloud, or offline
   backup and check for partial remote objects or active share links.
6. For secret exposure, remove only the scoped plaintext handoff file, clear the
   shell and clipboard, run `devops vault clean-cache` when applicable, revoke
   sessions, and rotate the credential. Deleting a cache does not revoke it.
7. Close a browser before touching its profile. Then inspect saved-profile
   `.tmp` directories and OS-temporary StackOps profiles for stale copies that
   contain cookies or tokens.

If the affected host is remote, retain console access until service and network
health have been verified from a separate connection.

## Limits of `devops self security` and VirusTotal checks

`devops self security` is a file-scanning, reporting, sharing, downloading, and
installation helper. It is not a host hardening audit, dependency or CVE scanner,
signature verifier, process monitor, behavioral sandbox, or guarantee that a
file is safe.

Important disclosure behavior:

- A VirusTotal scan reads and uploads the complete file to VirusTotal. It is not
  a local hash-only lookup. Do not submit private binaries, credentials,
  customer data, or material you are not permitted to disclose.
- `--record` controls only local CSV recording for an explicit `--path` scan;
  omitting it does not prevent the VirusTotal upload. Installed-app scans record
  by default, and the current CLI has no `--no-record` option.
- An installed-app scan also attempts to upload every discovered directory
  entry to the configured rclone remote named `gdp` and requests a share link,
  even if the VirusTotal scan returned no summary. Discovery does not require
  an entry to be a regular executable before queuing it; VirusTotal skips
  directories, but the `gdp` upload is still attempted. A single explicit
  `--path` scan does not perform this additional `gdp` upload.
- `security upload` and installed-app sharing are provider operations. There is
  no `security` command that recalls a VirusTotal submission or deletes the
  remote object/share. Use the providers' controls.

Installed-app discovery covers non-symlink directory entries larger than 0.1
KiB in StackOps' supported user/system binary directories; it does not verify
that each entry is a regular executable before scheduling it. It does not cover
all applications, libraries, dependencies, install scripts, configurations,
services, persistence mechanisms, or runtime network behavior.

VirusTotal results are point-in-time opinions from the engines that returned a
verdict. StackOps counts `malicious` plus `suspicious` as flagged and calculates
the percentage from malicious, suspicious, harmless, and undetected verdicts.
Timeouts, unsupported types, engine failures, and unknown categories are
excluded from that denominator. A displayed `Clean` result means only zero
reporting verdict engines flagged that submitted sample at that time. False
positives and false negatives remain possible.

File-scan failures can be reduced to a missing summary, and polling has no total
completion deadline. Reports are plaintext CSV files under
`~/.config/stackops/profile/records/<os>/`. A new or filtered scan replaces the
saved reports; the two CSV files are written separately and can be incomplete or
mismatched after interruption.

Reports store an app name, path, timestamp, engine results, and possibly a share
URL, but no cryptographic digest binds the verdict to the later download.
`security install` treats a cached row as eligible when it has at least one
verdict and zero flagged engines, then downloads the recorded Google Drive URL
without a checksum, signature verification, identity comparison, or rescan.
Reports and URLs can be stale or mutable, and concurrent installs can partially
succeed without rollback. Verify the exact downloaded bytes independently
before execution.

## Reporting a vulnerability

Do not report a suspected vulnerability through a public GitHub issue, pull
request, discussion, or terminal transcript containing live secrets.

Email [programmer@usa.com](mailto:programmer@usa.com) with the subject
`[SECURITY] StackOps vulnerability`. Include:

- the affected StackOps version or commit and operating system;
- the affected command or component;
- the security impact and required attacker access;
- minimal reproduction steps with all secrets and private data removed; and
- any known mitigation or suggested fix.

Do not attach live credentials, private browser profiles, customer files, or a
sensitive executable. Ask first for a safe transfer method if a private artifact
is essential. If a credential or externally shared file may already be exposed,
revoke or rotate it and remove provider shares before reporting the metadata of
the incident. Coordinate public disclosure with the maintainer after a fix or
mitigation is available.
