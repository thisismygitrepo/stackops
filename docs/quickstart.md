# Quickstart

## Choose a workflow

After [installation](installation.md), inspect the command families and the workflow you need:

```bash
stackops --help
devops install --help
devops config sync --help
terminal run --help
```

## Install tools

For example, check whether Television's `tv` binary is available:

```bash
devops install tv --check
```

This checks binary status; it does not preview or validate the installer. To install Television using the packaged catalog:

```bash
devops install tv --source library
```

Availability and installer behavior depend on the platform. To select other tools interactively:

```bash
devops install --interactive --source library
```

If you already know the bundle you want:

```bash
devops install --group <group-name>
```

Check the live help and [package guide](guide/packages.md) before choosing names:

```bash
devops install --help
```

## Choose configuration changes

Configuration sync uses declared mappings. Inspect its options and the [configuration guide](guide/configuration.md) before choosing a mapping:

```bash
devops config sync --help
devops data sync --help
```

`devops config interactive` offers package, asset, configuration, and shell setup choices. Its public copy and symlink choices use `overwrite-default-path`, which can replace existing target files. The explicit scripted example below instead uses `throw-error` to stop on conflicts.

## Optional workstation setup

This broader sequence installs system and terminal package groups, copies bundled assets, applies all public configuration mappings, and updates the default shell profile. It is useful when you want StackOps' workstation conventions. On an existing configured machine, choose only the individual actions you need. System package groups can invoke privileged package managers, and their behavior varies by platform.

```bash
devops install --group sysabc
devops config copy-assets all
devops config sync down \
  --sensitivity public \
  --method copy \
  --on-conflict throw-error \
  --which all
devops config terminal config-shell --which default
devops install --group termabc
```

The sync command copies files; it does not create symlinks. If it reports a conflict, inspect the existing target and choose a conflict policy deliberately. Open a new shell after configuring its profile.

## Explore the rest of the CLI

```bash
devops --help
cloud --help
terminal --help
agents --help
utils --help
fire --help
preview --help
seek --help
stackops --help
```


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
