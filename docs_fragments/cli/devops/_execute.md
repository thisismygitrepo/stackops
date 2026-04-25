## execute

Execute Python or shell scripts from pre-defined directories.

```bash
devops execute [OPTIONS] [NAME]
```

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--where` | `-w` | Script location: `all`, `repo`, `private`, `public`, `library`, `dynamic`, `custom` |
| `--interactive` | `-i` | Interactive selection of scripts |
| `--command` | `-c` | Run as command |
| `--list` | `-l` | List available scripts |

### Examples

```bash
# Run a script by name
devops execute my_script

# List all available scripts
devops execute --list
devops e -l

# Interactive script selection
devops execute --interactive
devops e -i

# Run from specific location
devops execute my_script --where private
devops execute my_script --where repo
```

---
