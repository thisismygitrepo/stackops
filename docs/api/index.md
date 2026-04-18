# API Reference

`stackops` is easiest to approach as three connected layers:

- `stackops.utils` for shared helpers and script-generation glue
- `stackops.cluster` for layouts, terminal sessions, and remote execution
- `stackops.jobs.installer` plus `stackops.utils.installer_utils` for curated installers

This reference follows those workflows instead of mirroring the raw package tree.

---

## Integration areas

| Area | What it covers | Main modules | Reference |
| --- | --- | --- | --- |
| Environment and project wiring | `.ve.yaml` discovery, optional IPython profile lookup, cloud metadata defaults | `stackops.utils.ve` | [Environment and project wiring](utils/environment-and-projects.md) |
| Paths, files, and config documents | JSON / INI / pickle IO, GPG helpers, path mutation, path-reference lookup | `stackops.utils.io`, `stackops.utils.path_core`, `stackops.utils.path_helper`, `stackops.utils.path_reference` | [Paths, files, and config](utils/paths-files-config.md) |
| Scheduling and cache | Repeating routines, memory cache, disk-backed cache | `stackops.utils.scheduler` | [Scheduling and cache](utils/scheduling-and-cache.md) |
| Interactive helpers and notifications | IDs, list splitting, fuzzy / TV-backed choices, HTML email | `stackops.utils.accessories`, `stackops.utils.options`, `stackops.utils.notifications` | [Interactive helpers and notifications](utils/interactive-helpers.md) |
| Code generation and command launching | Lambda-to-script conversion, `uv` command builders, shell execution, shell handoff | `stackops.utils.meta`, `stackops.utils.code`, `stackops.utils.installer_utils.installer_cli` | [Code generation and command launching](utils/code-generation.md) |
| Session layouts and orchestration | Layout schema, tab builders, tab splitting, zellij / tmux / Windows Terminal backends | `stackops.utils.schemas.layouts.layout_types`, `stackops.cluster.sessions_managers.*` | [Layouts](cluster/layouts.md), [Sessions](cluster/sessions.md) |
| Remote execution and networking | Remote job config and state, transfer, SSH, public-IP and LAN helpers | `stackops.cluster.remote.*`, `stackops.utils.ssh`, `stackops.scripts.python.helpers.helpers_network.*` | [Remote execution and networking](cluster/remote.md) |
| Installer catalog and package groups | Installer data, package groups, install orchestration, direct URL installers | `stackops.jobs.installer.*`, `stackops.utils.installer_utils.*`, `stackops.utils.schemas.installer.installer_types` | [Jobs and installer APIs](jobs/index.md) |

---

## Package map

```text
stackops/
├── cluster/
│   ├── remote/                    # Remote job models, transfer, script generation
│   └── sessions_managers/         # zellij, tmux, Windows Terminal backends
├── jobs/
│   └── installer/                 # installer_data.json, package groups, install scripts
├── scripts/python/helpers/
│   └── helpers_network/           # IP and connectivity helpers
├── utils/
│   ├── accessories, code, io, meta, notifications, options, scheduler, ssh, ve
│   ├── installer_utils/           # Runtime installer engine
│   ├── path_core, path_helper, path_reference
│   └── schemas/{installer,layouts}
└── settings/                      # Configuration assets and templates
```

---

## Choose a reference track

### Utilities

Start here if you are importing helper APIs into your own scripts or applications:

- [Utils overview](utils/index.md)
- [Environment and project wiring](utils/environment-and-projects.md)
- [Paths, files, and config](utils/paths-files-config.md)
- [Scheduling and cache](utils/scheduling-and-cache.md)
- [Interactive helpers and notifications](utils/interactive-helpers.md)
- [Code generation and command launching](utils/code-generation.md)

### Cluster and remote execution

Start here if you are generating layouts, managing terminal sessions, or submitting jobs to other machines:

- [Cluster overview](cluster/index.md)
- [Layouts](cluster/layouts.md)
- [Sessions](cluster/sessions.md)
- [Remote execution and networking](cluster/remote.md)

### Jobs and installers

Start here if you need the curated installer catalog, group definitions, or install orchestration helpers:

- [Jobs overview](jobs/index.md)
- [Installer reference](jobs/installer.md)

---

## Common import patterns

```python
from stackops.cluster.remote.models import RemoteStackOpsConfig
from stackops.cluster.remote.remote_machine import RemoteMachine
from stackops.cluster.sessions_managers.utils.maker import make_layout_from_functions
from stackops.jobs.installer.package_groups import PACKAGE_GROUP2NAMES
from stackops.utils.code import run_shell_script
from stackops.utils.installer_utils.installer_cli import install_if_missing
from stackops.utils.scheduler import Scheduler, Cache
```

If you need end-user command entrypoints instead of library APIs, see the [CLI Reference](../cli/index.md).
