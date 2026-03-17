# Package Management

The current package installation workflow is centered on `devops install`.

---

## Overview

Machineconfig keeps package installation behind one command surface:

```bash
devops install --help
```

The live help currently describes `devops install [WHICH]` as the supported package entrypoint.

---

## Installation modes

Current help shows three main ways to use `devops install`:

### Install named programs

Pass `WHICH` as a comma-separated list of program names:

```bash
devops install --help
```

### Install a group

Use the `--group` flag when `WHICH` refers to a group name:

```bash
devops install --help
```

### Choose interactively

Use the interactive picker:

```bash
devops install --interactive --help
```

---

## What changed

Older documentation referred to commands such as:

- `devops install-essentials`
- `devops install-group`
- `devops check-installations`
- `devops update-all`

Those are not part of the current verified command surface for this guide. For package installation, prefer `devops install` and inspect its live help output.

---

## Practical guidance

- Use `devops install --help` to see the current argument and option shape.
- Use `devops --help` to discover adjacent machine-management workflows.
- Treat group names as environment-specific until you confirm them in your own setup.
