# Shell History Cross-Platform Solutions

Research date: 2026-04-23.

This covers McFly, Atuin, and fuzzy history search over Bash, Zsh, and
PowerShell history. The practical conclusion is:

1. Use Atuin as the canonical cross-OS history store when sync and migration
   matter.
2. Use McFly when its local ranking model is the desired UI, but treat McFly as
   a local index unless you deliberately export/import it.
3. Use fzf/PSFzf as search UI over another store. fzf itself is not a history
   database.
4. Prefer official import/export commands. Read SQLite databases only when you
   need a one-time exact migration. Avoid writing Atuin or McFly SQLite directly
   unless you are intentionally accepting schema coupling.

## Capability Matrix

| Store or UI | Owns data? | Cross-OS | Rich metadata | Official import | Official export | Sync |
| --- | --- | --- | --- | --- | --- | --- |
| Bash history | Yes | Unix-like, Git Bash, WSL | Command; timestamp only when Bash writes `#epoch` lines | Shell-native | Plain file | External only |
| Zsh history | Yes | Unix-like, macOS, WSL | Command; with `EXTENDED_HISTORY`: epoch start and elapsed seconds | Shell-native | Plain file | External only |
| PowerShell PSReadLine | Yes | Windows, macOS, Linux | Persistent file is mostly command text; `Get-History` has richer data only for current session | Shell-native | Plain file | External only |
| Atuin | Yes | Bash, Zsh, Fish, Nushell, Xonsh, PowerShell tier 2 | Command, cwd, duration, host, user, exit, time, session | `atuin import ...` | `atuin history list ...` | Built-in E2E sync |
| McFly | Yes | Bash, Zsh, Fish, PowerShell 7+ | Command, cwd, timestamp, exit, session, selected | First-run shell import, `mcfly add` | `mcfly dump` JSON/CSV | No built-in sync |
| fzf | No | Binary works broadly; official shell keybindings for Bash/Zsh/Fish | None | N/A | N/A | N/A |
| PSFzf | No | PowerShell module | None | N/A | N/A | N/A |

## Data Model Reality

Plain shell files are lossy. Once history has gone through Bash without
timestamps, Zsh simple history, or PSReadLine persistent history, cwd, exit code,
duration, host, and often timestamps are gone.

Atuin is the best canonical store because it stores command context and has
official importers for common history formats. Its docs say it replaces shell
history with a SQLite database, records extra context, supports Bash, Zsh, Fish,
Nushell, Xonsh, and PowerShell tier 2, and can sync history with end-to-end
encryption.

McFly also stores richer local context in SQLite. Its README documents command
exit status, timestamp, execution directory, normal shell history preservation,
and support for Zsh, Bash, Fish, and PowerShell. Its supported export path is
`mcfly dump`, which emits JSON by default and can emit CSV.

fzf is different. It is an interactive fuzzy filter over input. It can search
history when shell integration feeds history to it, but it has no persistent
history store of its own. In PowerShell, PSFzf wraps fzf and can bind Ctrl-R to
PSReadLine history.

## Path Discovery

Prefer discovery commands over hard-coded paths.

### Atuin

Use:

```sh
atuin info
```

The docs show `atuin info` reporting the client config, server config, client DB
path, key path, and session path. The default Unix-like client DB path is:

```text
~/.local/share/atuin/history.db
```

The default config file is:

```text
~/.config/atuin/config.toml
```

Atuin data location follows XDG unless overridden. `ATUIN_CONFIG_DIR` can
override the config directory.

### McFly

Use the CLI when possible:

```sh
mcfly dump --format csv > mcfly-history.csv
mcfly dump --format json > mcfly-history.json
```

The documented SQLite locations are:

```text
macOS:   ~/Library/Application Support/McFly/history.db
Linux:   $XDG_DATA_DIR/mcfly/history.db, normally ~/.local/share/mcfly/history.db
Windows: %LOCALAPPDATA%\McFly\data\history.db
Legacy:  ~/.mcfly/history.db, if ~/.mcfly exists
```

### Bash

At runtime:

```sh
printf '%s\n' "${HISTFILE:-$HOME/.bash_history}"
```

Bash reads `$HISTFILE`, defaulting to `~/.bash_history`. If `HISTTIMEFORMAT` is
set, Bash writes timestamp lines beginning with the history comment character
followed by epoch digits. Those timestamp lines delimit entries, including
multi-line entries.

### Zsh

At runtime:

```sh
printf '%s\n' "${HISTFILE:-$HOME/.zsh_history}"
```

Atuin's Zsh importer reads `$HISTFILE`, `~/.zhistory`, or `~/.zsh_history`.
With `EXTENDED_HISTORY`, Zsh writes entries as:

```text
: <beginning time>:<elapsed seconds>;<command>
```

### PowerShell PSReadLine

Use:

```powershell
(Get-PSReadLineOption).HistorySavePath
```

Default locations:

```text
Windows:     $Env:APPDATA\Microsoft\Windows\PowerShell\PSReadLine\<Host>_history.txt
Non-Windows: $Env:XDG_DATA_HOME/powershell/PSReadLine/<Host>_history.txt
If unset:    $HOME/.local/share/powershell/PSReadLine/<Host>_history.txt
```

For the normal terminal host, the file is usually `ConsoleHost_history.txt`.
PSReadLine saves incrementally by default and has a secret filter, but this is
not a complete secret-management boundary.

## Recommended Architecture

Use Atuin as the canonical synchronized history store:

```sh
atuin import auto
atuin sync
```

Then choose one interactive owner for Ctrl-R in each shell:

1. Atuin Ctrl-R/up if you want sync-aware history and context filters.
2. McFly Ctrl-R if you prefer McFly ranking locally.
3. fzf/PSFzf Ctrl-R if you want a lightweight fuzzy selector over plain history.

Do not let keybindings fight. McFly, Atuin, fzf, and PSFzf can all bind Ctrl-R.
The last initialization line in the shell startup file usually wins.

## Transfer Routes

### Shell History -> Atuin

This is the cleanest migration direction because Atuin has documented importers.

Current shell:

```sh
atuin import auto
```

Explicit Bash:

```sh
HISTFILE=/path/to/.bash_history atuin import bash
```

Explicit Zsh:

```sh
HISTFILE=/path/to/.zsh_history atuin import zsh
```

PowerShell:

```powershell
atuin import powershell
```

Then sync:

```sh
atuin sync
```

Notes:

1. For formats without timestamps, Atuin generates timestamps at import time.
2. Atuin discards invalid UTF-8 in most importers.
3. Old shell files continue to be updated after Atuin is installed, so keeping a
   shell file as an emergency copy is normal.

### McFly -> Atuin

Best case: import the normal shell file directly into Atuin.

```sh
atuin import bash
atuin import zsh
atuin import powershell
```

McFly deliberately keeps the normal shell history file. If that file has the
same commands you care about, this path is simpler than touching McFly's DB.

If McFly has commands that are not in the shell file, use `mcfly dump` and
convert to a shell format Atuin can import. Zsh extended history is a good
interchange format because it carries timestamps:

```sh
mcfly dump --format csv > mcfly-history.csv
```

Cross-platform PowerShell conversion to Zsh extended history:

```powershell
$rows = Import-Csv ./mcfly-history.csv
$rows |
  Sort-Object { [datetime]::Parse($_.when_run, [Globalization.CultureInfo]::InvariantCulture) } |
  ForEach-Object {
    $dt = [datetime]::Parse($_.when_run, [Globalization.CultureInfo]::InvariantCulture)
    $epoch = ([datetimeoffset]$dt).ToUnixTimeSeconds()
    ": ${epoch}:0;$($_.cmd)"
  } |
  Set-Content -Encoding utf8NoBOM ./mcfly.zsh_history

$env:HISTFILE = (Resolve-Path ./mcfly.zsh_history).Path
atuin import zsh
```

Losses in this route:

1. `mcfly dump` exports `cmd` and `when_run`, not cwd, exit code, or selection
   training state.
2. Zsh history import cannot represent host/user/session.
3. Multi-line commands need extra care. If exact preservation matters, keep the
   McFly SQLite backup and use direct read-only SQL for analysis, then import
   into Atuin through a purpose-built importer.

### Atuin -> McFly

McFly has a supported `mcfly add` command. Use it instead of writing McFly
SQLite directly.

Simple command-only import:

```sh
atuin history list --cmd-only --reverse |
while IFS= read -r cmd; do
  [ -n "$cmd" ] && mcfly add -- "$cmd"
done
```

This preserves command text but uses the current timestamp and current
directory. That is acceptable when the goal is local fuzzy recall, not forensic
history.

If timestamps and cwd matter, `atuin history list --format` exposes fields such
as `{time}`, `{directory}`, `{duration}`, `{user}`, `{host}`, and `{command}`.
For ordinary single-line commands, use a delimiter and pass the data to
`mcfly add --when ... --dir ...`. Treat this as an operational migration, not a
perfect archival format, because commands can contain tabs or newlines.

PowerShell sketch:

```powershell
atuin history list --reverse --format "{time}`t{directory}`t{command}" |
  ForEach-Object {
    $parts = $_ -split "`t", 3
    if ($parts.Count -eq 3) {
      $dt = [datetime]::Parse($parts[0], [Globalization.CultureInfo]::InvariantCulture)
      $epoch = ([datetimeoffset]$dt).ToUnixTimeSeconds()
      mcfly add --when $epoch --dir "$($parts[1])" -- "$($parts[2])"
    }
  }
```

For exact large migrations, direct read-only access to Atuin SQLite can recover
more fields, but the schema is not the stable public interface. Keep that as a
one-time migration script with a backup, not a recurring integration.

### Shell History -> McFly

McFly can initialize from shell history when its DB does not exist. It reads
`$HISTFILE` or `MCFLY_HISTFILE` through its shell integration. This is useful for
a new McFly installation.

For precise scripted imports, use `mcfly add`:

```sh
mcfly add --when 1713910000 --dir "$PWD" --exit 0 -- "git status"
```

Important limitation from current McFly source:

1. The first-run Bash and Zsh import path strips/ignores shell timestamp
   prefixes and assigns the import-time timestamp to imported entries.
2. Fish history import preserves Fish `when` timestamps.
3. PowerShell integration sets `$env:HISTFILE` to PSReadLine's history path and
   captures new commands through PSReadLine's `AddToHistoryHandler`; persistent
   PSReadLine history itself is still command text.

If timestamp preservation from Bash/Zsh matters, parse the source history and
call `mcfly add --when ...` yourself.

### Atuin -> Plain Shell Files

Command-only export:

```sh
atuin history list --cmd-only --reverse > exported_history.txt
```

Bash:

```sh
cp ~/.bash_history ~/.bash_history.backup
atuin history list --cmd-only --reverse >> ~/.bash_history
```

Zsh command-only:

```sh
cp ~/.zsh_history ~/.zsh_history.backup
atuin history list --cmd-only --reverse >> ~/.zsh_history
```

PowerShell:

```powershell
$path = (Get-PSReadLineOption).HistorySavePath
Copy-Item -LiteralPath $path -Destination "$path.backup"
atuin history list --cmd-only --reverse | Add-Content -Encoding utf8 -LiteralPath $path
```

This is intentionally lossy. It writes commands for recall, not full history
records. For Bash/Zsh timestamps, generate Bash timestamp blocks or Zsh extended
entries from Atuin `{time}` output, then import into the target shell.

### McFly -> Plain Shell Files

If McFly has been running normally, the shell file is already maintained. That
is one of McFly's documented features.

If you need to reconstruct from McFly:

```sh
mcfly dump --format csv > mcfly-history.csv
```

Then convert CSV to the target format:

1. Bash command-only: one command per line.
2. Bash timestamped: `#<epoch>` line followed by the command.
3. Zsh extended: `: <epoch>:0;<command>`.
4. PowerShell PSReadLine: command text lines in the host history file.

### fzf / PSFzf

There is no fzf history migration because fzf does not own history.

Use fzf directly over Atuin:

```sh
atuin history list --cmd-only --reverse | fzf --scheme=history
```

Use fzf directly over Bash/Zsh:

```sh
history | fzf --scheme=history
```

For Bash/Zsh/Fish, fzf's official shell integration provides Ctrl-R history
search:

```sh
eval "$(fzf --bash)"
source <(fzf --zsh)
fzf --fish | source
```

For PowerShell, use PSFzf when the goal is fzf over PSReadLine history:

```powershell
Set-PsFzfOption -PSReadlineChordProvider 'Ctrl+t' -PSReadlineChordReverseHistory 'Ctrl+r'
```

PSFzf's README says this binds Ctrl-R to select a command from PSReadLine
history and insert it into the current line without executing it.

## Cross-OS Migration Protocol

Use this process for any serious migration:

1. Stop active shells or open a fresh shell that will not write history during
   the migration.
2. Discover paths with `atuin info`, `(Get-PSReadLineOption).HistorySavePath`,
   and `$HISTFILE`.
3. Back up the source and target stores.
4. Export to the least-lossy available interchange:
   - Atuin canonical: use `atuin sync` for machine-to-machine transfer.
   - McFly canonical: use `mcfly dump --format csv` or `--format json`.
   - Shell canonical: use the shell history file directly.
5. Convert timestamps to Unix epoch seconds for Zsh extended history or
   `mcfly add --when`.
6. Import through the target's CLI/importer.
7. Run a count and spot-check commands with spaces, quotes, Unicode, and
   multi-line entries.

## Backup Commands

Unix-like:

```sh
mkdir -p ./history-backup
cp -p "${HISTFILE:-$HOME/.bash_history}" ./history-backup/ 2>/dev/null || true
atuin info
mcfly dump --format json > ./history-backup/mcfly.json
```

PowerShell:

```powershell
$backup = Join-Path (Get-Location) "history-backup"
New-Item -ItemType Directory -Force -Path $backup | Out-Null

$psHistory = (Get-PSReadLineOption).HistorySavePath
Copy-Item -LiteralPath $psHistory -Destination (Join-Path $backup "ConsoleHost_history.txt") -Force

atuin info
mcfly dump --format json | Set-Content -Encoding utf8NoBOM (Join-Path $backup "mcfly.json")
```

For live SQLite databases, prefer application export commands. If copying DB
files directly, stop the app/daemon first or copy the `db`, `db-wal`, and
`db-shm` files together when they exist.

## Edge Cases

### Duplicate Handling

Do not dedupe blindly. The same command repeated at different times can be
useful history. Dedupe only when the target tool is a simple recall cache and
you do not care about frequency or recency.

### Timestamps

Timestamp precision and timezone handling differ:

1. Bash timestamped history uses Unix epoch comments.
2. Zsh extended history uses Unix epoch start time plus elapsed seconds.
3. McFly `dump` writes local timezone date/time strings.
4. Atuin `history list --format "{time}"` is CLI-formatted output, not a stable
   interchange schema.
5. PSReadLine persistent files do not store timestamps.

When converting, normalize to Unix epoch seconds.

### Multi-line Commands

Multi-line history is the hardest part of shell-file migration.

1. Bash timestamp lines can delimit multi-line commands.
2. Zsh and PowerShell can represent multi-line commands in ways that are awkward
   for line-oriented converters.
3. `atuin history list --print0` is useful when exporting entries for scripts,
   because NUL termination avoids ambiguity between entries.
4. If exact multi-line preservation matters, use a structured export or direct
   read-only database extraction instead of shell text.

### Encoding

Use UTF-8. Atuin's importer discards invalid UTF-8 in most formats. McFly reads
some shell files with lossy UTF-8 conversion. In PowerShell 7+, prefer:

```powershell
Set-Content -Encoding utf8NoBOM
```

### Secrets

All history systems can contain secrets.

1. PSReadLine has sensitive-history filtering.
2. Atuin has secret filters and encrypted sync.
3. Plain shell files and exported CSV/JSON are plaintext.
4. McFly dump files are plaintext.

Delete temporary migration files after verification if they contain sensitive
commands.

## Best Default Setups

### One Canonical History Across All OSes

Use Atuin everywhere:

```sh
atuin import auto
atuin sync
```

PowerShell:

```powershell
atuin import powershell
atuin sync
```

Use Atuin Ctrl-R/up bindings. Keep fzf for file/process/git selection. Do not
make McFly the sync layer.

### Atuin Sync Plus McFly Local Ranking

Use Atuin for sync, then periodically seed McFly from Atuin if you want McFly's
local UI:

```sh
atuin sync
atuin history list --cmd-only --reverse |
while IFS= read -r cmd; do
  [ -n "$cmd" ] && mcfly add -- "$cmd"
done
```

This gives McFly local recall but loses Atuin metadata in McFly. It is a cache,
not the canonical store.

### Minimal Dependencies

Use shell history plus fzf:

```sh
eval "$(fzf --bash)"
source <(fzf --zsh)
```

PowerShell:

```powershell
Set-PsFzfOption -PSReadlineChordReverseHistory 'Ctrl+r'
```

This is simple, but history transfer is just file copying, and rich metadata is
not available.

## Source Links

Atuin:

1. Getting started and supported shells: https://docs.atuin.sh/cli/
2. Import reference: https://docs.atuin.sh/cli/reference/import/
3. History list reference: https://docs.atuin.sh/cli/reference/list/
4. Sync guide: https://docs.atuin.sh/cli/guide/sync/
5. Config and DB path: https://docs.atuin.sh/cli/configuration/config/
6. `atuin info`: https://docs.atuin.sh/cli/reference/info/

McFly:

1. README, features, dump, DB paths: https://github.com/cantino/mcfly
2. CLI/source for `add`, `dump`, history formats: https://github.com/cantino/mcfly/tree/master/src

fzf and PSFzf:

1. fzf README and shell integration: https://github.com/junegunn/fzf
2. PSFzf README and PSReadLine integration: https://github.com/kelleyma49/PSFzf

Shell history formats:

1. Bash history manual: https://www.gnu.org/software/bash/manual/html_node/Bash-History-Facilities.html
2. Zsh `EXTENDED_HISTORY`: https://zsh.sourceforge.io/Doc/Release/Options.html
3. PSReadLine history: https://learn.microsoft.com/en-us/powershell/module/psreadline/about/about_psreadline
4. PSReadLine history path/save style: https://learn.microsoft.com/en-us/powershell/module/PSReadline/set-psreadlineoption
