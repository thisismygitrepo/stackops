## scripts

Run, list, locate, and edit Python or shell scripts from configured sources.

```bash
devops scripts run [OPTIONS] [NAME] [SCRIPT_ARGS]...
devops scripts list [--source SOURCE]
devops scripts path [NAME] [--source SOURCE]
devops scripts edit [NAME] [--source SOURCE] [--editor hx|nano|code]
```

The group alias is `x`; command aliases are `run/r`, `list/l`, `path/p`, and `edit/e`.

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--source` | `-s` | Script location: `all`, `repo`, `private`, `public`, `library`, `dynamic` |
| `--interactive` | `-i` | Choose matching scripts interactively for run, path, or edit |
| `--command` | `-c` | Run NAME as a shell command |
| `--subprocess` | `-S` | Run shell scripts in a child shell instead of sourcing them |
| `--editor` | `-e` | Editor for `edit`: `hx`, `nano`, or `code` |

Put `run` options before NAME. Arguments after NAME belong to the script.

### Examples

```bash
devops scripts run my_script
devops scripts list
devops scripts run --interactive
devops scripts run --source private my_script
devops scripts run --source repo my_script --script-option value
devops scripts path my_script
devops scripts edit my_script --editor code
```

`path` without a name prints search locations as JSON. `edit` requires a local script source.

---
