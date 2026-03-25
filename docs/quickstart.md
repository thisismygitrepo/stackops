# Quickstart

This quickstart assumes Machineconfig is already installed with `uv tool install machineconfig`.

## 1. See the current command families

```bash
mcfg --help
devops --help
```

Use `mcfg` or `machineconfig` as umbrella entrypoints, then prefer the direct commands for routine work.

## 2. Explore shell configuration

```bash
devops config shell
```

To configure a shell profile directly, use the dedicated subcommand:

```bash
devops config shell config-shell --which default
```

For the subgroup help and theme commands:

```bash
devops config shell --help
```

## 3. Install tools

Interactive flow:

```bash
devops install --interactive
```

If you already know the bundle you want:

```bash
devops install --group <group-name>
```

Check the live help before choosing names:

```bash
devops install --help
```

## 4. Inspect config and data sync workflows

```bash
devops config sync --help
devops data sync --help
```

These help screens show the current required arguments and options for dotfiles/config sync and backup sync.

## 5. Explore the rest of the CLI

```bash
cloud --help
sessions --help
agents --help
utils --help
```

Highlights from the current surface:

- `cloud`: `sync`, `copy`, `mount`, `ftpx`
- `sessions`: `run`, `run-aoe`, `attach`, `kill`, `trace`, `create-from-function`, `balance-load`, `create-template`, `summarize`
- `agents`: `parallel.{create, create-context, collect, make-template}`, `make-config`, `make-todo`, `make-symlinks`, `run-prompt`, `ask`, `add-skill`
- `utils`: `kill-process`, `environment`, `get-machine-specs`, `list-devices`, `mount`, `init-project`, `upgrade-packages`, `type-hint`, `edit`, `download`, `pdf-merge`, `pdf-compress`, `read-db`

## Next steps

<div class="grid cards" markdown>

-   :material-book-open-variant:{ .lg .middle } **User Guide**

    ---

    Continue to the broader documentation.

    [:octicons-arrow-right-24: User Guide](guide/overview.md)

-   :material-console:{ .lg .middle } **CLI Reference**

    ---

    Browse the full command reference.

    [:octicons-arrow-right-24: CLI Reference](cli/index.md)

</div>
