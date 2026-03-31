# Quickstart

## Good first commands

```bash

devops install --group sysabc  # Install (if missing) package manager (apt or brew or winget)
devops config copy-assets all  # copy config files to machine
devops config sync down --sensitivity public --method copy --on-conflict overwrite-default-path --which all  # link config files
devops config terminal config-shell --which default  # add alias to shell
devops install --group termabc  # install the basic terminal cli's

```


## 2. Explore terminal configuration

```bash
devops config terminal --help
```

To configure a shell profile directly, use the dedicated subcommand:

```bash
devops config terminal config-shell --which default
```

If you want the Nushell profile instead:

```bash
devops config terminal config-shell --which nushell
```

The nested help screens render `Usage: devops terminal ...`, but the full entrypoint is still `devops config terminal ...`.

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
croshell --help
```

Highlights from the current surface:

- `cloud`: `sync`, `copy`, `mount`, `ftpx`
- `sessions`: `run`, `run-aoe`, `attach`, `kill`, `trace`, `create-from-function`, `balance-load`, `create-template`, `summarize`
- `agents`: `parallel.{create, create-context, collect, make-template}`, `make-config`, `make-todo`, `make-symlinks`, `run-prompt`, `ask`, `add-skill`
- `utils`: `machine.{kill-process, environment, get-machine-specs, list-devices, mount}`, `pyproject.{init-project, upgrade-packages, type-hint}`, `file.{edit, download, pdf-merge, pdf-compress, read-db}`
- `croshell`: launch `ipython`, `python`, `marimo`, `jupyter`, `vscode`, or `visidata` against a file or project context

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
